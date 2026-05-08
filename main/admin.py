from django.contrib import admin
from .models import (
    Equipment, ContactMessage,
    NutritionArticle, WorkoutArticle,
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
