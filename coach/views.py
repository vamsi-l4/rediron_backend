from datetime import timedelta
import logging

from django.db import IntegrityError
from django.db.models import Count
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from accounts.models import UserProfile

from .models import (
    AIConversation,
    CalendarEvent,
    ChallengeProgress,
    CoachNotification,
    CoachPlan,
    ProgressHistory,
    WeeklyReport,
)
from .permissions import IsCoachOwner
from .serializers import (
    AIConversationSerializer,
    CalendarEventSerializer,
    ChallengeProgressSerializer,
    CoachNotificationSerializer,
    CoachPlanSerializer,
    ProgressHistorySerializer,
    WeeklyReportSerializer,
)
from .services.ai_service import generate_plan, send_chat_message
from .services.context_loader import load_user_context
from .utils import generate_weekly_report

logger = logging.getLogger(__name__)


class UserScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsCoachOwner]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CoachPlanViewSet(UserScopedViewSet):
    queryset = CoachPlan.objects.all()
    serializer_class = CoachPlanSerializer
    search_fields = ["title", "plan_type"]
    ordering_fields = ["created_at", "updated_at", "title"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            queryset = queryset.filter(is_saved=True).exclude(plan_type__in=["chat", "body_explorer"])
        return queryset

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        plan = self.get_object()
        duplicate = CoachPlan.objects.create(
            user=request.user,
            title=f"{plan.title} Copy",
            plan_type=plan.plan_type,
            input_payload=plan.input_payload,
            response_json=plan.response_json,
            source_context=plan.source_context,
            provider=plan.provider,
            is_saved=True,
            duplicated_from=plan,
        )
        return Response(self.get_serializer(duplicate).data, status=status.HTTP_201_CREATED)


class ProgressHistoryViewSet(UserScopedViewSet):
    queryset = ProgressHistory.objects.all()
    serializer_class = ProgressHistorySerializer
    ordering_fields = ["recorded_on", "created_at"]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        recorded_on = data.get("recorded_on") or timezone.localdate()
        defaults = {key: value for key, value in data.items() if key != "recorded_on"}
        try:
            progress, created = ProgressHistory.objects.update_or_create(
                user=request.user,
                recorded_on=recorded_on,
                defaults=defaults,
            )
        except IntegrityError:
            logger.exception("Progress upsert failed for user=%s date=%s", request.user.pk, recorded_on)
            return Response({"detail": "Could not save progress for this date."}, status=status.HTTP_409_CONFLICT)
        output = self.get_serializer(progress)
        return Response(output.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ChallengeProgressViewSet(UserScopedViewSet):
    queryset = ChallengeProgress.objects.all()
    serializer_class = ChallengeProgressSerializer
    search_fields = ["title", "badge"]


class CoachNotificationViewSet(UserScopedViewSet):
    queryset = CoachNotification.objects.all()
    serializer_class = CoachNotificationSerializer

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at", "updated_at"])
        return Response(self.get_serializer(notification).data)


class WeeklyReportViewSet(UserScopedViewSet):
    queryset = WeeklyReport.objects.all()
    serializer_class = WeeklyReportSerializer

    @action(detail=False, methods=["post"])
    def generate(self, request):
        report = generate_weekly_report(request.user)
        return Response(self.get_serializer(report).data, status=status.HTTP_201_CREATED)


class CalendarEventViewSet(UserScopedViewSet):
    queryset = CalendarEvent.objects.all()
    serializer_class = CalendarEventSerializer
    filterset_fields = ["status", "event_date"]


class AIConversationViewSet(UserScopedViewSet):
    queryset = AIConversation.objects.prefetch_related("messages")
    serializer_class = AIConversationSerializer
    search_fields = ["title", "messages__content"]

    def get_queryset(self):
        return super().get_queryset().filter(archived_at__isnull=True)

    @action(detail=True, methods=["post"])
    def message(self, request, pk=None):
        message = request.data.get("message", "").strip()
        if not message:
            return Response({"detail": "Message is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            conversation = send_chat_message(request.user, message, conversation_id=pk)
            return Response(self.get_serializer(conversation).data)
        except Exception:
            logger.exception("Coach chat message failed")
            return Response({"detail": "Coach AI could not process this message. Please retry."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    @action(detail=True, methods=["post"])
    def pin(self, request, pk=None):
        conversation = self.get_object()
        conversation.is_pinned = not conversation.is_pinned
        conversation.save(update_fields=["is_pinned", "updated_at"])
        return Response(self.get_serializer(conversation).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    user = request.user
    today = timezone.localdate()
    context = load_user_context(user, intent="dashboard")
    profile_obj, _ = UserProfile.objects.get_or_create(user=user)
    missing_fields = [
        field for field, value in {
            "height": profile_obj.height,
            "weight": profile_obj.weight,
            "fitness_goal": profile_obj.fitness_goal,
            "experience_level": profile_obj.experience_level,
            "gender": profile_obj.gender,
        }.items() if not value
    ]
    needs_setup = bool(missing_fields)
    estimated_calories = None
    estimated_protein = None
    estimated_water = None
    if profile_obj.weight and profile_obj.height and profile_obj.fitness_goal:
        base = 24 * profile_obj.weight
        multiplier = {"weight_loss": 1.15, "muscle_gain": 1.35, "maintenance": 1.25, "endurance": 1.4, "flexibility": 1.2}.get(profile_obj.fitness_goal, 1.25)
        estimated_calories = round(base * multiplier)
        estimated_protein = round(profile_obj.weight * 1.8)
        estimated_water = f"{max(2.2, round(profile_obj.weight * 0.04, 1))}L"
    latest_progress = ProgressHistory.objects.filter(user=user).order_by("-recorded_on").first()
    today_event = CalendarEvent.objects.filter(user=user, event_date=today).order_by("created_at").first()
    saved_plan_queryset = CoachPlan.objects.filter(user=user, is_saved=True).exclude(plan_type__in=["chat", "body_explorer"])
    counts = saved_plan_queryset.values("plan_type").annotate(total=Count("id"))
    notifications = CoachNotification.objects.filter(user=user, read_at__isnull=True)[:6]
    reports = WeeklyReport.objects.filter(user=user)[:4]
    saved_plans = saved_plan_queryset[:6]
    challenge = ChallengeProgress.objects.filter(user=user, is_completed=False).first()
    payload = {
        "profile": context["profile"],
        "needs_setup": needs_setup,
        "missing_fields": missing_fields,
        "today": {
            "workout": today_event.title if today_event else "No workout scheduled yet",
            "calories": estimated_calories,
            "protein": estimated_protein,
            "water": estimated_water,
        },
        "current_challenge": ChallengeProgressSerializer(challenge).data if challenge else None,
        "progress_summary": {
            "weight": getattr(latest_progress, "weight", context["profile"].get("weight_kg")),
            "body_fat": getattr(latest_progress, "body_fat", None),
            "streak": getattr(latest_progress, "streak", 0) if latest_progress else 0,
            "completed_workouts": getattr(latest_progress, "completed_workouts", 0) if latest_progress else 0,
        },
        "plan_counts": {item["plan_type"]: item["total"] for item in counts},
        "saved_plans": CoachPlanSerializer(saved_plans, many=True).data,
        "recent_reports": WeeklyReportSerializer(reports, many=True).data,
        "latest_recommendations": context["articles"][:3] + context["nutrition_articles"][:3],
        "notifications": CoachNotificationSerializer(notifications, many=True).data,
        "body_metrics": list(ProgressHistory.objects.filter(user=user, recorded_on__gte=today - timedelta(days=90)).values("recorded_on", "weight", "body_fat", "waist", "strength")[:30]),
        "quick_shortcuts": ["Workout Generator", "Nutrition Planner", "Coach Chat", "Transformation Planner"],
    }
    return Response(payload)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def profile_setup(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    allowed = {"height", "weight", "fitness_goal", "experience_level", "gender", "date_of_birth"}
    for field in allowed:
        if field in request.data:
            setattr(profile, field, request.data.get(field) or None)
    profile.is_complete = all([profile.height, profile.weight, profile.fitness_goal, profile.experience_level, profile.gender])
    profile.save()
    return Response({
        "success": True,
        "profile": {
            "height": profile.height,
            "weight": profile.weight,
            "fitness_goal": profile.fitness_goal,
            "experience_level": profile.experience_level,
            "gender": profile.gender,
            "is_complete": profile.is_complete,
        },
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_ai_plan(request, intent):
    allowed = {"workout", "nutrition", "transformation", "supplement", "equipment", "body_explorer"}
    if intent not in allowed:
        return Response({"detail": "Unsupported Coach AI intent."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        plan, cached = generate_plan(request.user, intent, request.data or {})
        return Response({"cached": cached, "plan": CoachPlanSerializer(plan).data}, status=status.HTTP_201_CREATED if not cached else status.HTTP_200_OK)
    except Exception:
        logger.exception("Coach AI generation failed")
        return Response({"detail": "Coach AI could not generate this response. Please retry."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_chat(request):
    message = request.data.get("message", "").strip()
    if not message:
        return Response({"detail": "Message is required."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        conversation = send_chat_message(request.user, message)
        return Response(AIConversationSerializer(conversation).data, status=status.HTTP_201_CREATED)
    except Exception:
        logger.exception("Coach chat start failed")
        return Response({"detail": "Coach AI could not start this chat. Please retry."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
