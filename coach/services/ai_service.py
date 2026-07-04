import hashlib
import json
import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from coach.models import AIConversation, CoachPlan, ConversationMessage
from .context_loader import load_user_context
from .json_validator import ResponseValidationError
from .prompt_builder import build_prompt
from .response_parser import parse_ai_json
from .providers.base_provider import AIProviderError
from .providers.gemini_provider import GeminiProvider
from .providers.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


def get_provider():
    import os

    provider = os.environ.get("COACH_AI_PROVIDER", "gemini").strip().lower()
    if provider == "openai":
        return OpenAIProvider()
    return GeminiProvider()


def _hash_payload(intent, payload, context):
    source = json.dumps({"intent": intent, "payload": payload, "profile": context.get("profile")}, sort_keys=True, default=str)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _local_response(intent, payload, context):
    exercises = context.get("exercises", [])[:8]
    products = context.get("products", [])[:6]
    equipment = context.get("equipment", [])[:6]
    articles = context.get("articles", [])[:4] + context.get("nutrition_articles", [])[:4]
    profile = context.get("profile", {})
    if intent == "workout":
        days = int(payload.get("days_per_week") or 4)
        daily = []
        for day in range(1, days + 1):
            daily.append({
                "day": f"Day {day}",
                "focus": (payload.get("focus_muscles") or ["Full Body"])[0] if isinstance(payload.get("focus_muscles"), list) else payload.get("focus_muscles", "Full Body"),
                "exercises": [
                    {"name": ex["name"], "sets": 3, "reps": "8-12", "tempo": "3-1-1", "rest": "75 sec", "exercise_url": ex["url"]}
                    for ex in exercises[:5]
                ],
                "warmup": ["5 minutes easy cardio", "Dynamic mobility for target joints"],
                "cooldown": ["Slow breathing", "Light stretching"],
                "tips": ["Keep 1-2 reps in reserve on most sets", "Increase load only when form is stable"],
            })
        return {
            "goal": payload.get("goal") or profile.get("goal") or "strength and body composition",
            "summary": "A RedIron-native plan built from your profile and the existing exercise library.",
            "weekly_split": [item["focus"] for item in daily],
            "daily_workouts": daily,
            "estimated_calories": days * 320,
            "difficulty": payload.get("experience") or profile.get("experience") or "intermediate",
        }
    if intent == "nutrition":
        calories = int(payload.get("calories") or 2200)
        protein = int(payload.get("protein") or max(120, (profile.get("weight_kg") or 70) * 1.8))
        return {
            "calories": calories,
            "protein": protein,
            "carbs": int((calories * 0.42) / 4),
            "fat": int((calories * 0.25) / 9),
            "meals": [
                {"name": "Breakfast", "time": "8:00 AM", "items": ["Paneer or eggs", "Oats", "Fruit"], "calories": 520, "protein": 35},
                {"name": "Lunch", "time": "1:00 PM", "items": ["Rice or roti", "Dal", "Chicken or tofu", "Salad"], "calories": 720, "protein": 45},
                {"name": "Dinner", "time": "8:00 PM", "items": ["Lean protein", "Vegetables", "Curd"], "calories": 620, "protein": 45},
            ],
            "shopping_list": ["Oats", "Dal", "Paneer", "Eggs or chicken", "Curd", "Rice", "Seasonal vegetables"],
            "water": "3.0-3.5 liters per day",
            "supplements": [{"name": p["name"], "product_url": p["url"], "timing": "As label directs"} for p in products[:3]],
            "timing": ["Protein across 3-5 feedings", "Carbs around training", "Hydrate before sessions"],
            "budget": payload.get("budget") or "balanced",
        }
    if intent == "body_explorer":
        muscle = payload.get("muscle") or "Chest"
        return {
            "muscle": muscle,
            "exercises": exercises,
            "articles": articles,
            "nutrition": context.get("nutrition_articles", [])[:4],
            "supplements": products,
            "equipment": equipment,
        }
    if intent == "supplement":
        return {"summary": "Recommendations are limited to products found in the RedIron catalog.", "products": products, "timing": ["Follow product label", "Pair protein with meals if intake is low"], "warnings": ["Check allergies and consult a clinician if you have a medical condition"]}
    if intent == "equipment":
        return {"summary": "Equipment matched from the RedIron equipment database.", "equipment": equipment, "recommendations": ["Choose based on space, goals, and current training split"]}
    if intent == "transformation":
        return {
            "current": profile,
            "target": {"goal": payload.get("goal") or profile.get("goal"), "timeline_weeks": payload.get("timeline_weeks") or 12},
            "timeline": ["Weeks 1-2 baseline and technique", "Weeks 3-8 progressive overload", "Weeks 9-12 refinement and testing"],
            "weekly_goals": ["Complete planned workouts", "Hit protein target", "Log body metrics once weekly"],
            "milestones": ["Streak established", "Strength up 5-10%", "Measurements trending toward goal"],
            "warnings": ["Avoid aggressive calorie cuts", "Deload if recovery drops"],
            "recommendations": ["Use saved RedIron exercises", "Review weekly reports", "Adjust plan from progress data"],
        }
    return {"answer": "I have your RedIron profile and can help with workouts, nutrition, progress, supplements, and equipment.", "cards": [], "recommendations": articles[:4]}


