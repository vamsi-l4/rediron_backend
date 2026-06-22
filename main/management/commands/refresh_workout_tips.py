import json
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from main.models import WorkoutTip


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

        for index, tip in enumerate(tips, start=1):
            code = tip.get("id") or tip.get("code") or f"WT{index:02d}"
            slug = tip.get("slug") or str(tip.get("title", code)).lower().replace(" ", "-")
            youtube_url = tip.get("youtubeUrl") or ""
            published_at = tip.get("published_at") or tip.get("date")
            if isinstance(published_at, str):
                published_at = parse_datetime(published_at)
            if not published_at:
                published_at = timezone.now()

            obj, created = WorkoutTip.objects.update_or_create(
                code=code,
                defaults={
                    "title": tip.get("title", code),
                    "slug": slug,
                    "thumbnail": tip.get("thumbnail") or f"/assets/workout-tips/{slug}.jpg",
                    "youtube_url": youtube_url,
                    "category": tip.get("category") or "Beginner",
                    "overview": tip.get("overview") or "",
                    "why_it_matters": tip.get("whyItMatters") or [],
                    "step_by_step_guide": tip.get("stepByStepGuide") or [],
                    "common_mistakes": tip.get("commonMistakes") or [],
                    "coach_tip": tip.get("coachTip") or "",
                    "key_takeaways": tip.get("keyTakeaways") or [],
                    "related_articles": tip.get("relatedArticles") or [],
                    "author": tip.get("author") or "RedIron Team",
                    "published_at": published_at,
                    "is_published": tip.get("is_published", True),
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
            obj.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Workout tips loaded. Created: {created_count}. Updated: {updated_count}. Total fixture rows: {len(tips)}."
            )
        )
