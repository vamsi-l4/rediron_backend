from django.conf import settings
from django.db import models
from django.utils import timezone


class CoachBaseModel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="%(class)ss")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AIConversation(CoachBaseModel):
    title = models.CharField(max_length=180, default="New Coach Chat")
    is_pinned = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    last_message_at = models.DateTimeField(default=timezone.now, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-is_pinned", "-last_message_at"]
        indexes = [models.Index(fields=["user", "-last_message_at"])]

    def __str__(self):
        return f"{self.user.email} - {self.title}"


class ConversationMessage(CoachBaseModel):
    ROLE_CHOICES = [("user", "User"), ("assistant", "Assistant"), ("system", "System")]
    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField(blank=True)
    structured_content = models.JSONField(default=dict, blank=True)
    token_usage = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["conversation", "created_at"])]

    def __str__(self):
        return f"{self.conversation_id} - {self.role}"


class CoachPlan(CoachBaseModel):
    PLAN_TYPES = [
        ("workout", "Workout"),
        ("nutrition", "Nutrition"),
        ("transformation", "Transformation"),
        ("supplement", "Supplement"),
        ("equipment", "Equipment"),
        ("body_explorer", "Body Explorer"),
        ("chat", "Chat"),
    ]
    title = models.CharField(max_length=180)
    plan_type = models.CharField(max_length=30, choices=PLAN_TYPES, db_index=True)
    input_payload = models.JSONField(default=dict, blank=True)
    response_json = models.JSONField(default=dict)
    source_context = models.JSONField(default=dict, blank=True)
    prompt_hash = models.CharField(max_length=64, db_index=True, blank=True)
    provider = models.CharField(max_length=40, blank=True)
    is_saved = models.BooleanField(default=True, db_index=True)
    duplicated_from = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "plan_type", "-created_at"]),
            models.Index(fields=["user", "prompt_hash", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.plan_type} - {self.title}"


class WorkoutPlan(CoachPlan):
    class Meta:
        proxy = True
        verbose_name = "Workout Plan"
        verbose_name_plural = "Workout Plans"


class NutritionPlan(CoachPlan):
    class Meta:
        proxy = True
        verbose_name = "Nutrition Plan"
        verbose_name_plural = "Nutrition Plans"


class TransformationPlan(CoachPlan):
    class Meta:
        proxy = True
        verbose_name = "Transformation Plan"
        verbose_name_plural = "Transformation Plans"


class ProgressHistory(CoachBaseModel):
    recorded_on = models.DateField(default=timezone.localdate, db_index=True)
    weight = models.FloatField(null=True, blank=True)
    body_fat = models.FloatField(null=True, blank=True)
    chest = models.FloatField(null=True, blank=True)
    waist = models.FloatField(null=True, blank=True)
    arms = models.FloatField(null=True, blank=True)
    legs = models.FloatField(null=True, blank=True)
    strength = models.FloatField(null=True, blank=True)
    completed_workouts = models.PositiveIntegerField(default=0)
    streak = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-recorded_on", "-created_at"]
        unique_together = ["user", "recorded_on"]

    def __str__(self):
        return f"{self.user.email} - {self.recorded_on}"


class ChallengeProgress(CoachBaseModel):
    title = models.CharField(max_length=180)
    duration_days = models.PositiveSmallIntegerField(default=30)
    started_on = models.DateField(default=timezone.localdate)
    completed_days = models.PositiveSmallIntegerField(default=0)
    badge = models.CharField(max_length=120, blank=True)
    certificate_url = models.URLField(blank=True)
    leaderboard_score = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def progress_percentage(self):
        if not self.duration_days:
            return 0
        return min(100, round((self.completed_days / self.duration_days) * 100))

    def __str__(self):
        return f"{self.user.email} - {self.title}"


class CoachNotification(CoachBaseModel):
    TYPE_CHOICES = [
        ("workout_reminder", "Workout Reminder"),
        ("meal_reminder", "Meal Reminder"),
        ("challenge_reminder", "Challenge Reminder"),
        ("report_ready", "Report Ready"),
        ("recommendation", "Recommendation"),
    ]
    notification_type = models.CharField(max_length=40, choices=TYPE_CHOICES, db_index=True)
    title = models.CharField(max_length=180)
    message = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "read_at", "-created_at"])]

    def __str__(self):
        return f"{self.user.email} - {self.title}"


class WeeklyReport(CoachBaseModel):
    week_start = models.DateField(db_index=True)
    week_end = models.DateField(db_index=True)
    summary_json = models.JSONField(default=dict)
    score = models.PositiveSmallIntegerField(default=0)
    is_ready = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-week_start"]
        unique_together = ["user", "week_start"]

    def __str__(self):
        return f"{self.user.email} - {self.week_start}"


class CalendarEvent(CoachBaseModel):
    STATUS_CHOICES = [
        ("planned", "Planned"),
        ("completed", "Completed"),
        ("rest", "Rest"),
        ("missed", "Missed"),
    ]
    title = models.CharField(max_length=180)
    event_date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planned", db_index=True)
    plan = models.ForeignKey(CoachPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name="calendar_events")
    reminder_at = models.DateTimeField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["event_date", "created_at"]
        indexes = [models.Index(fields=["user", "event_date", "status"])]

    def __str__(self):
        return f"{self.user.email} - {self.title}"
