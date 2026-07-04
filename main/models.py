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
    code = models.CharField(max_length=20, unique=True, null=True, blank=True, help_text="Stable fixture ID, e.g. N01")
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
    video_url = models.URLField(blank=True, null=True, help_text="Optional YouTube/Vimeo link for the article")
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


# ---------- FITNESS ARTICLES ----------
class FitnessArticle(models.Model):
    CATEGORY_CHOICES = [
        ("Beginner", "Beginner"),
        ("Intermediate", "Intermediate"),
        ("Advanced", "Advanced"),
        ("Strength Training", "Strength Training"),
        ("Fat Loss", "Fat Loss"),
        ("Recovery", "Recovery"),
        ("Mobility", "Mobility"),
        ("Nutrition", "Nutrition"),
    ]

    code = models.CharField(max_length=20, unique=True, help_text="Stable fixture ID, e.g. FA01")
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=260, unique=True, blank=True)
    category = models.CharField(max_length=60, choices=CATEGORY_CHOICES, default="Beginner", db_index=True)
    featured_image = models.ImageField(upload_to="fitness_articles/", null=True, blank=True)
    featured_image_url = models.URLField(blank=True, help_text="Optional remote image URL")
    author = models.CharField(max_length=120, default="RedIron Team")
    overview = models.TextField(blank=True)
    coreConcepts = models.JSONField(default=list, blank=True)
    whyItMatters = models.JSONField(default=list, blank=True)
    scienceExplained = models.JSONField(default=list, blank=True)
    practicalApplication = models.JSONField(default=list, blank=True)
    commonMyths = models.JSONField(default=list, blank=True)
    coachInsight = models.TextField(blank=True)
    keyTakeaways = models.JSONField(default=list, blank=True)
    videoTitle = models.CharField(max_length=250, blank=True)
    youtubeUrl = models.URLField(blank=True)
    relatedArticles = models.JSONField(default=list, blank=True, help_text="List of related FitnessArticle codes")
    published_at = models.DateTimeField(default=timezone.now, db_index=True)
    is_published = models.BooleanField(default=True, db_index=True)
    reading_time = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "title"]
        indexes = [
            models.Index(fields=["category", "is_published"]),
            models.Index(fields=["slug"]),
        ]

    def _word_count(self):
        parts = [
            self.overview,
            self.coachInsight,
            " ".join(self.coreConcepts or []),
            " ".join(self.whyItMatters or []),
            " ".join(self.scienceExplained or []),
            " ".join(self.practicalApplication or []),
            " ".join(self.commonMyths or []),
            " ".join(self.keyTakeaways or []),
        ]
        return len(re.findall(r"\w+", " ".join(parts)))

    def save(self, *args, **kwargs):
        if self.pk is None and self.code:
            existing = FitnessArticle.objects.filter(code=self.code).only("pk").first()
            if existing:
                self.pk = existing.pk
        if not self.slug:
            base = slugify(self.title or self.code or "fitness-article")[:240]
            existing = FitnessArticle.objects.filter(slug__startswith=base).exclude(pk=self.pk).values_list("slug", flat=True)
            existing_set = set(existing)
            if base not in existing_set:
                slug = base
            else:
                max_n = 0
                pattern = re.compile(r"^" + re.escape(base) + r"-(\d+)$")
                for value in existing_set:
                    match = pattern.match(value)
                    if match:
                        try:
                            max_n = max(max_n, int(match.group(1)))
                        except ValueError:
                            pass
                slug = f"{base}-{max_n + 1}"
            self.slug = slug
        wc = self._word_count()
        self.reading_time = max(1, math.ceil(wc / 200)) if wc else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.title}"


