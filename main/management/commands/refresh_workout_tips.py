import json
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from main.models import WorkoutTip
from main.serializers import WORKOUT_TIP_IMAGE_FALLBACKS, matched_image_url


class Command(BaseCommand):
    help = "Loads WorkoutTip records from main/fixtures/Workout_Tips.json into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing WorkoutTip rows before loading the fixture.",
        )

    def handle(self, *args, **options):
        fixture_path = os.path.join(settings.BASE_DIR, "main", "fixtures", "Workout_Tips.json")
        if not os.path.exists(fixture_path):
            self.stdout.write(self.style.ERROR(f"Missing fixture: {fixture_path}"))
            return

        with open(fixture_path, "r", encoding="utf-8") as fixture:
            tips = json.load(fixture)

        if options["clear"]:
            deleted, _ = WorkoutTip.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing workout tips."))

        created_count = 0
        updated_count = 0

        for index, row in enumerate(tips, start=1):
            fields = row.get("fields", row)
            code = row.get("pk") or fields.get("id") or fields.get("code") or f"WT{index:02d}"
            slug = fields.get("slug") or str(fields.get("title", code)).lower().replace(" ", "-")
            youtube_url = fields.get("youtubeUrl") or fields.get("youtube_url") or ""
            featured_image_url = fields.get("featured_image_url") or fields.get("image_url") or fields.get("thumbnail") or ""
            published_at = fields.get("published_at") or fields.get("date")
            if isinstance(published_at, str):
                published_at = parse_datetime(published_at)
            if not published_at:
                published_at = timezone.now()

            obj, created = WorkoutTip.objects.update_or_create(
                code=code,
                defaults={
                    "title": fields.get("title", code),
                    "slug": slug,
                    "thumbnail": featured_image_url or f"/assets/workout-tips/{slug}.jpg",
                    "featured_image_url": featured_image_url,
                    "youtube_url": youtube_url,
                    "category": fields.get("category") or "Beginner",
                    "overview": fields.get("overview") or "",
                    "why_it_matters": fields.get("whyItMatters") or fields.get("why_it_matters") or [],
                    "step_by_step_guide": fields.get("stepByStepGuide") or fields.get("step_by_step_guide") or [],
                    "common_mistakes": fields.get("commonMistakes") or fields.get("common_mistakes") or [],
                    "coach_tip": fields.get("coachTip") or fields.get("coach_tip") or "",
                    "key_takeaways": fields.get("keyTakeaways") or fields.get("key_takeaways") or [],
                    "related_articles": fields.get("relatedArticles") or fields.get("related_articles") or [],
                    "author": fields.get("author") or "RedIron Team",
                    "published_at": published_at,
                    "is_published": fields.get("is_published", True),
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
            if not obj.featured_image_url or str(obj.featured_image_url).startswith(("/assets/workout-tips/", "assets/workout-tips/")):
                obj.featured_image_url = matched_image_url(
                    obj,
                    WORKOUT_TIP_IMAGE_FALLBACKS,
                    "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=900&q=80",
                )
                obj.thumbnail = obj.featured_image_url
            obj.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Workout tips loaded. Created: {created_count}. Updated: {updated_count}. Total fixture rows: {len(tips)}."
            )
        )
