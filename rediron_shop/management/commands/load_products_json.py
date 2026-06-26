import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from rediron_shop.models import Brand, Category, Product, Subcategory


CATEGORY_META = {
    "Proteins": {
        "description": "Whey, isolate, casein, and mass gainers for muscle recovery and strength goals.",
        "image_url": "https://images.unsplash.com/photo-1612487529431-2da0571c87ef?w=600&q=80",
        "product_type": "nutrition",
    },
    "Supplements": {
        "description": "Creatine, BCAA, pre-workout, and recovery formulas for serious training sessions.",
        "image_url": "https://images.unsplash.com/photo-1593095948071-474c5cc2989d?w=600&q=80",
        "product_type": "nutrition",
    },
    "Vitamins": {
        "description": "Daily wellness essentials including multivitamins, D3, zinc, magnesium, and fish oil.",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=600&q=80",
        "product_type": "nutrition",
    },
    "Healthy Foods": {
        "description": "High-protein snacks, oats, granola, dry fruits, and clean everyday nutrition.",
        "image_url": "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=600&q=80",
        "product_type": "nutrition",
    },
    "Gym Wear": {
        "description": "Training-ready tees, tanks, joggers, leggings, shorts, and sports bras.",
        "image_url": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600&q=80",
        "product_type": "clothing",
    },
    "Footwear": {
        "description": "Running, lifting, and training shoes built for stability, comfort, and performance.",
        "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80",
        "product_type": "footwear",
    },
    "Accessories": {
        "description": "Gym bags, gloves, belts, wraps, shakers, sleeves, and bands for better sessions.",
        "image_url": "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=600&q=80",
        "product_type": "accessory",
    },
}


DETAIL_KEYS = {
    "nutrition": "nutrition",
    "clothing": "clothing",
    "footwear": "footwear",
    "accessory": "accessory",
}


class Command(BaseCommand):
    help = "Load the new ecommerce Products.json fixture into rediron_shop."

    def add_arguments(self, parser):
        parser.add_argument(
            "json_path",
            nargs="?",
            default=None,
            help="Path to Products.json. Defaults to main/fixtures/Products.json.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Validate and report without writing.")

    def handle(self, *args, **options):
        path = Path(options["json_path"]) if options["json_path"] else Path(__file__).resolve().parents[3] / "main" / "fixtures" / "Products.json"
        if not path.exists():
            raise CommandError(f"Products JSON not found: {path}")

        try:
            products = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise CommandError(f"Could not read Products.json: {exc}")

        if not isinstance(products, list):
            raise CommandError("Products.json must contain a top-level list.")

        required = ["category", "subcategory", "name", "slug", "brand", "description", "price", "mrp", "rating", "stock"]
        missing = []
        for item in products:
            for field in required:
                if item.get(field) in [None, ""]:
                    missing.append(f"{item.get('id', item.get('name', 'unknown'))}: missing {field}")
        if missing:
            for line in missing[:30]:
                self.stdout.write(self.style.ERROR(line))
            raise CommandError(f"Validation failed with {len(missing)} missing required values.")

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Dry run OK. {len(products)} products are ready to import."))
            return

        created_products = 0
        updated_products = 0
        category_cache = {}
        subcategory_cache = {}
        brand_cache = {}

        for item in products:
            category_name = item["category"].strip()
            category_slug = slugify(category_name)
            meta = CATEGORY_META.get(category_name, {})
            category, _ = Category.objects.update_or_create(
                slug=category_slug,
                defaults={
                    "name": category_name,
                    "description": meta.get("description", ""),
                    "image_url": meta.get("image_url", ""),
                },
            )
            category_cache[category_name] = category

            subcategory_name = item["subcategory"].strip()
            subcategory_slug = f"{category_slug}-{slugify(subcategory_name)}"
            subcategory, _ = Subcategory.objects.update_or_create(
                slug=subcategory_slug,
                defaults={
                    "category": category,
                    "name": subcategory_name,
                    "description": f"{subcategory_name} products in {category_name}.",
                    "image_url": item.get("featured_image_url", ""),
                },
            )
            subcategory_cache[(category_name, subcategory_name)] = subcategory

            brand_name = item["brand"].strip()
            brand_slug = slugify(brand_name)
            brand, _ = Brand.objects.update_or_create(
                slug=brand_slug,
                defaults={"name": brand_name},
            )
            brand_cache[brand_name] = brand

            product_type = meta.get("product_type")
            if not product_type:
                product_type = next((DETAIL_KEYS[key] for key in DETAIL_KEYS if item.get(key)), "")

            detail_defaults = {key: {} for key in DETAIL_KEYS.values()}
            if product_type in DETAIL_KEYS.values():
                detail_defaults[product_type] = item.get(product_type, {}) or {}
                if product_type == "clothing":
                    detail_defaults[product_type] = detail_defaults[product_type] or item.get("apparel", {}) or {}

            defaults = {
                "category": category,
                "subcategory": subcategory,
                "brand": brand,
                "product_type": product_type,
                "name": item["name"],
                "description": item["description"],
                "featured_image_url": item.get("featured_image_url", ""),
                "price": Decimal(str(item["price"])),
                "mrp": Decimal(str(item["mrp"])),
                "discount_percent": int(item.get("discount_percent") or 0),
                "rating": Decimal(str(item.get("rating") or 0)),
                "stock": int(item.get("stock") or 0),
                "sku": item.get("sku", ""),
                "tags": item.get("tags", []) or [],
                "is_active": bool(item.get("is_active", True)),
                **detail_defaults,
            }

            _, created = Product.objects.update_or_create(slug=item["slug"], defaults=defaults)
            if created:
                created_products += 1
            else:
                updated_products += 1

        self.stdout.write(self.style.SUCCESS(
            "Loaded ecommerce catalog: "
            f"{len(category_cache)} categories, {len(subcategory_cache)} subcategories, "
            f"{len(brand_cache)} brands, {created_products} created products, {updated_products} updated products."
        ))