def generate_plan(user, intent, payload):
    context = load_user_context(user, intent=intent, payload=payload)
    prompt_hash = _hash_payload(intent, payload, context)
    cached = CoachPlan.objects.filter(
        user=user,
        plan_type=intent if intent in dict(CoachPlan.PLAN_TYPES) else "workout",
        prompt_hash=prompt_hash,
        created_at__gte=timezone.now() - timedelta(hours=1),
    ).first()
    if cached:
        return cached, True

    provider = get_provider()
    prompt = build_prompt(intent, payload, context)
    schema_name = intent if intent in {"workout", "nutrition", "transformation", "chat", "supplement", "equipment", "body_explorer"} else "chat"
    try:
        raw = provider.generate_json(prompt, schema_name)
        parsed = parse_ai_json(raw, schema_name)
    except (AIProviderError, ResponseValidationError, json.JSONDecodeError) as first_error:
        logger.warning("Coach AI provider failed once: %s", first_error)
        try:
            raw = provider.generate_json(prompt + "\nRepair: return strictly valid JSON matching the schema.", schema_name)
            parsed = parse_ai_json(raw, schema_name)
        except Exception as second_error:
            logger.exception("Coach AI provider failed twice; using deterministic RedIron response: %s", second_error)
            parsed = _local_response(schema_name, payload, context)

    title = payload.get("title") or f"{schema_name.replace('_', ' ').title()} Plan"
    plan_type = schema_name if schema_name in dict(CoachPlan.PLAN_TYPES) else "workout"
    plan = CoachPlan.objects.create(
        user=user,
        title=title,
        plan_type=plan_type,
        input_payload=payload,
        response_json=parsed,
        source_context=context,
        prompt_hash=prompt_hash,
        provider=getattr(provider, "name", ""),
    )
    return plan, False


@transaction.atomic
def send_chat_message(user, message, conversation_id=None):
    if conversation_id:
        conversation = AIConversation.objects.get(id=conversation_id, user=user)
    else:
        conversation = AIConversation.objects.create(user=user, title=message[:60] or "Coach Chat")
    ConversationMessage.objects.create(user=user, conversation=conversation, role="user", content=message)
    plan, _ = generate_plan(user, "chat", {"message": message, "conversation_id": conversation.id})
    answer = plan.response_json
    ConversationMessage.objects.create(
        user=user,
        conversation=conversation,
        role="assistant",
        content=answer.get("answer", ""),
        structured_content=answer,
    )
    conversation.last_message_at = timezone.now()
    conversation.save(update_fields=["last_message_at", "updated_at"])
    return conversation

