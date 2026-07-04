from rest_framework import serializers

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


class ConversationMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationMessage
        fields = ["id", "role", "content", "structured_content", "created_at"]
        read_only_fields = fields


class AIConversationSerializer(serializers.ModelSerializer):
    messages = ConversationMessageSerializer(many=True, read_only=True)

    class Meta:
        model = AIConversation
        fields = ["id", "title", "is_pinned", "archived_at", "last_message_at", "metadata", "messages", "created_at", "updated_at"]
        read_only_fields = ["id", "last_message_at", "created_at", "updated_at", "messages"]


class CoachPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoachPlan
        fields = [
            "id",
            "title",
            "plan_type",
            "input_payload",
            "response_json",
            "provider",
            "is_saved",
            "duplicated_from",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "response_json", "provider", "duplicated_from", "created_at", "updated_at"]


class ProgressHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgressHistory
        fields = ["id", "recorded_on", "weight", "body_fat", "chest", "waist", "arms", "legs", "strength", "completed_workouts", "streak", "notes", "created_at"]
        read_only_fields = ["id", "created_at"]


class ChallengeProgressSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.IntegerField(read_only=True)

    class Meta:
        model = ChallengeProgress
        fields = ["id", "title", "duration_days", "started_on", "completed_days", "badge", "certificate_url", "leaderboard_score", "is_completed", "progress_percentage", "created_at"]
        read_only_fields = ["id", "progress_percentage", "created_at"]


class CoachNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoachNotification
        fields = ["id", "notification_type", "title", "message", "payload", "scheduled_for", "read_at", "created_at"]
        read_only_fields = ["id", "created_at"]


class WeeklyReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeeklyReport
        fields = ["id", "week_start", "week_end", "summary_json", "score", "is_ready", "created_at"]
        read_only_fields = ["id", "created_at"]


class CalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEvent
        fields = ["id", "title", "event_date", "status", "plan", "reminder_at", "details", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

