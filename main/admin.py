from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Equipment, ContactMessage,
    NutritionArticle, WorkoutArticle, FitnessArticle, WorkoutTip,
    MuscleGroup, Exercise, Workout, WorkoutExercise
)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    list_filter = ("category",)
    search_fields = ("name",)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "is_read", "created_at")
    search_fields = ("name", "email", "subject")
    readonly_fields = ("created_at",)
    list_filter = ("is_read", "created_at")


@admin.register(NutritionArticle)
class NutritionArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "featured", "is_published", "published_at")
    list_filter = ("category", "featured", "is_published")
    search_fields = ("title", "excerpt", "content", "tags")
    readonly_fields = ("created_at", "updated_at", "reading_time")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-featured", "-published_at")


@admin.register(WorkoutArticle)
class WorkoutArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "featured", "is_published", "published_at")
    list_filter = ("category", "featured", "is_published")
    search_fields = ("title", "excerpt", "content", "tags")
    readonly_fields = ("created_at", "updated_at", "reading_time")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-featured", "-published_at")


@admin.register(FitnessArticle)
class FitnessArticleAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "category", "is_published", "published_at", "preview_image")
    list_filter = ("category", "is_published", "published_at", "created_at")
    search_fields = ("code", "title", "overview", "coach_insight")
    readonly_fields = ("created_at", "updated_at", "reading_time", "preview_image")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-published_at", "title")
    filter_horizontal = ()
    fieldsets = (
        ("Article", {
            "fields": ("code", "title", "slug", "category", "author", "published_at", "is_published", "reading_time")
        }),
        ("Featured Media", {
            "fields": ("featured_image", "featured_image_url", "preview_image", "video_title", "youtube_url")
        }),
        ("Content", {
            "fields": (
                "overview", "core_concepts", "why_it_matters", "science_explained",
                "practical_application", "common_myths", "coach_insight", "key_takeaways",
            )
        }),
        ("Related", {
            "fields": ("related_articles",)
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )

    def preview_image(self, obj):
        url = ""
        if obj.featured_image and hasattr(obj.featured_image, "url"):
            url = obj.featured_image.url
        elif obj.featured_image_url:
            url = obj.featured_image_url
        if not url:
            return "No image"
        return format_html(
            '<img src="{}" style="width: 180px; height: 102px; object-fit: cover; border-radius: 8px; border: 1px solid #991b1b;" />',
            url,
        )
    preview_image.short_description = "Preview image"


@admin.register(WorkoutTip)
class WorkoutTipAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "category", "is_published", "published_at", "reading_time")
    list_filter = ("category", "is_published", "published_at")
    search_fields = ("code", "title", "overview", "coach_tip")
    readonly_fields = ("created_at", "updated_at", "reading_time")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("category", "title")


class WorkoutExerciseInline(admin.TabularInline):
    model = WorkoutExercise
    extra = 1
    autocomplete_fields = ("exercise",)


@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    inlines = [WorkoutExerciseInline]
    list_display = ("title", "difficulty", "duration_minutes", "published", "created_at")
    list_filter = ("difficulty", "published", "muscle_groups")
    search_fields = ("title", "description")


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "skill_level", "exercise_type")
    search_fields = ("name", "description")
    filter_horizontal = ("primary_muscles", "secondary_muscles", "equipment")
    list_filter = ("skill_level", "exercise_type")


@admin.register(MuscleGroup)
class MuscleGroupAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "slug")
    search_fields = ("name",)
