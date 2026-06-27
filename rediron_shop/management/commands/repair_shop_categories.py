from django.core.management.base import BaseCommand

from rediron_shop.models import Category, Product
from rediron_shop.serializers import CATEGORY_IMAGE_FALLBACKS


class Command(BaseCommand):
    help = "Repair shop category image URLs, active flags, and equipment stock counts."

    def handle(self, *args, **options):
        stock_updated = Product.objects.filter(
            stock=0,
        ).update(stock=25)
        active_updated = Product.objects.filter(is_active=False).update(is_active=True)
        if stock_updated:
            self.stdout.write(self.style.SUCCESS(f"Updated {stock_updated} products to in stock"))
        if active_updated:
            self.stdout.write(self.style.SUCCESS(f"Activated {active_updated} products"))

        for slug, image_url in CATEGORY_IMAGE_FALLBACKS.items():
            updated = Category.objects.filter(slug=slug).update(image="", image_url=image_url)
            if updated:
                count = Category.objects.get(slug=slug).products.filter(is_active=True).count()
                self.stdout.write(self.style.SUCCESS(f"{slug}: image fixed, {count} active products"))

        missing = set(CATEGORY_IMAGE_FALLBACKS) - set(Category.objects.values_list("slug", flat=True))
        for slug in sorted(missing):
            self.stdout.write(self.style.WARNING(f"{slug}: category not found"))
