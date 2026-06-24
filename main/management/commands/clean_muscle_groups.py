import re

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from main.models import Exercise, MuscleGroup, NutritionArticle


MUSCLE_TREE = {
    "Chest": ["Upper Chest", "Middle Chest", "Lower Chest"],
    "Back": ["Lats", "Mid Back", "Traps", "Erector Spinae"],
    "Shoulders": ["Front Delts", "Side Delts", "Rear Delts"],
    "Legs": ["Quads", "Hamstrings", "Glutes", "Calves"],
    "Biceps": ["Long Head", "Short Head", "Brachialis"],
    "Triceps": ["Long Head", "Lateral Head", "Medial Head"],
    "Forearms": ["Brachioradialis", "Wrist Flexors", "Wrist Extensors"],
    "Abs": ["Upper Abs", "Lower Abs", "Obliques", "Static Core"],
    "Cardio": ["Treadmill", "Cycling", "Rowing", "HIIT", "Jump Rope", "Stair Climber"],
}

VIDEO_URL_RE = re.compile(
    r'(https?://(?:www\.)?(?:youtube\.com/watch\?v=[A-Za-z0-9_-]+|youtu\.be/[A-Za-z0-9_-]+|youtube\.com/embed/[A-Za-z0-9_-]+|vimeo\.com/[0-9]+)(?:[^\s"<]*)?)',
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
    help = "Rebuild RedIron exercise muscle groups and extract NutritionArticle video URLs."

    def handle(self, *args, **options):
        with transaction.atomic():
            existing_primary = {
                exercise.id: list(exercise.primary_muscles.values_list("name", flat=True))
                for exercise in Exercise.objects.prefetch_related("primary_muscles")
            }
            existing_secondary = {
                exercise.id: list(exercise.secondary_muscles.values_list("name", flat=True))
                for exercise in Exercise.objects.prefetch_related("secondary_muscles")
            }

            MuscleGroup.objects.all().delete()
            created_groups = {}

            for parent_name, children in MUSCLE_TREE.items():
                parent = MuscleGroup.objects.create(
                    name=parent_name,
                    slug=slugify(parent_name),
                    body_region=slugify(parent_name),
                )
                created_groups[parent_name.lower()] = parent
                for child_name in children:
                    child = MuscleGroup.objects.create(
                        name=child_name,
                        slug=f"{parent.slug}-{slugify(child_name)}",
                        parent=parent,
                        body_region=parent.body_region,
                    )
                    created_groups[child_name.lower()] = child

            for exercise in Exercise.objects.all():
                primary_names = existing_primary.get(exercise.id) or [exercise.subcategory, exercise.muscle_group]
                secondary_names = existing_secondary.get(exercise.id) or []
                primary_groups = [created_groups[name.lower()] for name in primary_names if name and name.lower() in created_groups]
                secondary_groups = [created_groups[name.lower()] for name in secondary_names if name and name.lower() in created_groups]
                if primary_groups:
                    exercise.primary_muscles.set(primary_groups)
                if secondary_groups:
                    exercise.secondary_muscles.set(secondary_groups)

            updated_articles = 0
            for article in NutritionArticle.objects.all():
                if article.video_url:
                    continue
                candidate = scan_for_video(article.content) or find_video_url(article.excerpt) or find_video_url(article.title)
                if candidate:
                    article.video_url = candidate
                    article.save(update_fields=["video_url", "updated_at"])
                    updated_articles += 1

        self.stdout.write(self.style.SUCCESS("Muscle groups rebuilt for Exercise Library."))
        self.stdout.write(self.style.SUCCESS(
            f"Nutrition articles updated with related video URLs: {updated_articles}."
        ))
