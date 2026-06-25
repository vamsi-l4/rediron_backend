import json
import os
import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from main.models import Equipment, Exercise, MuscleGroup


EXERCISE_TYPE_MAP = {
    "compound": "strength",
    "strength": "strength",
    "cardio": "cardio",
    "cardiovascular": "cardio",
    "mobility": "mobility",
    "functional": "functional",
    "isolation": "isolation",
    "hypertrophy": "hypertrophy",
}

SKILL_LEVELS = {"beginner", "intermediate", "advanced"}
MUSCLE_GROUPS = {choice[0] for choice in Exercise.MUSCLE_GROUP_CHOICES}
PRODUCTION_MEDIA_BASE = "https://rediron-backend-1.onrender.com/media/exercises"
MUSCLE_REGION_HINTS = {
    "Chest": ("pectoral", "chest", "serratus"),
    "Back": ("latissimus", "rhomboid", "trapezius", "erector", "teres", "levator", "infraspinatus", "supraspinatus"),
    "Shoulders": ("deltoid", "shoulder"),
    "Legs": (
        "quadriceps", "rectus femoris", "glute", "hamstring", "biceps femoris", "semitendinosus",
        "semimembranosus", "gastrocnemius", "soleus", "adductor", "hip flexor", "iliopsoas",
        "piriformis", "tensor fasciae", "popliteus", "tibialis",
    ),
    "Biceps": ("biceps brachii", "brachialis", "coracobrachialis"),
    "Triceps": ("triceps", "anconeus"),
    "Forearms": ("forearm", "brachioradialis", "flexor", "extensor", "palmaris"),
    "Abs": ("rectus abdominis", "oblique", "transverse abdominis", "core"),
}


