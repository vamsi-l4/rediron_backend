import os
import re
from rest_framework import serializers
from django.conf import settings
from django.db import transaction

from .models import (
    Equipment, ContactMessage, NutritionArticle, WorkoutArticle,
    FitnessArticle, WorkoutTip, Exercise, MuscleGroup
)

# ---------- BASE SERIALIZER FOR REUSABLE LOGIC ----------
class BaseImageSerializer(serializers.ModelSerializer):
    """
    A base serializer to handle common image URL generation logic.
    """
    def _absolute_url(self, request, url_path):
        """
        Helper: build absolute URL if request present, otherwise return plain path.
        """
        if not url_path:
            return None
        if request:
            return request.build_absolute_uri(url_path)
        return url_path

    def _build_media_url(self, filename):
        if not filename:
            return None
        if filename.startswith("http"):
            return filename
        return os.path.join(settings.MEDIA_URL, filename).replace('\\\\', '/')

class EquipmentSerializer(BaseImageSerializer):
    image = serializers.SerializerMethodField()
    image1 = serializers.SerializerMethodField()
    image2 = serializers.SerializerMethodField()
    image3 = serializers.SerializerMethodField()
    image4 = serializers.SerializerMethodField()
    image_urls = serializers.SerializerMethodField()

    _EQUIPMENT_PREFIX_OVERRIDES = {
        "Commercial Treadmill": "Threadmill",
        "Manual Treadmill": "ManualThreadmill",
        "Rear Delt Machine (Reverse Pec Deck)": "PecDeckMachine",
        "Preacher Curl Machine": "BicepCurlMachine",
        "Functional Trainer": "CableMachine",
    }

    class Meta:
        model = Equipment
        fields = [
            "id", "name", "image", "usage", "video_link", "category",
            "key_features", "specifications", "benefits", "perfect_for", "additional_stats",
            "image1", "image2", "image3", "image4", "image_urls",
        ]

    def get_image(self, obj):
        request = self.context.get("request", None)
        if obj.image and hasattr(obj.image, "url"):
            return self._absolute_url(request, obj.image.url)
        return None

    def _normalize_equipment_prefix(self, value):
        if not value:
            return ""
        return re.sub(r"[^A-Za-z0-9]", "", value).lower()

    def _equipment_prefixes(self):
        if not hasattr(self, "_equipment_prefix_cache"):
            self._equipment_prefix_cache = set()
            equipment_dir = os.path.join(settings.MEDIA_ROOT, "equipment")
            if os.path.isdir(equipment_dir):
                for filename in os.listdir(equipment_dir):
                    if os.path.isfile(os.path.join(equipment_dir, filename)) and filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                        # Extract prefix by removing trailing digits
                        base = os.path.splitext(filename)[0]
                        # Remove trailing digits to get the base name
                        prefix = re.sub(r'\d+$', '', base)
                        if prefix:
                            self._equipment_prefix_cache.add(prefix)
        return list(self._equipment_prefix_cache)

    def _find_equipment_prefix(self, obj):
        if not obj.name:
            return None

        if obj.name in self._EQUIPMENT_PREFIX_OVERRIDES:
            return self._EQUIPMENT_PREFIX_OVERRIDES[obj.name]

        candidate = obj.name.split("(")[0].strip()
        candidate_variants = set()
        candidate_variants.add(candidate)
        candidate_variants.add(candidate.replace("-", ""))
        candidate_variants.add(re.sub(r"(Machine|Bench|Rack|Trainer|Chair|Station|Ball|Board)$", "", candidate).strip())
        candidate_variants.add(re.sub(r"[^A-Za-z0-9]", "", candidate))
        candidate_variants.add(re.sub(r"[^A-Za-z0-9]", "", candidate.replace("-", "")))

        normalized_candidates = {self._normalize_equipment_prefix(value) for value in candidate_variants if value}
        if not normalized_candidates:
            return None

        for prefix in self._equipment_prefixes():
            normalized_prefix = self._normalize_equipment_prefix(prefix)
            if any(
                normalized_prefix == candidate_norm or
                normalized_prefix.startswith(candidate_norm) or
                candidate_norm.startswith(normalized_prefix)
                for candidate_norm in normalized_candidates
            ):
                return prefix
        return None

    def _equipment_filename(self, obj, index):
        prefix = self._find_equipment_prefix(obj)
        if not prefix:
            return None

        for extension in ("png", "jpg", "jpeg", "webp"):
            filename = f"{prefix}{index}.{extension}"
            file_path = os.path.join(settings.MEDIA_ROOT, "equipment", filename)
            if os.path.exists(file_path):
                return f"equipment/{filename}"
        return None

    def _equipment_url(self, obj, index):
        filename = self._equipment_filename(obj, index)
        request = self.context.get("request", None)
        if filename:
            return self._absolute_url(request, f"{settings.MEDIA_URL}{filename}")

        # Fallback to the saved image for all image slots when explicit equipment files are absent
        if obj.image and hasattr(obj.image, "url"):
            return self._absolute_url(request, obj.image.url)

        return None

    def get_image1(self, obj):
        return self._equipment_url(obj, 1)

    def get_image2(self, obj):
        return self._equipment_url(obj, 2)

    def get_image3(self, obj):
        return self._equipment_url(obj, 3)

    def get_image4(self, obj):
        return self._equipment_url(obj, 4)

    def get_image_urls(self, obj):
        request = self.context.get("request", None)
        urls = []
        primary = self.get_image(obj)
        if primary:
            urls.append(primary)
        for index in range(1, 5):
            candidate = self._equipment_url(obj, index)
            if candidate and candidate not in urls:
                urls.append(candidate)
        return urls


