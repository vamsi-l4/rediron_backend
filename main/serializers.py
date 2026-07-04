import os
import re
from rest_framework import serializers
from django.conf import settings
from django.db import transaction

from .models import (
    Equipment, ContactMessage, NutritionArticle, WorkoutArticle,
    FitnessArticle, WorkoutTip, Exercise, MuscleGroup
)

NUTRITION_IMAGE_FALLBACKS = (
    ("whey", "https://images.unsplash.com/photo-1593095948071-474c5cc2989d?w=900&q=80"),
    ("protein", "https://images.unsplash.com/photo-1622484211148-b2f5a3e3d90b?w=900&q=80"),
    ("creatine", "https://images.unsplash.com/photo-1579722820308-d74e571900a9?w=900&q=80"),
    ("supplement", "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=900&q=80"),
    ("oats", "https://images.unsplash.com/photo-1517673132405-a56a62b18caf?w=900&q=80"),
    ("pancake", "https://images.unsplash.com/photo-1528207776546-365bb710ee93?w=900&q=80"),
    ("yogurt", "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=900&q=80"),
    ("banana", "https://images.unsplash.com/photo-1528825871115-3581a5387919?w=900&q=80"),
    ("egg", "https://images.unsplash.com/photo-1498654896293-37aacf113fd9?w=900&q=80"),
    ("chicken", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=900&q=80"),
    ("salmon", "https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=900&q=80"),
    ("smoothie", "https://images.unsplash.com/photo-1553530666-ba11a7da3888?w=900&q=80"),
    ("electrolyte", "https://images.unsplash.com/photo-1523362628745-0c100150b504?w=900&q=80"),
    ("vitamin", "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=900&q=80"),
    ("fat loss", "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=900&q=80"),
    ("bulking", "https://images.unsplash.com/photo-1550547660-d9450f859349?w=900&q=80"),
    ("meal", "https://images.unsplash.com/photo-1547592180-85f173990554?w=900&q=80"),
)

WORKOUT_TIP_IMAGE_FALLBACKS = (
    ("warm-up", "https://images.unsplash.com/photo-1518611012118-696072aa579a?w=900&q=80"),
    ("right-weight", "https://images.unsplash.com/photo-1534367610401-9f5ed68180aa?w=900&q=80"),
    ("progressive-overload", "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=900&q=80"),
    ("rest-days", "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=900&q=80"),
    ("rest-between-sets", "https://images.unsplash.com/photo-1599058917212-d750089bc07e?w=900&q=80"),
    ("squat", "https://images.unsplash.com/photo-1574680096145-d05b474e2155?w=900&q=80"),
    ("bench-press", "https://images.unsplash.com/photo-1532029837206-abbe2b7620e3?w=900&q=80"),
    ("deadlift", "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=900&q=80"),
    ("pull-up", "https://images.unsplash.com/photo-1598971639058-fab3c3109a00?w=900&q=80"),
    ("sleep", "https://images.unsplash.com/photo-1541781774459-bb2af2f05b55?w=900&q=80"),
    ("stretching", "https://images.unsplash.com/photo-1571019613576-2b22c76fd955?w=900&q=80"),
    ("hydration", "https://images.unsplash.com/photo-1523362628745-0c100150b504?w=900&q=80"),
    ("injuries", "https://images.unsplash.com/photo-1571019613914-85f342c6a11e?w=900&q=80"),
    ("compound", "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=900&q=80"),
    ("failure", "https://images.unsplash.com/photo-1517963879433-6ad2b056d712?w=900&q=80"),
    ("tempo", "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=900&q=80"),
    ("deload", "https://images.unsplash.com/photo-1571902943202-507ec2618e8f?w=900&q=80"),
    ("plateaus", "https://images.unsplash.com/photo-1546483875-ad9014c88eba?w=900&q=80"),
)


def matched_image_url(obj, mapping, default_url):
    text = f"{getattr(obj, 'slug', '')} {getattr(obj, 'title', '')} {getattr(obj, 'category', '')}".lower()
    for keyword, image_url in mapping:
        if keyword in text:
            return image_url
    return default_url

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
        return matched_image_url(obj, NUTRITION_IMAGE_FALLBACKS, "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=900&q=80")


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
        return matched_image_url(obj, WORKOUT_TIP_IMAGE_FALLBACKS, "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=900&q=80")

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
    thumbnail = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
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
            "id", "title", "slug", "thumbnail", "image_url", "featured_image_url", "youtubeUrl", "category",
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

    def get_thumbnail(self, obj):
        return self.get_image_url(obj)

    def get_image_url(self, obj):
        request = self.context.get("request", None)
        if obj.featured_image and hasattr(obj.featured_image, "url"):
            url = obj.featured_image.url
            return request.build_absolute_uri(url) if request else url
        if obj.featured_image_url:
            return obj.featured_image_url
        current = obj.thumbnail or ""
        if current.startswith("http"):
            return current
        return matched_image_url(obj, WORKOUT_TIP_IMAGE_FALLBACKS, "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=900&q=80")


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
        return matched_image_url(obj, WORKOUT_TIP_IMAGE_FALLBACKS, "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=900&q=80")

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