def normalize_key(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


class Command(BaseCommand):
    help = "Replace old Exercise rows with normalized records from main/fixtures/exercise_videos.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            default=os.path.join(settings.BASE_DIR, "main", "fixtures", "exercise_videos.json"),
            help="Path to the exercise video JSON fixture.",
        )
        parser.add_argument(
            "--keep-existing",
            action="store_true",
            help="Update/create fixture exercises without deleting existing Exercise rows first.",
        )

    def handle(self, *args, **options):
        records = self.load_records(options["fixture"])
        self.validate_records(records)

        with transaction.atomic():
            if not options["keep_existing"]:
                Exercise.objects.all().delete()

            equipment_by_key = {
                normalize_key(item.name): item
                for item in Equipment.objects.all()
            }
            muscle_by_key = {
                (normalize_key(item.name), item.parent_id): item
                for item in MuscleGroup.objects.select_related("parent")
            }

            imported = 0
            for record in records:
                exercise = self.upsert_exercise(record, equipment_by_key, muscle_by_key)
                imported += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {imported} exercises from exercise_videos.json."))
        self.stdout.write(self.style.SUCCESS(f"Exercise table now contains {Exercise.objects.count()} rows."))

    def load_records(self, fixture_path):
        if not os.path.exists(fixture_path):
            raise CommandError(f"Fixture not found: {fixture_path}")
        with open(fixture_path, "r", encoding="utf-8") as fixture_file:
            data = json.load(fixture_file)
        if not isinstance(data, list):
            raise CommandError("exercise_videos.json must contain a JSON list.")
        return data

    def validate_records(self, records):
        seen_codes = set()
        seen_slugs = set()
        codes = {str(item.get("code") or item.get("id") or "").strip() for item in records}
        errors = []

        for index, record in enumerate(records, start=1):
            code = str(record.get("code") or record.get("id") or "").strip()
            name = str(record.get("name") or record.get("title") or "").strip()
            slug = str(record.get("slug") or slugify(name)).strip()
            muscle_group = record.get("muscle_group")
            skill_level = self.normalize_skill(record.get("skill_level") or record.get("difficulty"))
            exercise_type = self.normalize_type(record.get("exercise_type"))

            if not code:
                errors.append(f"Row {index}: missing code")
            if not name:
                errors.append(f"{code or index}: missing name")
            if code in seen_codes:
                errors.append(f"{code}: duplicate code")
            if slug in seen_slugs:
                errors.append(f"{code}: duplicate slug {slug}")
            if muscle_group not in MUSCLE_GROUPS:
                errors.append(f"{code}: invalid muscle_group {muscle_group!r}")
            if skill_level not in SKILL_LEVELS:
                errors.append(f"{code}: invalid skill_level {record.get('skill_level')!r}")
            if exercise_type not in dict(Exercise.TYPE_CHOICES):
                errors.append(f"{code}: invalid exercise_type {record.get('exercise_type')!r}")

            for related_code in record.get("related_exercises") or []:
                if related_code not in codes:
                    errors.append(f"{code}: related exercise {related_code} is missing")

            seen_codes.add(code)
            seen_slugs.add(slug)

        if errors:
            joined = "\n".join(errors[:50])
            if len(errors) > 50:
                joined += f"\n...and {len(errors) - 50} more errors"
            raise CommandError(joined)

    def upsert_exercise(self, record, equipment_by_key, muscle_by_key):
        code = str(record.get("code") or record.get("id")).strip()
        name = str(record.get("name") or record.get("title")).strip()
        image = str(record.get("image") or "").strip()
        featured_image_url = str(record.get("featured_image_url") or "").strip()
        if image and not featured_image_url:
            featured_image_url = f"{PRODUCTION_MEDIA_BASE}/{os.path.basename(image)}"

        defaults = {
            "name": name,
            "slug": str(record.get("slug") or slugify(name)).strip(),
            "muscle_group": record.get("muscle_group"),
            "subcategory": record.get("subcategory") or "",
            "description": record.get("description") or "",
            "video_url": record.get("video_url") or "",
            "youtube_url": record.get("youtube_url") or "",
            "image": image,
            "featured_image_url": featured_image_url,
            "skill_level": self.normalize_skill(record.get("skill_level") or record.get("difficulty")),
            "exercise_type": self.normalize_type(record.get("exercise_type")),
            "benefits": record.get("benefits") or [],
            "how_to_perform": record.get("how_to_perform") or [],
            "variations": record.get("variations") or [],
            "common_mistakes": record.get("common_mistakes") or [],
            "sample_30_day_challenge": record.get("sample_30_day_challenge") or [],
            "tips": record.get("tips") or [],
            "related_exercises": record.get("related_exercises") or [],
            "content": record.get("content") or None,
        }

        exercise, _ = Exercise.objects.update_or_create(code=code, defaults=defaults)

        primary = [
            self.get_or_create_muscle(name, defaults["muscle_group"], muscle_by_key)
            for name in record.get("primary_muscles") or []
        ]
        secondary = [
            self.get_or_create_muscle(name, defaults["muscle_group"], muscle_by_key)
            for name in record.get("secondary_muscles") or []
        ]
        equipment = self.get_or_create_equipment(record.get("equipment"), defaults["muscle_group"], equipment_by_key)

        exercise.primary_muscles.set([item for item in primary if item])
        exercise.secondary_muscles.set([item for item in secondary if item])
        exercise.equipment.set([equipment] if equipment else [])
        return exercise

    def get_or_create_muscle(self, name, body_region, muscle_by_key):
        if not name:
            return None

        body_region = self.infer_body_region(name, body_region)
        parent = self.get_or_create_parent_muscle(body_region, muscle_by_key)
        exact_key = (normalize_key(name), parent.id if parent else None)
        if exact_key in muscle_by_key:
            return muscle_by_key[exact_key]

        existing = MuscleGroup.objects.filter(name=name).first()
        if existing:
            updates = {}
            if existing.parent_id != (parent.id if parent else None):
                updates["parent"] = parent
            if existing.body_region != slugify(body_region):
                updates["body_region"] = slugify(body_region)
            if updates:
                for field, value in updates.items():
                    setattr(existing, field, value)
                existing.save(update_fields=[*updates.keys()])
            muscle_by_key[(normalize_key(existing.name), existing.parent_id)] = existing
            return existing

        muscle = MuscleGroup.objects.create(
            name=name,
            slug=f"{slugify(body_region)}-{slugify(name)}"[:120],
            parent=parent,
            body_region=slugify(body_region),
        )
        muscle_by_key[(normalize_key(muscle.name), muscle.parent_id)] = muscle
        return muscle

    def get_or_create_parent_muscle(self, body_region, muscle_by_key):
        key = (normalize_key(body_region), None)
        if key in muscle_by_key:
            return muscle_by_key[key]
        muscle, _ = MuscleGroup.objects.get_or_create(
            name=body_region,
            parent=None,
            defaults={"slug": slugify(body_region), "body_region": slugify(body_region)},
        )
        muscle_by_key[(normalize_key(muscle.name), muscle.parent_id)] = muscle
        return muscle

    def get_or_create_equipment(self, name, muscle_group, equipment_by_key):
        if not name:
            return None
        key = normalize_key(name)
        if key in equipment_by_key:
            return equipment_by_key[key]

        category = "cardio" if muscle_group == "Cardio" else "strength"
        equipment = Equipment.objects.create(name=name, category=category)
        equipment_by_key[key] = equipment
        return equipment

    def normalize_skill(self, value):
        text = str(value or "beginner").strip().lower()
        return text if text in SKILL_LEVELS else "beginner"

    def normalize_type(self, value):
        text = str(value or "strength").strip().lower()
        return EXERCISE_TYPE_MAP.get(text, "strength")

    def infer_body_region(self, muscle_name, fallback):
        text = normalize_key(muscle_name)
        for region, hints in MUSCLE_REGION_HINTS.items():
            if any(hint in text for hint in hints):
                return region
        return fallback
