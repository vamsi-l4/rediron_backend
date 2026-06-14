import re
from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from main.models import Exercise, MuscleGroup, NutritionArticle, Workout


VIDEO_URL_RE = re.compile(
    r"(https?://(?:www\.)?(?:youtube\.com/watch\?v=[A-Za-z0-9_-]+|youtu\.be/[A-Za-z0-9_-]+|youtube\.com/embed/[A-Za-z0-9_-]+|vimeo\.com/[0-9]+)(?:[^"]*))",
    re.IGNORECASE,
)


def find_video_url(text):
    if not text or not isinstance(text, str):
        return None
    match = VIDEO_URL_RE.search(text)
    return match.group(1) if match else None


def scan_for_video(obj):
    if isinstance(obj, str):
        return find_video_url(obj)
    if isinstance(obj, dict):
        for value in obj.values():
            candidate = scan_for_video(value)
            if candidate:
                return candidate
    if isinstance(obj, list):
        for item in obj:
            candidate = scan_for_video(item)
            if candidate:
                return candidate
    return None


class Command(BaseCommand):
    help = (
        "Rename bad muscle groups and optionally extract NutritionArticle video URLs "
        "from existing content."
    )

    def handle(self, *args, **options):
        rename_map = {
            "Extra Group 7": "Biceps",
            "Extra Group 8": "Triceps",
            "Extra Group 9": "Forearms",
        }

        with transaction.atomic():
            for old_name, new_name in rename_map.items():
                try:
                    old_group = MuscleGroup.objects.get(name=old_name)
                except MuscleGroup.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Missing muscle group: {old_name}."))
                    continue

                target_group, created = MuscleGroup.objects.get_or_create(
                    name=new_name,
                    defaults={"slug": slugify(new_name)},
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f"Created new muscle group: {new_name}"))

                exercise_qs = Exercise.objects.filter(primary_muscles=old_group)
                for exercise in exercise_qs:
                    exercise.primary_muscles.add(target_group)
                    exercise.primary_muscles.remove(old_group)

                exercise_qs = Exercise.objects.filter(secondary_muscles=old_group)
                for exercise in exercise_qs:
                    exercise.secondary_muscles.add(target_group)
                    exercise.secondary_muscles.remove(old_group)

                workout_qs = Workout.objects.filter(muscle_groups=old_group)
                for workout in workout_qs:
                    workout.muscle_groups.add(target_group)
                    workout.muscle_groups.remove(old_group)

                old_group.delete()
                self.stdout.write(self.style.SUCCESS(f"Replaced '{old_name}' with '{new_name}'."))

            updated_articles = 0
            for article in NutritionArticle.objects.all():
                if article.video_url:
                    continue
                candidate = scan_for_video(article.content) or find_video_url(article.excerpt) or find_video_url(article.title)
                if candidate:
                    article.video_url = candidate
                    article.save(update_fields=["video_url", "updated_at"])
                    updated_articles += 1

            self.stdout.write(self.style.SUCCESS(
                f"Nutrition articles updated with related video URLs: {updated_articles}."
            ))
