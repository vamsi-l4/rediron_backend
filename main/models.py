from django.db import models
from django.utils.text import slugify
from django.utils import timezone
import re
import math
from django.conf import settings


# ---------- EQUIPMENT ----------
class Equipment(models.Model):
    CATEGORY_CHOICES = [
        ("cardio", "Cardio"),
        ("strength", "Strength"),
        ("core", "Core"),
    ]
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to="equipment_images/", blank=True, null=True)
    usage = models.TextField(blank=True)
    video_link = models.URLField(blank=True)

    key_features = models.JSONField(default=list, blank=True)
    specifications = models.JSONField(default=list, blank=True)
    benefits = models.JSONField(default=list, blank=True)
    perfect_for = models.JSONField(default=list, blank=True)
    additional_stats = models.JSONField(default=list, blank=True)

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="cardio")

    def __str__(self):
        return self.name


# ---------- CONTACT ----------
class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    # admin can mark read/unread for badge counters
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.subject}"


# ---------- NUTRITION ----------
class NutritionArticle(models.Model):
    CATEGORY_CHOICES = [
        ("Nutrition", "Nutrition"),
        ("Supplements", "Supplements"),
        ("Recipes", "Recipes"),
    ]
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=260, unique=True, blank=True)
    author = models.CharField(max_length=120, default="RedIron Team")
    excerpt = models.CharField(max_length=300, blank=True)
    # structured JSON content (consistent type)
    content = models.JSONField(help_text="Structured JSON content with overview, key_benefits, etc.", blank=True, null=True)
    featured_image = models.ImageField(upload_to="articles/", null=True, blank=True)
    featured_image_url = models.URLField(blank=True, help_text="Optional remote image URL")
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default="Nutrition")
    tags = models.CharField(max_length=300, blank=True, help_text="Comma-separated tags")
    published_at = models.DateTimeField(default=timezone.now)
    is_published = models.BooleanField(default=True)
    reading_time = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Minutes")
    featured = models.BooleanField(default=False)
    references = models.JSONField(blank=True, null=True, help_text="List of reference dicts for the article")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def _word_count(self):
        if not self.content:
            return 0
        # flatten JSON content to text and count words
        def extract_text(obj):
            if isinstance(obj, str):
                return obj
            if isinstance(obj, dict):
                return " ".join(extract_text(v) for v in obj.values())
            if isinstance(obj, list):
                return " ".join(extract_text(v) for v in obj)
            return ""
        text = extract_text(self.content)
        return len(re.findall(r"\w+", text))

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title or "article")[:240]
            existing = NutritionArticle.objects.filter(slug__startswith=base).exclude(pk=self.pk).values_list('slug', flat=True)
            existing_set = set(existing)
            if base not in existing_set:
                slug = base
            else:
                # find highest numeric suffix
                max_n = 0
                pattern = re.compile(r'^' + re.escape(base) + r'-(\d+)$')
                for s in existing_set:
                    m = pattern.match(s)
                    if m:
                        try:
                            n = int(m.group(1))
                            if n > max_n:
                                max_n = n
                        except ValueError:
                            pass
                slug = f"{base}-{max_n+1}"
            self.slug = slug
        wc = self._word_count()
        self.reading_time = max(1, math.ceil(wc / 200)) if wc > 0 else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title if self.title else f"Article {self.pk}"


# ---------- WORKOUT ARTICLES ----------
class WorkoutArticle(models.Model):
    CATEGORY_CHOICES = [
        ("Workout Tips", "Workout Tips"),
        ("Fitness", "Fitness"),
    ]
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=260, unique=True, blank=True)
    author = models.CharField(max_length=120, default="RedIron Team")
    excerpt = models.CharField(max_length=300, blank=True)
    content = models.TextField(help_text="Markdown or HTML content", blank=True)
    featured_image = models.ImageField(upload_to="workout_articles/", null=True, blank=True)
    featured_image_url = models.URLField(blank=True, help_text="Optional remote image URL")
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default="Workout Tips")
    tags = models.CharField(max_length=300, blank=True, help_text="Comma-separated tags")
    published_at = models.DateTimeField(default=timezone.now)
    is_published = models.BooleanField(default=True)
    reading_time = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Minutes")
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def _word_count(self):
        if not self.content:
            return 0
        return len(re.findall(r"\w+", self.content))

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title or "article")[:240]
            existing = WorkoutArticle.objects.filter(slug__startswith=base).exclude(pk=self.pk).values_list('slug', flat=True)
            existing_set = set(existing)
            if base not in existing_set:
                slug = base
            else:
                max_n = 0
                pattern = re.compile(r'^' + re.escape(base) + r'-(\d+)$')
                for s in existing_set:
                    m = pattern.match(s)
                    if m:
                        try:
                            n = int(m.group(1))
                            if n > max_n:
                                max_n = n
                        except ValueError:
                            pass
                slug = f"{base}-{max_n+1}"
            self.slug = slug
        wc = self._word_count()
        self.reading_time = max(1, math.ceil(wc / 200)) if wc > 0 else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title if self.title else f"Article {self.pk}"


