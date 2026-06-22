import json
import os
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from main.models import FitnessArticle


DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%SZ",
]


def normalize_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    return [str(value).strip()]


def parse_date(value):
    if not value:
        return timezone.now()
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(str(value), fmt)
            return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(str(value))
        return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed
    except ValueError:
        return timezone.now()


def fixture_candidates():
    main_dir = os.path.join(settings.BASE_DIR, "main")
    return [
        os.path.join(main_dir, "fitness_articles.json"),
        os.path.join(main_dir, "Fitness_article.json"),
        os.path.join(main_dir, "fixtures", "fitness_articles.json"),
        os.path.join(main_dir, "fixtures", "Fitness_article.json"),
    ]


class Command(BaseCommand):
    help = "Loads FitnessArticle records from fitness_articles.json/Fitness_article.json without creating duplicates."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing FitnessArticle rows before loading.",
        )

    def handle(self, *args, **options):
        fixture_path = next((path for path in fixture_candidates() if os.path.exists(path)), None)
        if not fixture_path:
            self.stdout.write(self.style.ERROR("Missing fitness articles fixture. Expected main/fitness_articles.json or main/fixtures/Fitness_article.json."))
            return

        with open(fixture_path, "r", encoding="utf-8") as fixture:
            articles = json.load(fixture)

        if options["clear"]:
            deleted, _ = FitnessArticle.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing fitness articles."))

        created_count = 0
        updated_count = 0

        for index, item in enumerate(articles, start=1):
            code = item.get("id") or item.get("code") or f"FA{index:02d}"
            title = item.get("title") or code
            featured = item.get("featuredImage") or {}
            image_url = (
                featured.get("imageUrl")
                or item.get("featured_image_url")
                or item.get("image_url")
                or ""
            )
            slug = item.get("slug") or slugify(title)[:240]

            obj, created = FitnessArticle.objects.update_or_create(
                code=code,
                defaults={
                    "title": title,
                    "slug": slug,
                    "category": item.get("category") or "Beginner",
                    "featured_image_url": image_url,
                    "author": item.get("author") or "RedIron Team",
                    "overview": item.get("overview") or "",
                    "core_concepts": normalize_list(item.get("coreConcepts")),
                    "why_it_matters": normalize_list(item.get("whyItMatters")),
                    "science_explained": normalize_list(item.get("scienceExplained")),
                    "practical_application": normalize_list(item.get("practicalApplication")),
                    "common_myths": normalize_list(item.get("commonMyths")),
                    "coach_insight": item.get("coachInsight") or "",
                    "key_takeaways": normalize_list(item.get("keyTakeaways")),
                    "video_title": item.get("videoTitle") or "",
                    "youtube_url": item.get("youtubeUrl") or "",
                    "related_articles": normalize_list(item.get("relatedArticles")),
                    "published_at": parse_date(item.get("publishDate") or item.get("published_at")),
                    "is_published": item.get("is_published", True),
                },
            )
            obj.save()
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Fitness articles loaded from {fixture_path}. Created: {created_count}. Updated: {updated_count}. Total rows: {len(articles)}."
            )
        )