# ---------- WORKOUT TIPS ----------
class WorkoutTip(models.Model):
    CATEGORY_CHOICES = [
        ("Beginner", "Beginner"),
        ("Form", "Form"),
        ("Recovery", "Recovery"),
        ("Strength", "Strength"),
        ("Advanced", "Advanced"),
    ]

    code = models.CharField(max_length=20, unique=True, help_text="Stable fixture ID, e.g. WT01")
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=260, unique=True, blank=True)
    thumbnail = models.CharField(max_length=500, blank=True)
    featured_image = models.ImageField(upload_to="workout_tips/", null=True, blank=True)
    featured_image_url = models.URLField(blank=True, help_text="Optional remote/admin image URL")
    youtube_url = models.URLField(blank=True, help_text="YouTube watch URL used for embedded demo video")
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, db_index=True)
    overview = models.TextField(blank=True)
    why_it_matters = models.JSONField(default=list, blank=True)
    step_by_step_guide = models.JSONField(default=list, blank=True)
    common_mistakes = models.JSONField(default=list, blank=True)
    coach_tip = models.TextField(blank=True)
    key_takeaways = models.JSONField(default=list, blank=True)
    related_articles = models.JSONField(default=list, blank=True, help_text="List of related WorkoutTip codes")
    author = models.CharField(max_length=120, default="RedIron Team")
    published_at = models.DateTimeField(default=timezone.now, db_index=True)
    is_published = models.BooleanField(default=True, db_index=True)
    reading_time = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "title"]
        indexes = [
            models.Index(fields=["category", "is_published"]),
            models.Index(fields=["slug"]),
        ]

    def _word_count(self):
        parts = [
            self.overview,
            self.coach_tip,
            " ".join(self.why_it_matters or []),
            " ".join(self.step_by_step_guide or []),
            " ".join(self.common_mistakes or []),
            " ".join(self.key_takeaways or []),
        ]
        return len(re.findall(r"\w+", " ".join(parts)))

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title or self.code)[:240]
        wc = self._word_count()
        self.reading_time = max(1, math.ceil(wc / 200)) if wc else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.title}"


# ---------- MUSCLES ----------
class MuscleGroup(models.Model):
    BODY_REGION_CHOICES = [
        ("chest", "Chest"),
        ("back", "Back"),
        ("shoulders", "Shoulders"),
        ("legs", "Legs"),
        ("biceps", "Biceps"),
        ("triceps", "Triceps"),
        ("forearms", "Forearms"),
        ("abs", "Abs"),
        ("cardio", "Cardio"),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=140, blank=True, db_index=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    body_region = models.CharField(max_length=30, choices=BODY_REGION_CHOICES, blank=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            parent_prefix = f"{self.parent.slug}-" if self.parent and self.parent.slug else ""
            self.slug = f"{parent_prefix}{slugify(self.name)}"[:120]
        if not self.body_region:
            self.body_region = self.parent.body_region if self.parent else slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["parent__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["parent", "name"], name="unique_muscle_group_per_parent"),
        ]

    def __str__(self):
        return f"{self.parent.name} / {self.name}" if self.parent else self.name


# ---------- EXERCISES ----------
class Exercise(models.Model):
    MUSCLE_GROUP_CHOICES = [
        ("Chest", "Chest"),
        ("Back", "Back"),
        ("Shoulders", "Shoulders"),
        ("Legs", "Legs"),
        ("Biceps", "Biceps"),
        ("Triceps", "Triceps"),
        ("Forearms", "Forearms"),
        ("Abs", "Abs"),
        ("Cardio", "Cardio"),
    ]
    SKILL_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]
    TYPE_CHOICES = [
        ("strength", "Strength"),
        ("hypertrophy", "Hypertrophy"),
        ("cardio", "Cardio"),
        ("mobility", "Mobility"),
        ("functional", "Functional"),
        ("isolation", "Isolation"),
    ]

    code = models.CharField(max_length=30, unique=True, null=True, blank=True, help_text="Stable exercise code, e.g. LG-CV-04")
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    muscle_group = models.CharField(max_length=30, choices=MUSCLE_GROUP_CHOICES, default="Chest", db_index=True)
    subcategory = models.CharField(max_length=80, blank=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    primary_muscles = models.ManyToManyField(MuscleGroup, related_name="primary_exercises")
    secondary_muscles = models.ManyToManyField(MuscleGroup, related_name="secondary_exercises", blank=True)
    equipment = models.ManyToManyField(Equipment, related_name="exercises", blank=True)
    video_url = models.URLField(blank=True, null=True, help_text="Legacy video URL. New UI uses youtube_url first.")
    youtube_url = models.URLField(blank=True, help_text="YouTube embed/watch URL for the demonstration video")
    image = models.ImageField(upload_to="exercises/", blank=True, null=True)
    featured_image_url = models.URLField(blank=True, help_text="Optional remote/admin URL fallback for featured image")
    skill_level = models.CharField(max_length=20, choices=SKILL_CHOICES, default="beginner")
    exercise_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="strength")
    benefits = models.JSONField(default=list, blank=True)
    how_to_perform = models.JSONField(default=list, blank=True)
    variations = models.JSONField(default=list, blank=True)
    common_mistakes = models.JSONField(default=list, blank=True)
    sample_30_day_challenge = models.JSONField(default=list, blank=True)
    tips = models.JSONField(default=list, blank=True)
    related_exercises = models.JSONField(default=list, blank=True, help_text="List of related Exercise codes or slugs")
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

