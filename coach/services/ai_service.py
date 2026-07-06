import hashlib
import json
import logging
from datetime import date, datetime
from decimal import Decimal
from datetime import timedelta

from django.db import transaction
from django.utils.text import slugify
from django.utils import timezone

from coach.models import AIConversation, CoachPlan, ConversationMessage
from main.models import Exercise
from .context_loader import load_user_context
from .json_validator import ResponseValidationError
from .prompt_builder import build_prompt
from .response_parser import parse_ai_json
from .providers.base_provider import AIProviderError
from .providers.gemini_provider import GeminiProvider
from .providers.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


def make_json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]
    return value


def get_provider():
    import os

    provider = os.environ.get("COACH_AI_PROVIDER", "gemini").strip().lower()
    if provider == "openai":
        return OpenAIProvider()
    return GeminiProvider()


def _hash_payload(intent, payload, context):
    source = json.dumps({
        "intent": intent,
        "payload": payload,
        "profile": context.get("profile"),
        "previous_plans": context.get("previous_plans", [])[:6],
        "saved_items": context.get("saved_items", [])[:10],
    }, sort_keys=True, default=str)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def build_conversation_title(message):
    words = [word.strip(".,!?;:()[]{}").title() for word in message.split() if len(word.strip(".,!?;:()[]{}")) > 2]
    stop = {"The", "And", "For", "With", "Can", "You", "This", "That", "Into", "From", "Please"}
    useful = [word for word in words if word not in stop][:6]
    return " ".join(useful) or "Coach AI Chat"


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
    message = str(payload.get("message") or "").lower()
    if "nutrition" in message or "meal" in message or "protein" in message or "diet" in message:
        answer = (
            "Based on your RedIron profile, start by making protein consistent, then adjust calories from weekly progress. "
            "Use 3-4 meals, place carbs around training, and keep hydration steady. "
            f"Useful RedIron reads: {', '.join(item['title'] for item in articles[:3])}."
        )
        cards = [{"title": product["name"], "url": product["url"]} for product in products[:3]]
    elif "equipment" in message or "home gym" in message:
        answer = (
            "For equipment, choose by your training style first: adjustable dumbbells and a bench for strength basics, "
            "cables or bands for joint-friendly volume, and cardio equipment only if conditioning is a priority."
        )
        cards = equipment[:4]
    elif "supplement" in message or "whey" in message or "creatine" in message:
        answer = (
            "Use supplements only to fill gaps: whey for protein convenience, creatine for strength output, and electrolytes if you sweat heavily. "
            "I matched recommendations to RedIron catalog products where available."
        )
        cards = [{"title": product["name"], "url": product["url"]} for product in products[:4]]
    elif "progress" in message or "streak" in message or "missed" in message:
        answer = (
            "Treat missed workouts as scheduling data, not failure. Move the highest-priority session forward, keep the next workout shorter, "
            "and log one simple metric today so your trend stays alive."
        )
        cards = articles[:3]
    else:
        workout_names = ", ".join(ex["name"] for ex in exercises[:5]) or "compound lifts from the RedIron exercise library"
        answer = (
            f"Here is a practical Coach AI direction: use {workout_names}. "
            "Keep the session focused, progress one variable at a time, and save the plan so I can remember it for your next recommendation."
        )
        cards = exercises[:5]
    return {"answer": answer, "cards": cards, "recommendations": articles[:4]}


def _normalize_text(value):
    return " ".join(str(value or "").lower().replace("&", "and").split())


def _exercise_url_for_name(name, exercise_lookup):
    normalized = _normalize_text(name)
    if normalized in exercise_lookup:
        return exercise_lookup[normalized]

    slug = slugify(name or "")
    if slug in exercise_lookup:
        return exercise_lookup[slug]

    stripped = normalized
    for token in (" modified", " controlled", " single arm", " mid position"):
        stripped = stripped.replace(token, "")
    return exercise_lookup.get(stripped) or exercise_lookup.get(slugify(stripped))


