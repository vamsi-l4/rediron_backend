import json


SCHEMA_INSTRUCTIONS = {
    "workout": {
        "goal": "string",
        "summary": "string",
        "weekly_split": ["string"],
        "daily_workouts": [{"day": "string", "focus": "string", "exercises": [{"name": "string", "sets": 3, "reps": "8-12", "tempo": "string", "rest": "string", "exercise_url": "string"}], "warmup": ["string"], "cooldown": ["string"], "tips": ["string"]}],
        "estimated_calories": 0,
        "difficulty": "string",
    },
    "nutrition": {
        "calories": 0,
        "protein": 0,
        "carbs": 0,
        "fat": 0,
        "meals": [{"name": "string", "time": "string", "items": ["string"], "calories": 0, "protein": 0}],
        "shopping_list": ["string"],
        "water": "string",
        "supplements": [{"name": "string", "product_url": "string", "timing": "string"}],
        "timing": ["string"],
        "budget": "string",
    },
    "transformation": {
        "current": {},
        "target": {},
        "timeline": ["string"],
        "weekly_goals": ["string"],
        "milestones": ["string"],
        "warnings": ["string"],
        "recommendations": ["string"],
    },
    "chat": {"answer": "markdown string", "cards": [], "recommendations": []},
    "supplement": {"summary": "string", "products": [], "timing": [], "warnings": []},
    "equipment": {"summary": "string", "equipment": [], "recommendations": []},
    "body_explorer": {"muscle": "string", "exercises": [], "articles": [], "nutrition": [], "supplements": [], "equipment": []},
}


def build_prompt(intent, payload, context):
    schema = SCHEMA_INSTRUCTIONS.get(intent, SCHEMA_INSTRUCTIONS["chat"])
    compact_context = json.dumps(context, default=str, ensure_ascii=True)[:18000]
    compact_payload = json.dumps(payload or {}, default=str, ensure_ascii=True)
    compact_schema = json.dumps(schema, default=str, ensure_ascii=True)
    return f"""
You are RedIron Coach AI, the premium native intelligence layer for RedIron Fitness.
Return ONLY valid JSON. Do not wrap in markdown. Do not include plain text outside JSON.
Use existing RedIron records first. Do not invent exercise, product, equipment, or article links when matching records exist.
Be specific, safe, and practical. Avoid medical diagnosis. Include injury-aware modifications when injuries are provided.
For chat intent, answer the latest user message directly and use recent_messages as conversation memory.
If the user asks about progress, hydration, calories, workouts, saved plans, orders, products, or profile data, ground the answer in the supplied RedIron context and clearly say when a value is missing.
Do not repeat a previous plan unless the user asks to repeat it; vary exercises, meals, timing, and recommendations using the supplied previous_plans as memory.
If diet_type is veg or vegetarian, do not include chicken, fish, eggs, meat, seafood, or non-vegetarian foods. Use paneer, tofu, dal, chana, rajma, curd, milk, soy, nuts, seeds, and vegetarian Indian meals instead.
If the requested exercise, product, equipment, or article is not present in RedIron context, leave its URL blank and explain the recommendation without pretending it exists in the database.
For workout daily_workouts exercises, use exact exercise names from Available RedIron context whenever possible.
For body_explorer intent, only recommend exercises and equipment from the supplied context for the requested muscle. If context has no equipment for that muscle, return an empty equipment array instead of generic racks or unrelated machines.

Intent: {intent}
User request/input JSON: {compact_payload}
Available RedIron context JSON: {compact_context}
Required response JSON shape: {compact_schema}
"""
