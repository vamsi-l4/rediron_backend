from django.contrib import admin

from .models import (
    AIConversation,
    CalendarEvent,
    ChallengeProgress,
    CoachNotification,
    CoachPlan,
    ConversationMessage,
    ProgressHistory,
    WeeklyReport,
)


class UserSearchAdmin(admin.ModelAdmin):
    search_fields = ["user__email", "user__name"]
    readonly_fields = ["created_at", "updated_at"]


class ConversationMessageInline(admin.TabularInline):
    model = ConversationMessage
    extra = 0
    readonly_fields = ["user", "role", "content", "structured_content", "created_at", "updated_at"]
    can_delete = False


@admin.register(AIConversation)
class AIConversationAdmin(UserSearchAdmin):
    list_display = ["title", "user", "is_pinned", "last_message_at", "created_at"]
    list_filter = ["is_pinned", "archived_at", "created_at"]
    search_fields = ["title", "user__email", "messages__content"]
    inlines = [ConversationMessageInline]


@admin.register(ConversationMessage)
class ConversationMessageAdmin(UserSearchAdmin):
    list_display = ["conversation", "role", "user", "created_at"]
    list_filter = ["role", "created_at"]
    search_fields = ["content", "conversation__title", "user__email"]


@admin.register(CoachPlan)
class CoachPlanAdmin(UserSearchAdmin):
    list_display = ["title", "plan_type", "user", "provider", "is_saved", "created_at"]
    list_filter = ["plan_type", "provider", "is_saved", "created_at"]
    search_fields = ["title", "user__email", "response_json"]


@admin.register(ProgressHistory)
class ProgressHistoryAdmin(UserSearchAdmin):
    list_display = ["user", "recorded_on", "weight", "body_fat", "completed_workouts", "streak"]
    list_filter = ["recorded_on", "created_at"]


@admin.register(ChallengeProgress)
class ChallengeProgressAdmin(UserSearchAdmin):
    list_display = ["title", "user", "completed_days", "duration_days", "is_completed", "leaderboard_score"]
    list_filter = ["is_completed", "started_on", "created_at"]
    search_fields = ["title", "badge", "user__email"]


@admin.register(CoachNotification)
class CoachNotificationAdmin(UserSearchAdmin):
    list_display = ["title", "notification_type", "user", "scheduled_for", "read_at", "created_at"]
    list_filter = ["notification_type", "read_at", "scheduled_for", "created_at"]
    search_fields = ["title", "message", "user__email"]


@admin.register(WeeklyReport)
class WeeklyReportAdmin(UserSearchAdmin):
    list_display = ["user", "week_start", "week_end", "score", "is_ready"]
    list_filter = ["is_ready", "week_start", "created_at"]


@admin.register(CalendarEvent)
class CalendarEventAdmin(UserSearchAdmin):
    list_display = ["title", "user", "event_date", "status", "reminder_at"]
    list_filter = ["status", "event_date", "created_at"]
    search_fields = ["title", "user__email"]

