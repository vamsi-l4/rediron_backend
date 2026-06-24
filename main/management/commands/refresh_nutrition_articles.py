import json
from pathlib import Path
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from main.models import NutritionArticle

CATEGORY_MAP = {
    "NUTRITION": "Nutrition",
    "SUPPLEMENTS": "Supplements",
    "RECIPES": "Recipes",
}

DATE_FORMATS = ["%B %Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]

def normalize_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def parse_date(value, item=None):
    if not value:
        return timezone.now()
    if isinstance(value, dict) and item:
        value = item.get("date") or item.get("Date") or item.get("published_at") or ""
    value = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt)
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed)
            return parsed
        except Exception:
            continue
    try:
        parsed = datetime.fromisoformat(value)
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed)
        return parsed
    except Exception:
        return timezone.now()


def build_excerpt(item, overview_list):
    excerpt = item.get("excerpt") or item.get("Excerpt")
    if excerpt:
        return str(excerpt).strip()
    if overview_list:
        return overview_list[0][:260].rstrip(" .,") + "..." if len(overview_list[0]) > 260 else overview_list[0]
    return ""


class Command(BaseCommand):
    help = "Reloads NutritionArticle data from main/fixtures/rediron_articles_complete_guide.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing NutritionArticle records before loading.",
        )

    def handle(self, *args, **options):
        fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / "rediron_articles_complete_guide.json"
        if not fixture_path.exists():
            self.stdout.write(self.style.ERROR(f"Missing fixture file: {fixture_path}"))
            return

        try:
            with fixture_path.open("r", encoding="utf-8") as f:
                fixture_data = json.load(f)
        except json.JSONDecodeError as exc:
            self.stdout.write(self.style.ERROR(f"Invalid JSON in fixture file: {exc}"))
            return

        if options["clear"]:
            count, _ = NutritionArticle.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {count} existing nutrition articles."))

        total_created = 0
        total_updated = 0
        for section_key, items in fixture_data.items():
            if not isinstance(items, list):
                continue

            category = CATEGORY_MAP.get(str(section_key).upper(), str(section_key).title())
            for index, item in enumerate(items, start=1):
                code = item.get("id") or f"{section_key[:1].upper()}{index:02d}"
                title = item.get("title") or item.get("Title") or f"Untitled Article {code}"
                slug = item.get("slug") or slugify(title)

                if not title:
                    continue

                overview_list = normalize_list(item.get("overview") or item.get("description"))
                content_data = {
                    "overview": overview_list,
                    "benefits": normalize_list(item.get("benefits") or item.get("key_benefits")),
                    "how_to": normalize_list(
                        item.get("how_to") or item.get("How To") or item.get("how to") or item.get("steps")
                    ),
                    "mistakes": normalize_list(item.get("mistakes") or item.get("common_mistakes")),
                    "tips": normalize_list(item.get("tips") or item.get("coach_tip")),
                    "video_url": item.get("video") or item.get("video_url"),
                    "video_title": item.get("video_title"),
                    "related_ids": item.get("related") or item.get("Related") or [],
                    "meta": {
                        "id": item.get("id"),
                        "sub": item.get("sub"),
                        "date": str(item.get("date")),
                        "read": item.get("read") or item.get("reading_time"),
                    },
                }

                obj, created = NutritionArticle.objects.update_or_create(
                    code=code,
                    defaults={
                        "title": title,
                        "slug": slug,
                        "author": item.get("author") or item.get("Author") or "RedIron Team",
                        "excerpt": build_excerpt(item, overview_list),
                        "content": content_data,
                        "featured_image_url": item.get("featured_image_url") or item.get("Featured image url") or "",
                        "category": CATEGORY_MAP.get(str(item.get("tag", category)).upper(), item.get("tag", category)),
                        "tags": ", ".join(filter(None, [str(item.get("tag") or "").strip(), str(item.get("sub") or "").strip()])).strip(),
                        "published_at": parse_date(item.get("date") or item.get("Date") or item.get("Published at"), item),
                        "is_published": item.get("is_published", True),
                        "featured": False,
                        "references": item.get("references"),
                        "video_url": item.get("video") or item.get("video_url"),
                    }
                )

                if created:
                    total_created += 1
                else:
                    total_updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"✔ Nutrition articles refreshed. Created: {total_created}, Updated: {total_updated}."
        ))