# ---------- CONTACT ----------
class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = "__all__"
        read_only_fields = ("created_at",)


# ---------- NUTRITION ARTICLE ----------
class NutritionArticleSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    reading_time = serializers.IntegerField(read_only=True)
    content = serializers.SerializerMethodField()

    class Meta:
        model = NutritionArticle
        fields = (
            "id", "title", "slug", "category", "excerpt", "video_url", "content",
            "image_url", "featured_image_url", "author", "reading_time",
            "published_at", "featured", "created_at", "updated_at",
            "tags", "is_published", "references",
        )
        read_only_fields = ("id", "slug", "reading_time", "created_at", "updated_at")

    def get_content(self, obj):
        return obj.content

    def _absolute_url(self, request, url_path):
        """
        Helper: build absolute URL if request present, otherwise return plain path.
        """
        if not url_path:
            return None
        if request:
            return request.build_absolute_uri(url_path)
        return url_path

    def get_image_url(self, obj):
        request = self.context.get("request", None)
        if obj.featured_image and hasattr(obj.featured_image, 'url'):
            image_path = str(obj.featured_image)
            if image_path.startswith('/media/'):
                return self._absolute_url(request, image_path)
            return self._absolute_url(request, obj.featured_image.url)

        if obj.featured_image_url:
            return obj.featured_image_url
        return None


# ---------- WORKOUT ARTICLE ----------
class WorkoutArticleSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    reading_time = serializers.IntegerField(read_only=True)

    class Meta:
        model = WorkoutArticle
        fields = (
            "id", "title", "slug", "category", "excerpt", "content",
            "image_url", "featured_image_url", "author", "reading_time",
            "published_at", "featured", "created_at", "updated_at",
            "tags", "is_published",
        )
        read_only_fields = ("id", "slug", "reading_time", "created_at", "updated_at")

    def _absolute_url(self, request, url_path):
        if not url_path:
            return None
        if request:
            return request.build_absolute_uri(url_path)
        return url_path

    def get_image_url(self, obj):
        request = self.context.get("request", None)
        if obj.featured_image and hasattr(obj.featured_image, 'url'):
            image_path = str(obj.featured_image)
            if image_path.startswith('/media/'):
                return self._absolute_url(request, image_path)
            return self._absolute_url(request, obj.featured_image.url)

        if obj.featured_image_url:
            return obj.featured_image_url
        return None