def _post_process_plan(intent, payload, parsed, context=None):
    if not isinstance(parsed, dict):
        return parsed
    context = context or {}

    if intent == "workout":
        exercises = Exercise.objects.only("name", "slug")
        exercise_lookup = {}
        for item in exercises:
            url = f"/exercises/{item.slug}"
            exercise_lookup[_normalize_text(item.name)] = url
            exercise_lookup[item.slug] = url

        for day in parsed.get("daily_workouts") or []:
            for exercise in day.get("exercises") or []:
                if not isinstance(exercise, dict):
                    continue
                url = _exercise_url_for_name(exercise.get("name"), exercise_lookup)
                exercise["exercise_url"] = url or ""

    if intent == "nutrition":
        diet_type = _normalize_text(payload.get("diet_type"))
        if diet_type in {"veg", "vegetarian"}:
            blocked = ("chicken", "fish", "egg", "eggs", "mutton", "beef", "pork", "turkey", "shrimp", "prawn")
            replacements = {
                "chicken": "paneer or tofu",
                "fish": "tofu or dal",
                "egg": "paneer or sprouted moong",
                "eggs": "paneer or sprouted moong",
                "mutton": "rajma or chana",
                "beef": "rajma or chana",
                "pork": "rajma or chana",
                "turkey": "tofu or paneer",
                "shrimp": "chana or tofu",
                "prawn": "chana or tofu",
            }
            for meal in parsed.get("meals") or []:
                items = []
                for item in meal.get("items") or []:
                    text = str(item)
                    lowered = text.lower()
                    for blocked_food in blocked:
                        if blocked_food in lowered:
                            text = replacements[blocked_food]
                            break
                    items.append(text)
                meal["items"] = items
            parsed["diet_type"] = "vegetarian"

    if intent == "body_explorer":
        context_equipment = context.get("equipment") or []
        context_exercises = context.get("exercises") or []
        context_articles = context.get("articles") or []
        context_nutrition = context.get("nutrition_articles") or []
        context_products = context.get("products") or []

        allowed_equipment_ids = {item.get("id") for item in context_equipment if isinstance(item, dict)}
        filtered_equipment = []
        for item in parsed.get("equipment") or []:
            if isinstance(item, dict) and item.get("id") in allowed_equipment_ids:
                filtered_equipment.append(item)

        parsed["muscle"] = payload.get("muscle") or parsed.get("muscle") or "Chest"
        parsed["exercises"] = parsed.get("exercises") or context_exercises[:8]
        parsed["articles"] = parsed.get("articles") or context_articles[:4]
        parsed["nutrition"] = parsed.get("nutrition") or context_nutrition[:4]
        parsed["supplements"] = parsed.get("supplements") or context_products[:4]
        parsed["equipment"] = filtered_equipment or context_equipment[:6]

    return parsed


def generate_plan(user, intent, payload):
    payload = make_json_safe(dict(payload or {}))
    context = make_json_safe(load_user_context(user, intent=intent, payload=payload))
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
            logger.warning("Coach AI provider failed twice; using deterministic RedIron response: %s", second_error)
            parsed = make_json_safe(_local_response(schema_name, payload, context))
    parsed = make_json_safe(_post_process_plan(schema_name, payload, parsed, context))

    title = payload.get("title") or f"{schema_name.replace('_', ' ').title()} Plan"
    plan_type = schema_name if schema_name in dict(CoachPlan.PLAN_TYPES) else "workout"
    plan = CoachPlan.objects.create(
        user=user,
        title=title,
        plan_type=plan_type,
        input_payload=payload,
        response_json=make_json_safe(parsed),
        source_context=context,
        prompt_hash=prompt_hash,
        provider=getattr(provider, "name", ""),
        is_saved=plan_type != "chat",
    )
    return plan, False


@transaction.atomic
def send_chat_message(user, message, conversation_id=None):
    if conversation_id:
        conversation = AIConversation.objects.get(id=conversation_id, user=user)
    else:
        conversation = AIConversation.objects.create(user=user, title=build_conversation_title(message)[:80])
    ConversationMessage.objects.create(user=user, conversation=conversation, role="user", content=message)
    recent_messages = list(
        conversation.messages.order_by("-created_at")
        .values("role", "content", "structured_content", "created_at")[:10]
    )
    recent_messages.reverse()
    plan, _ = generate_plan(user, "chat", {
        "message": message,
        "conversation_id": conversation.id,
        "recent_messages": make_json_safe(recent_messages),
    })
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
