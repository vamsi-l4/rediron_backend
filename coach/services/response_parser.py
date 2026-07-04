import json
import re

from .json_validator import validate_response


def parse_ai_json(raw_text, schema_name):
    if isinstance(raw_text, dict):
        return validate_response(schema_name, raw_text)

    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group(0))
    return validate_response(schema_name, parsed)

