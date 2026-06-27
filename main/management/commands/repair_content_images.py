from django.core.management.base import BaseCommand

from main.models import NutritionArticle, WorkoutArticle, WorkoutTip
from main.serializers import NUTRITION_IMAGE_FALLBACKS, WORKOUT_TIP_IMAGE_FALLBACKS, matched_image_url
from rediron_shop.models import Category, Product
from rediron_shop.serializers import CATEGORY_IMAGE_FALLBACKS, FOOTWEAR_KEYWORD_IMAGES, PRODUCT_IMAGE_FALLBACKS


MISSING_LOCAL_PREFIXES = ("/assets/workout-tips/", "assets/workout-tips/")


class Command(BaseCommand):
    help = "Repairs shop category/product and article thumbnail URLs with matched image URLs."

    def handle(self, *args, **options):
        category_updates = 0
        for category in Category.objects.all():
            fallback = CATEGORY_IMAGE_FALLBACKS.get(category.slug)
            if fallback and category.image_url != fallback:
                category.image_url = fallback
                category.image = ""
                category.save(update_fields=["image_url", "image"])
                category_updates += 1

        product_updates = 0
        for product in Product.objects.all():
            image_url = PRODUCT_IMAGE_FALLBACKS.get(product.slug)
            if not image_url and product.product_type == "footwear":
                name = product.name.lower()
                for keyword, candidate in FOOTWEAR_KEYWORD_IMAGES:
                    if keyword in name:
                        image_url = candidate
                        break
            if image_url and product.featured_image_url != image_url:
                product.featured_image_url = image_url
                product.save(update_fields=["featured_image_url"])
                product_updates += 1

        nutrition_updates = 0
        for article in NutritionArticle.objects.all():
            if not article.featured_image_url:
                article.featured_image_url = matched_image_url(
                    article,
                    NUTRITION_IMAGE_FALLBACKS,
                    "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=900&q=80",
                )
                article.save(update_fields=["featured_image_url"])
                nutrition_updates += 1

        workout_article_updates = 0
        for article in WorkoutArticle.objects.all():
            if not article.featured_image_url:
                article.featured_image_url = matched_image_url(
                    article,
                    WORKOUT_TIP_IMAGE_FALLBACKS,
                    "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=900&q=80",
                )
                article.save(update_fields=["featured_image_url"])
                workout_article_updates += 1

        workout_tip_updates = 0
        for tip in WorkoutTip.objects.all():
            thumbnail = tip.thumbnail or ""
            if not thumbnail.startswith("http") or thumbnail.startswith(MISSING_LOCAL_PREFIXES):
                tip.thumbnail = matched_image_url(
                    tip,
                    WORKOUT_TIP_IMAGE_FALLBACKS,
                    "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=900&q=80",
                )
                tip.save(update_fields=["thumbnail"])
                workout_tip_updates += 1

        self.stdout.write(self.style.SUCCESS(
            "Image repair complete. "
            f"Categories: {category_updates}, Products: {product_updates}, "
            f"Nutrition articles: {nutrition_updates}, Workout articles: {workout_article_updates}, "
            f"Workout tips: {workout_tip_updates}."
        ))
