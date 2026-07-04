from datetime import timedelta

from django.utils import timezone

from coach.models import CoachNotification, ProgressHistory, WeeklyReport


def generate_weekly_report(user):
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    entries = ProgressHistory.objects.filter(user=user, recorded_on__range=(week_start, week_end))
    workouts = sum(item.completed_workouts for item in entries)
    streak = max([item.streak for item in entries] or [0])
    latest = entries.order_by("-recorded_on").first()
    score = min(100, workouts * 12 + streak * 3)
    summary = {
        "workouts": workouts,
        "nutrition": "Review your saved nutrition plans and keep protein consistent.",
        "protein": "Aim for the target set in Coach AI Nutrition Planner.",
        "water": "Maintain 3 liters daily unless medically restricted.",
        "consistency": f"{score} weekly score",
        "strength_improvements": latest.strength if latest else None,
        "recommendations": ["Schedule next week in the calendar", "Log progress once weekly"],
    }
    report, _ = WeeklyReport.objects.update_or_create(
        user=user,
        week_start=week_start,
        defaults={"week_end": week_end, "summary_json": summary, "score": score, "is_ready": True},
    )
    CoachNotification.objects.get_or_create(
        user=user,
        notification_type="report_ready",
        title="Weekly Coach Report Ready",
        defaults={"message": "Your RedIron Coach AI weekly report is ready.", "payload": {"report_id": report.id}},
    )
    return report