# ---------- FITNESS ARTICLE ----------
class FitnessArticleSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="code", read_only=True)
    image_url = serializers.SerializerMethodField()
    featuredImage = serializers.SerializerMethodField()
    coachInsight = serializers.CharField(allow_blank=True)
    videoTitle = serializers.CharField(allow_blank=True)
    youtubeUrl = serializers.URLField(allow_blank=True)
    excerpt = serializers.SerializerMethodField()
    reading_time = serializers.IntegerField(read_only=True)

    class Meta:
        model = FitnessArticle
        fields = (
            "id", "title", "slug", "category", "image_url", "featuredImage",
            "featured_image_url", "author", "overview", "excerpt", "coreConcepts",
            "whyItMatters", "scienceExplained", "practicalApplication", "commonMyths",
            "coachInsight", "keyTakeaways", "videoTitle", "youtubeUrl", "relatedArticles",
            "published_at", "reading_time", "is_published", "created_at", "updated_at",
        )
        read_only_fields = ("created_at", "updated_at", "reading_time")

    def _absolute_url(self, request, url_path):
        if not url_path:
            return None
        if request:
            return request.build_absolute_uri(url_path)
        return url_path

    def get_image_url(self, obj):
        request = self.context.get("request", None)
        if obj.featured_image and hasattr(obj.featured_image, "url"):
            return self._absolute_url(request, obj.featured_image.url)
        if obj.featured_image_url:
            return obj.featured_image_url
        return None

    def get_featuredImage(self, obj):
        return {
            "imageFile": obj.featured_image.url if obj.featured_image and hasattr(obj.featured_image, "url") else "",
            "imageUrl": self.get_image_url(obj) or "",
        }

    def get_excerpt(self, obj):
        if not obj.overview:
            return ""
        clean = " ".join(str(obj.overview).split())
        return clean[:180] + "..." if len(clean) > 180 else clean


# ---------- WORKOUT TIP ----------
class WorkoutTipSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="code", read_only=True)
    youtubeUrl = serializers.URLField(source="youtube_url", required=False, allow_blank=True)
    whyItMatters = serializers.JSONField(source="why_it_matters")
    stepByStepGuide = serializers.JSONField(source="step_by_step_guide")
    commonMistakes = serializers.JSONField(source="common_mistakes")
    coachTip = serializers.CharField(source="coach_tip", allow_blank=True)
    keyTakeaways = serializers.JSONField(source="key_takeaways")
    relatedArticles = serializers.JSONField(source="related_articles")
    excerpt = serializers.SerializerMethodField()

    class Meta:
        model = WorkoutTip
        fields = (
            "id", "title", "slug", "thumbnail", "youtubeUrl", "category",
            "overview", "whyItMatters", "stepByStepGuide", "commonMistakes",
            "coachTip", "keyTakeaways", "relatedArticles", "excerpt",
            "author", "published_at", "reading_time", "is_published",
            "created_at", "updated_at",
        )
        read_only_fields = ("created_at", "updated_at", "reading_time")

    def get_excerpt(self, obj):
        if not obj.overview:
            return ""
        return obj.overview[:156] + "..." if len(obj.overview) > 156 else obj.overview


# ---------- SUPPORTING SERIALIZERS ----------
class MuscleGroupSerializer(serializers.ModelSerializer):
    parent = serializers.SerializerMethodField()

    class Meta:
        model = MuscleGroup
        fields = ["id", "name", "slug", "body_region", "parent"]

    def get_parent(self, obj):
        if not obj.parent:
            return None
        return {"id": obj.parent_id, "name": obj.parent.name, "slug": obj.parent.slug}


class EquipmentSimpleSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    image1 = serializers.SerializerMethodField()
    image_urls = serializers.SerializerMethodField()

    class Meta:
        model = Equipment
        fields = ["id", "name", "category", "image", "image1", "image_urls"]

    def _absolute_url(self, url_path):
        if not url_path:
            return None
        request = self.context.get("request", None)
        if request:
            return request.build_absolute_uri(url_path)
        return url_path

    def get_image(self, obj):
        if obj.image and hasattr(obj.image, "url"):
            return self._absolute_url(obj.image.url)
        return None

    def get_image1(self, obj):
        return self.get_image(obj)

    def get_image_urls(self, obj):
        image = self.get_image(obj)
        return [image] if image else []


# ---------- EXERCISE ----------
class ExerciseSerializer(serializers.ModelSerializer):
    primary_muscles = MuscleGroupSerializer(many=True, read_only=True)
    secondary_muscles = MuscleGroupSerializer(many=True, read_only=True)
    equipment = EquipmentSimpleSerializer(many=True, read_only=True)

    primary_muscle_ids = serializers.PrimaryKeyRelatedField(
        queryset=MuscleGroup.objects.all(), many=True, write_only=True,
        source="primary_muscles", required=False
    )
    secondary_muscle_ids = serializers.PrimaryKeyRelatedField(
        queryset=MuscleGroup.objects.all(), many=True, write_only=True,
        source="secondary_muscles", required=False
    )
    equipment_ids = serializers.PrimaryKeyRelatedField(
        queryset=Equipment.objects.all(), many=True, write_only=True,
        source="equipment", required=False
    )

    image = serializers.SerializerMethodField()
    featured_image = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    video_url = serializers.URLField(required=False, allow_blank=True)
    youtube_url = serializers.URLField(required=False, allow_blank=True)
    difficulty = serializers.SerializerMethodField()
    title = serializers.CharField(source="name", read_only=True)

    class Meta:
        model = Exercise
        fields = [
            "id", "code", "title", "name", "slug", "muscle_group", "subcategory",
            "description", "content", "benefits", "how_to_perform", "variations",
            "common_mistakes", "sample_30_day_challenge", "tips", "related_exercises",
            "primary_muscles", "secondary_muscles", "equipment",
            "video_url", "youtube_url", "image", "featured_image", "featured_image_url",
            "skill_level", "difficulty", "exercise_type",
            "primary_muscle_ids", "secondary_muscle_ids", "equipment_ids",
        ]
        read_only_fields = ("slug",)

    def _absolute_url(self, request, url_path):
        if not url_path:
            return None
        if request:
            return request.build_absolute_uri(url_path)
        return url_path

    def get_image(self, obj):
        request = self.context.get("request", None)
        if obj.image and hasattr(obj.image, 'url'):
            image_path = str(obj.image)
            if image_path.startswith('/media/'):
                return self._absolute_url(request, image_path)
            return self._absolute_url(request, obj.image.url)
        if obj.featured_image_url:
            return obj.featured_image_url
        return None

    def get_featured_image(self, obj):
        return self.get_image(obj)

    def get_difficulty(self, obj):
        return obj.get_skill_level_display() if obj.skill_level else ""

    def get_content(self, obj):
        return obj.content

    def create(self, validated_data):
        primary = validated_data.pop("primary_muscles", [])
        secondary = validated_data.pop("secondary_muscles", [])
        equipment = validated_data.pop("equipment", [])
        exercise = Exercise.objects.create(**validated_data)
        if primary:
            exercise.primary_muscles.set(primary)
        if secondary:
            exercise.secondary_muscles.set(secondary)
        if equipment:
            exercise.equipment.set(equipment)
        return exercise

    def update(self, instance, validated_data):
        primary = validated_data.pop("primary_muscles", None)
        secondary = validated_data.pop("secondary_muscles", None)
        equipment = validated_data.pop("equipment", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if primary is not None:
            instance.primary_muscles.set(primary)
        if secondary is not None:
            instance.secondary_muscles.set(secondary)
        if equipment is not None:
            instance.equipment.set(equipment)
        return instance


# ============================================
# REDIRON PERFORMANCE LAB - SERIALIZERS
# ============================================

class ExerciseLogSerializer(serializers.Serializer):
    """Serializer for individual exercise logs (nested in WorkoutSession)."""
    id = serializers.IntegerField(read_only=True)
    exercise_name = serializers.CharField(max_length=200)
    sets = serializers.IntegerField(min_value=1)
    reps = serializers.IntegerField(min_value=1)
    weight = serializers.FloatField(min_value=0)
    calculated_1rm = serializers.FloatField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class WorkoutSessionSerializer(serializers.Serializer):
    """
    Serializer for workout sessions with nested exercises.
    Optimized for performance with minimal database queries.
    """
    id = serializers.IntegerField(read_only=True)
    clerk_user_id = serializers.CharField(read_only=True)
    date = serializers.DateField()
    duration = serializers.IntegerField(min_value=1)
    total_volume = serializers.FloatField(read_only=True)
    exercises = ExerciseLogSerializer(many=True, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        """Create a new workout session."""
        from .models import WorkoutSession
        return WorkoutSession.objects.create(**validated_data)


class BodyMetricsSerializer(serializers.Serializer):
    """Serializer for body composition metrics."""
    id = serializers.IntegerField(read_only=True)
    clerk_user_id = serializers.CharField(read_only=True)
    weight = serializers.FloatField(min_value=0)
    body_fat = serializers.FloatField(allow_null=True, required=False)
    recorded_at = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        """Create a new body metrics record."""
        from .models import BodyMetrics
        return BodyMetrics.objects.create(**validated_data)


class NutritionLogSerializer(serializers.Serializer):
    """Serializer for daily nutrition logs."""
    id = serializers.IntegerField(read_only=True)
    clerk_user_id = serializers.CharField(read_only=True)
    date = serializers.DateField()
    calories = serializers.IntegerField(min_value=0)
    protein = serializers.FloatField(min_value=0)
    carbs = serializers.FloatField(min_value=0)
    fat = serializers.FloatField(min_value=0)
    water = serializers.FloatField(min_value=0)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        """Create a new nutrition log."""
        from .models import NutritionLog
        return NutritionLog.objects.create(**validated_data)


class UserGoalSerializer(serializers.Serializer):
    """Serializer for user fitness goals."""
    id = serializers.IntegerField(read_only=True)
    clerk_user_id = serializers.CharField(read_only=True)
    goal_type = serializers.ChoiceField(
        choices=['fat_loss', 'muscle_gain', 'strength', 'endurance']
    )
    target_value = serializers.FloatField(allow_null=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        """Create a new user goal."""
        from .models import UserGoal
        return UserGoal.objects.create(**validated_data)


class PerformanceDashboardSerializer(serializers.Serializer):
    """
    Serializer for comprehensive performance dashboard data.
    Combines all analytics into a single response.
    """
    strength_score = serializers.DictField(read_only=True)
    weekly_volume = serializers.DictField(read_only=True)
    body_metrics_trend = serializers.DictField(read_only=True)
    calorie_balance = serializers.DictField(read_only=True)
    training_streak = serializers.DictField(read_only=True)
    recommendations = serializers.ListField(read_only=True)
    current_goal = UserGoalSerializer(read_only=True, required=False)
    last_updated = serializers.DateTimeField(read_only=True)


class RecommendationSerializer(serializers.Serializer):
    """Serializer for AI-generated workout recommendations."""
    recommendation_type = serializers.CharField(
        help_text="Type of recommendation (e.g., 'workout_split', 'nutrition', 'recovery')"
    )
    content = serializers.DictField(help_text="Structured recommendation content from OpenAI")
    generated_at = serializers.DateTimeField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)