# ---------- MUSCLES ----------
class MuscleGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ---------- EXERCISES ----------
class Exercise(models.Model):
    SKILL_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]
    TYPE_CHOICES = [
        ("strength", "Strength"),
        ("cardio", "Cardio"),
        ("mobility", "Mobility"),
        ("hiit", "HIIT"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    primary_muscles = models.ManyToManyField(MuscleGroup, related_name="primary_exercises")
    secondary_muscles = models.ManyToManyField(MuscleGroup, related_name="secondary_exercises", blank=True)
    equipment = models.ManyToManyField(Equipment, related_name="exercises", blank=True)
    video_url = models.URLField(blank=True, null=True)
    image = models.ImageField(upload_to="exercises/", blank=True, null=True)
    skill_level = models.CharField(max_length=20, choices=SKILL_CHOICES, default="beginner")
    exercise_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="strength")
    # Changed to JSONField for consistency with NutritionArticle content
    content = models.JSONField(blank=True, null=True, help_text="Structured JSON content for exercise details")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=False, default=timezone.now)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            existing = Exercise.objects.filter(slug__startswith=base).exclude(pk=self.pk).values_list('slug', flat=True)
            existing_set = set(existing)
            if base not in existing_set:
                slug = base
            else:
                max_n = 0
                pattern = re.compile(r'^' + re.escape(base) + r'-(\d+)$')
                for s in existing_set:
                    m = pattern.match(s)
                    if m:
                        try:
                            n = int(m.group(1))
                            if n > max_n:
                                max_n = n
                        except ValueError:
                            pass
                slug = f"{base}-{max_n+1}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ---------- WORKOUTS ----------
class Workout(models.Model):
    DIFFICULTY_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    duration_minutes = models.PositiveIntegerField(default=30)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    muscle_groups = models.ManyToManyField(MuscleGroup, related_name="workouts", blank=True)
    equipment = models.ManyToManyField(Equipment, related_name="workouts", blank=True)
    featured_image = models.ImageField(upload_to="workouts/", blank=True, null=True)
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # optional created_by to track author for audit
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_workouts")

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:240]
            existing = Workout.objects.filter(slug__startswith=base).exclude(pk=self.pk).values_list('slug', flat=True)
            existing_set = set(existing)
            if base not in existing_set:
                slug = base
            else:
                max_n = 0
                pattern = re.compile(r'^' + re.escape(base) + r'-(\d+)$')
                for s in existing_set:
                    m = pattern.match(s)
                    if m:
                        try:
                            n = int(m.group(1))
                            if n > max_n:
                                max_n = n
                        except ValueError:
                            pass
                slug = f"{base}-{max_n+1}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# ---------- WORKOUT EXERCISES ----------
class WorkoutExercise(models.Model):
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name='workout_exercises')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    sets = models.PositiveIntegerField(default=3)
    reps = models.CharField(max_length=50, default='10')
    rest_time = models.PositiveIntegerField(default=60, help_text='Rest time in seconds')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.workout.title} - {self.exercise.name}"

# ============================================
# REDIRON PERFORMANCE LAB - ANALYTICS MODELS
# ============================================

class WorkoutSession(models.Model):
    """
    Tracks individual workout sessions per user.
    Used for performance analytics and progress tracking.
    """
    clerk_user_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Clerk user ID for data isolation"
    )
    date = models.DateField(default=timezone.now)
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    total_volume = models.FloatField(default=0, help_text="Auto-calculated total volume (weight × reps × sets)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['clerk_user_id', '-date']),
        ]

    def __str__(self):
        return f"Workout - {self.clerk_user_id} - {self.date}"


class ExerciseLog(models.Model):
    """
    Logs individual exercises within a workout session.
    Stores sets, reps, weight, and calculates 1RM.
    """
    session = models.ForeignKey(
        WorkoutSession,
        on_delete=models.CASCADE,
        related_name='exercises'
    )
    exercise_name = models.CharField(max_length=200)
    sets = models.PositiveIntegerField(default=3)
    reps = models.PositiveIntegerField()
    weight = models.FloatField(help_text="Weight in kg")
    calculated_1rm = models.FloatField(default=0, help_text="Auto-calculated 1RM using Epley formula")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-session__date', '-created_at']

    def __str__(self):
        return f"{self.exercise_name} - {self.weight}kg x {self.reps}"


class BodyMetrics(models.Model):
    """
    Tracks body composition metrics over time.
    Used for progress tracking and trend analysis.
    """
    clerk_user_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Clerk user ID for data isolation"
    )
    weight = models.FloatField(help_text="Body weight in kg")
    body_fat = models.FloatField(null=True, blank=True, help_text="Body fat percentage")
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['clerk_user_id', '-recorded_at']),
        ]

    def __str__(self):
        return f"{self.clerk_user_id} - {self.weight}kg ({self.recorded_at.date()})"


class NutritionLog(models.Model):
    """
    Logs daily nutrition intake.
    Tracks macros and hydration for performance analysis.
    """
    clerk_user_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Clerk user ID for data isolation"
    )
    date = models.DateField(default=timezone.now)
    calories = models.PositiveIntegerField(default=0)
    protein = models.FloatField(default=0, help_text="Protein in grams")
    carbs = models.FloatField(default=0, help_text="Carbs in grams")
    fat = models.FloatField(default=0, help_text="Fat in grams")
    water = models.FloatField(default=0, help_text="Water intake in liters")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['clerk_user_id', '-date']),
        ]

    def __str__(self):
        return f"Nutrition - {self.clerk_user_id} - {self.date}"


class UserGoal(models.Model):
    """
    Stores user fitness goals for personalized recommendations.
    """
    GOAL_TYPES = [
        ('fat_loss', 'Fat Loss'),
        ('muscle_gain', 'Muscle Gain'),
        ('strength', 'Strength'),
        ('endurance', 'Endurance'),
    ]
    
    clerk_user_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Clerk user ID for data isolation"
    )
    goal_type = models.CharField(
        max_length=50,
        choices=GOAL_TYPES,
        default='muscle_gain'
    )
    target_value = models.FloatField(null=True, blank=True, help_text="Target value (e.g., weight, strength level)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['clerk_user_id']),
        ]

    def __str__(self):
        return f"{self.clerk_user_id} - {self.get_goal_type_display()}"