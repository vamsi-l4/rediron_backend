from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from accounts.models import FitnessProgress, SavedItem
from main.models import Equipment, Exercise, FitnessArticle, NutritionArticle, WorkoutTip
from rediron_shop.models import Order, Product, Subscription, WishlistItem
from coach.models import ChallengeProgress, CoachPlan, ProgressHistory, WeeklyReport


MUSCLE_ALIASES = {
    "chest": ("chest", "pec", "pector"),
    "upper chest": ("chest", "pec", "pector", "incline"),
    "back": ("back", "lat", "row", "pull"),
    "shoulders": ("shoulder", "delt"),
    "biceps": ("bicep", "curl", "arm"),
    "triceps": ("tricep", "pushdown", "dip", "extension"),
    "forearms": ("forearm", "wrist", "grip", "farmer"),
    "abs": ("abs", "core", "abdominal", "oblique"),
    "legs": ("leg", "quad", "hamstring", "glute", "calf", "squat", "curl", "press"),
}


def _payload_muscles(payload):
    muscles = payload.get("focus_muscles") or payload.get("muscle") or []
    if isinstance(muscles, str):
        muscles = [muscles]
    return [str(item).strip() for item in muscles if str(item).strip()]


def _muscle_keywords(muscles):
    keywords = []
    for muscle in muscles:
        normalized = muscle.lower()
        keywords.extend(MUSCLE_ALIASES.get(normalized, (normalized,)))
    return tuple(dict.fromkeys(keyword for keyword in keywords if keyword))


def _safe_profile(user):
    profile = getattr(user, "profile", None)
    if not profile:
        return {}
    age = None
    if profile.date_of_birth:
        today = timezone.localdate()
        age = today.year - profile.date_of_birth.year - (
            (today.month, today.day) < (profile.date_of_birth.month, profile.date_of_birth.day)
        )
    return {
        "height_cm": profile.height,
        "weight_kg": profile.weight,
        "age": age,
        "goal": profile.fitness_goal,
        "experience": profile.experience_level,
        "gender": profile.gender,
        "timezone": profile.timezone,
    }


def load_user_context(user, intent="dashboard", payload=None):
    payload = payload or {}
    now = timezone.now()
    profile = _safe_profile(user)
    latest_progress = ProgressHistory.objects.filter(user=user).order_by("-recorded_on").first()
    account_progress = FitnessProgress.objects.filter(user=user).order_by("-date_recorded")[:8]
    plans = CoachPlan.objects.filter(user=user).order_by("-created_at")[:6]
    challenge = ChallengeProgress.objects.filter(user=user, is_completed=False).order_by("-created_at").first()
    subscription = Subscription.objects.filter(user=user, active=True, end_date__gte=now).order_by("-created_at").first()
    orders = Order.objects.filter(user=user).prefetch_related("items__product").order_by("-placed_at")[:5]
    wishlist = WishlistItem.objects.filter(wishlist__user=user).select_related("product")[:12]
    saved = SavedItem.objects.filter(user=user).order_by("-saved_at")[:20]

    focus = " ".join(str(v) for v in payload.values()).lower()
    requested_muscles = _payload_muscles(payload)
    muscle_keywords = _muscle_keywords(requested_muscles)
    exercises = Exercise.objects.all()
    if requested_muscles:
        exercise_filter = Q()
        for muscle in requested_muscles:
            exercise_filter |= Q(muscle_group__iexact=muscle)
        for keyword in muscle_keywords:
            exercise_filter |= Q(muscle_group__icontains=keyword) | Q(name__icontains=keyword)
        exercises = exercises.filter(exercise_filter)
    exercises = exercises.select_related().prefetch_related("equipment")[:20]

    products = Product.objects.filter(is_active=True)
    if intent in {"nutrition", "supplement"} or "protein" in focus or "supplement" in focus:
        products = products.filter(product_type__in=["nutrition", "supplement"]) | Product.objects.filter(
            is_active=True,
            category__name__icontains="supplement",
        )
    products = products.select_related("category")[:16]

    equipment = Equipment.objects.all()
    if payload.get("equipment"):
        equipment = equipment.filter(name__icontains=str(payload.get("equipment")).split(",")[0])
    elif intent == "body_explorer" and muscle_keywords:
        equipment_filter = Q(exercises__in=exercises)
        for keyword in muscle_keywords:
            equipment_filter |= Q(name__icontains=keyword) | Q(usage__icontains=keyword)
        equipment = equipment.filter(equipment_filter).distinct()
    equipment = equipment[:16]

    articles = list(FitnessArticle.objects.filter(is_published=True).order_by("-published_at")[:8])
    nutrition_articles = list(NutritionArticle.objects.filter(is_published=True).order_by("-published_at")[:8])
    tips = list(WorkoutTip.objects.filter(is_published=True).order_by("-published_at")[:8])

    return {
        "profile": profile,
        "subscription": {
            "plan": getattr(subscription, "plan", None),
            "active": bool(subscription),
        },
        "latest_progress": {
            "weight": getattr(latest_progress, "weight", None),
            "body_fat": getattr(latest_progress, "body_fat", None),
            "streak": getattr(latest_progress, "streak", 0) if latest_progress else 0,
            "recorded_on": str(latest_progress.recorded_on) if latest_progress else None,
        },
        "account_progress": list(account_progress.values("date_recorded", "weight", "body_fat_percentage", "muscle_mass")[:8]),
        "current_challenge": {
            "title": getattr(challenge, "title", None),
            "progress_percentage": challenge.progress_percentage if challenge else 0,
        },
        "previous_plans": list(plans.values("id", "title", "plan_type", "created_at")[:6]),
        "orders": [
            {
                "id": order.id,
                "status": order.status,
                "items": [item.product.name for item in order.items.all() if item.product],
            }
            for order in orders
        ],
        "saved_items": list(saved.values("item_type", "item_title")[:20]),
        "saved_products": [{"id": item.product_id, "name": item.product.name, "url": f"/shop-products/{item.product_id}"} for item in wishlist],
        "exercises": [
            {
                "id": item.id,
                "name": item.name,
                "muscle_group": item.muscle_group,
                "difficulty": item.skill_level,
                "url": f"/exercises/{item.slug}",
                "equipment": [eq.name for eq in item.equipment.all()],
            }
            for item in exercises
        ],
        "products": [
            {"id": item.id, "name": item.name, "price": float(item.price), "url": f"/shop-products/{item.id}"}
            for item in products
        ],
        "equipment": [
            {"id": item.id, "name": item.name, "category": item.category, "url": f"/equipment/{item.category}/{item.id}"}
            for item in equipment
        ],
        "articles": [
            {"title": item.title, "url": f"/articles/fitness/{item.slug}", "category": item.category}
            for item in articles
        ],
        "nutrition_articles": [
            {"title": item.title, "url": f"/nutrition/{item.slug}", "category": item.category}
            for item in nutrition_articles
        ],
        "workout_tips": [
            {"title": item.title, "url": f"/articles/workout-tips/{item.slug}", "category": item.category}
            for item in tips
        ],
        "recent_reports": list(
            WeeklyReport.objects.filter(user=user, week_start__gte=timezone.localdate() - timedelta(days=60))
            .values("id", "week_start", "week_end", "score", "summary_json")[:6]
        ),
    }
