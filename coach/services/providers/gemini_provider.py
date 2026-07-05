import json
import os
import urllib.error
import urllib.request

from .base_provider import AIProviderError, BaseAIProvider


class GeminiProvider(BaseAIProvider):
    name = "gemini"

    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        configured_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        fallback_models = os.environ.get(
            "GEMINI_FALLBACK_MODELS",
            "gemini-2.5-flash,gemini-2.5-flash-lite,gemini-2.0-flash,gemini-1.5-flash,gemini-1.5-flash-latest,gemini-pro",
        )
        self.models = [configured_model] + [item.strip() for item in fallback_models.split(",") if item.strip()]

    def generate_json(self, prompt, schema_name):
        if not self.api_key:
            raise AIProviderError("GEMINI_API_KEY is not configured.")

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.35,
            },
        }
        last_error = None
        for model in dict.fromkeys(self.models):
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={self.api_key}"
            )
            request = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=35) as response:
                    data = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in {404, 429, 503}:
                    raise AIProviderError(f"Gemini request failed with HTTP {exc.code}.") from exc
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
        else:
            raise AIProviderError("Gemini request failed.") from last_error

        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError("Gemini returned an unexpected response.") from exc
