REQUIRED_KEYS = {
    "workout": ["goal", "summary", "weekly_split", "daily_workouts", "estimated_calories", "difficulty"],
    "nutrition": ["calories", "protein", "carbs", "fat", "meals", "shopping_list", "water", "supplements"],
    "transformation": ["current", "target", "timeline", "weekly_goals", "milestones", "recommendations"],
    "chat": ["answer", "cards", "recommendations"],
    "supplement": ["summary", "products", "timing", "warnings"],
    "equipment": ["summary", "equipment", "recommendations"],
    "body_explorer": ["muscle", "exercises", "articles", "nutrition", "supplements", "equipment"],
}


class ResponseValidationError(ValueError):
    pass


def validate_response(schema_name, data):
    if not isinstance(data, dict):
        raise ResponseValidationError("AI response must be a JSON object.")
    missing = [key for key in REQUIRED_KEYS.get(schema_name, []) if key not in data]
    if missing:
        raise ResponseValidationError(f"AI response missing required keys: {', '.join(missing)}")
    return data

