from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AIConversationViewSet,
    CalendarEventViewSet,
    ChallengeProgressViewSet,
    CoachNotificationViewSet,
    CoachPlanViewSet,
    ProgressHistoryViewSet,
    WeeklyReportViewSet,
    dashboard,
    generate_ai_plan,
    profile_setup,
    start_chat,
)

router = DefaultRouter()
router.register("plans", CoachPlanViewSet, basename="coach-plans")
router.register("progress", ProgressHistoryViewSet, basename="coach-progress")
router.register("challenges", ChallengeProgressViewSet, basename="coach-challenges")
router.register("notifications", CoachNotificationViewSet, basename="coach-notifications")
router.register("reports", WeeklyReportViewSet, basename="coach-reports")
router.register("calendar", CalendarEventViewSet, basename="coach-calendar")
router.register("conversations", AIConversationViewSet, basename="coach-conversations")

urlpatterns = [
    path("dashboard/", dashboard, name="coach-dashboard"),
    path("profile-setup/", profile_setup, name="coach-profile-setup"),
    path("generate/<str:intent>/", generate_ai_plan, name="coach-generate"),
    path("chat/", start_chat, name="coach-chat"),
]

urlpatterns += router.urls
