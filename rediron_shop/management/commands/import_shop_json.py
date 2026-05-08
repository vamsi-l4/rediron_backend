import json
from pathlib import Path
from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from rediron_shop.models import (
    Category, Subcategory, Brand, Product, ProductVariant, ProductReview,
    BlogPost, FAQ, Dealer, Coupon, RewardPoint, PaymentMethod
)


def validate_mandatory_fields(data, required_fields, section_name):
    """Validate that all required fields are present in the data."""
    missing = []
    for item in data:
        for field in required_fields:
            if field not in item or (item[field] is None or item[field] == ""):
                missing.append(f"{section_name}: Missing or empty '{field}' in item {item.get('id', item.get('name', 'unknown'))}")
    return missing


class Command(BaseCommand):
    help = "Import shop data from shop.json into the database after validation."

    def add_arguments(self, parser):
        parser.add_argument(
            "json_path",
            type=str,
            help="Path to the shop JSON file (e.g. shop.json)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Parse and report actions without saving to DB.",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            dest="skip_existing",
            help="When set, existing items (matched by slug or name) will not be updated.",
        )

    def handle(self, *args, **options):
        path = Path(options["json_path"])
        dry_run = options["dry_run"]
        skip_existing = options["skip_existing"]

        if not path.exists():
            raise CommandError(f"File not found: {path}")

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise CommandError(f"Error reading JSON file: {e}")

        # Validation
        validations = []
        validations.extend(validate_mandatory_fields(data.get("categories", []), ["id", "name", "slug"], "categories"))
        validations.extend(validate_mandatory_fields(data.get("subcategories", []), ["id", "name", "category"], "subcategories"))
        validations.extend(validate_mandatory_fields(data.get("brands", []), ["id", "name"], "brands"))
        validations.extend(validate_mandatory_fields(data.get("products", []), ["category", "name", "slug", "description", "image", "mrp", "price", "is_active"], "products"))
        validations.extend(validate_mandatory_fields(data.get("blog_posts", []), ["title", "slug", "content", "author"], "blog_posts"))
        validations.extend(validate_mandatory_fields(data.get("faqs", []), ["question", "answer"], "faqs"))
        validations.extend(validate_mandatory_fields(data.get("dealers", []), ["name", "address", "city", "state", "phone"], "dealers"))
        validations.extend(validate_mandatory_fields(data.get("coupons", []), ["code", "description", "discount_percent", "active", "valid_from", "valid_to"], "coupons"))
        validations.extend(validate_mandatory_fields(data.get("reward_points", []), ["name", "points"], "reward_points"))
        validations.extend(validate_mandatory_fields(data.get("payment_methods", []), ["id", "method"], "payment_methods"))

        if validations:
            for v in validations:
                self.stdout.write(self.style.ERROR(v))
            raise CommandError("Validation failed. Mandatory fields missing.")

        self.stdout.write(self.style.SUCCESS("Validation passed. All mandatory fields present."))

        # Import logic
        created = 0
        updated = 0
        skipped = 0
        errors = 0

        # Categories
        for item in data.get("categories", []):
            try:
                obj, created_flag = Category.objects.get_or_create(
                    slug=item["slug"],
                    defaults={
                        "name": item["name"],
                        "description": item.get("description", ""),
                        "image": item.get("image", ""),
                    }
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"Error importing category {item['name']}: {e}"))

        # Subcategories
        for item in data.get("subcategories", []):
            try:
                category = Category.objects.get(name=item["category"])
                obj, created_flag = Subcategory.objects.get_or_create(
                    slug=f"{category.slug}-{item['name'].lower().replace(' ', '-')}",
                    defaults={
                        "category": category,
                        "name": item["name"],
                        "description": item.get("description", ""),
                        "image": item.get("image", ""),
                    }
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"Error importing subcategory {item['name']}: {e}"))

        # Brands
        for item in data.get("brands", []):
            try:
                obj, created_flag = Brand.objects.get_or_create(
                    name=item["name"],
                    defaults={
                        "slug": item["name"].lower().replace(" ", "-"),
                        "description": item.get("description", ""),
                        "logo": item.get("image", ""),
                    }
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"Error importing brand {item['name']}: {e}"))

        # Products
        for item in data.get("products", []):
            try:
                category = Category.objects.get(name=item["category"])
                obj, created_flag = Product.objects.get_or_create(
                    slug=item["slug"],
                    defaults={
                        "category": category,
                        "name": item["name"],
                        "description": item["description"],
                        "image": item["image"],
                        "mrp": Decimal(str(item["mrp"])),
                        "price": Decimal(str(item["price"])),
                        "discount_percent": item["discount_percent"],
                        "rating": Decimal(str(item["rating"])),
                        "is_active": item["is_active"],
                    }
                )
                if created_flag:
                    created += 1
                    # Variants
                    for var in item.get("variants", []):
                        ProductVariant.objects.create(
                            product=obj,
                            variant_name=var["variant_name"],
                            sku=var["sku"],
                            price=Decimal(str(var["price"])),
                            in_stock=var["in_stock"],
                            inventory=var["inventory"],
                        )
                    # Reviews
                    for rev in item.get("reviews", []):
                        ProductReview.objects.create(
                            product=obj,
                            reviewer_name=rev["reviewer_name"],
                            rating=rev["rating"],
                            comment=rev["comment"],
                        )
                else:
                    updated += 1
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"Error importing product {item['name']}: {e}"))

        # Blog Posts
        for item in data.get("blog_posts", []):
            try:
                published_at = parse_datetime(item["published_at"]) or timezone.now()
                obj, created_flag = BlogPost.objects.get_or_create(
                    slug=item["slug"],
                    defaults={
                        "title": item["title"],
                        "content": item["content"],
                        "image": item.get("image", ""),
                        "author": item["author"],
                        "tags": item.get("tags", ""),
                        "published_at": published_at,
                    }
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"Error importing blog post {item['title']}: {e}"))

        # FAQs
        for item in data.get("faqs", []):
            try:
                obj, created_flag = FAQ.objects.get_or_create(
                    question=item["question"],
                    defaults={
                        "answer": item["answer"],
                        "category": item.get("category", ""),
                    }
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"Error importing FAQ {item['question']}: {e}"))

        # Dealers
        for item in data.get("dealers", []):
            try:
                obj, created_flag = Dealer.objects.get_or_create(
                    name=item["name"],
                    defaults={
                        "address": item["address"],
                        "city": item["city"],
                        "state": item["state"],
                        "phone": item["phone"],
                        "email": item.get("email", ""),
                        "is_active": item.get("is_active", True),
                    }
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"Error importing dealer {item['name']}: {e}"))

        # Coupons
        for item in data.get("coupons", []):
            try:
                valid_from = parse_datetime(item["valid_from"]) or timezone.now()
                valid_to = parse_datetime(item["valid_to"]) or timezone.now()
                obj, created_flag = Coupon.objects.get_or_create(
                    code=item["code"],
                    defaults={
                        "description": item["description"],
                        "discount_percent": item["discount_percent"],
                        "active": item["active"],
                        "valid_from": valid_from,
                        "valid_to": valid_to,
                    }
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"Error importing coupon {item['code']}: {e}"))

        # Reward Points
        for item in data.get("reward_points", []):
            try:
                last_updated = parse_datetime(item["last_updated"]) or timezone.now()
                obj, created_flag = RewardPoint.objects.get_or_create(
                    name=item["name"],
                    defaults={
                        "points": item["points"],
                        "last_updated": last_updated,
                    }
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"Error importing reward point {item['name']}: {e}"))

        # Payment Methods
        for item in data.get("payment_methods", []):
            try:
                method_map = {
                    "Credit Card": "card",
                    "Debit Card": "card",
                    "UPI": "upi",
                    "Net Banking": "netbanking",
                    "Wallet": "upi",
                    "EMI": "card",
                    "PayLater": "upi",
                    "MBCash": "upi",
                    "Cash On Delivery": "cod",
                }
                method = method_map.get(item["method"], "card")
                obj, created_flag = PaymentMethod.objects.get_or_create(
                    name=item["method"],
                    defaults={
                        "method": method,
                        "is_active": True,
                    }
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"Error importing payment method {item['method']}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Import finished — created={created}, updated={updated}, skipped={skipped}, errors={errors}"))
