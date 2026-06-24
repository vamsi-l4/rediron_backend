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
            fields = item.get("fields", item)
            code = fields.get("id") or fields.get("code") or f"FA{index:02d}"
            title = fields.get("title") or code
            featured = fields.get("featuredImage") or {}
            image_url = (
                featured.get("imageUrl")
                or fields.get("featured_image_url")
                or fields.get("image_url")
                or ""
            )
            slug = fields.get("slug") or slugify(title)[:240]

            obj, created = FitnessArticle.objects.update_or_create(
                code=code,
                defaults={
                    "title": title,
                    "slug": slug,
                    "category": fields.get("category") or "Beginner",
                    "featured_image_url": image_url,
                    "author": fields.get("author") or "RedIron Team",
                    "overview": fields.get("overview") or "",
                    "coreConcepts": normalize_list(fields.get("coreConcepts")),
                    "whyItMatters": normalize_list(fields.get("whyItMatters")),
                    "scienceExplained": normalize_list(fields.get("scienceExplained")),
                    "practicalApplication": normalize_list(fields.get("practicalApplication")),
                    "commonMyths": normalize_list(fields.get("commonMyths")),
                    "coachInsight": fields.get("coachInsight") or "",
                    "keyTakeaways": normalize_list(fields.get("keyTakeaways")),
                    "videoTitle": fields.get("videoTitle") or "",
                    "youtubeUrl": fields.get("youtubeUrl") or "",
                    "relatedArticles": normalize_list(fields.get("relatedArticles")),
                    "published_at": parse_date(fields.get("publishDate") or fields.get("published_at")),
                    "is_published": fields.get("is_published", True),
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
