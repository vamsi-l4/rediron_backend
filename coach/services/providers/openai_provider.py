import os

from .base_provider import AIProviderError, BaseAIProvider


class OpenAIProvider(BaseAIProvider):
    name = "openai"

    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def generate_json(self, prompt, schema_name):
        if not self.api_key:
            raise AIProviderError("OPENAI_API_KEY is not configured.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AIProviderError("openai package is not installed.") from exc

        try:
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.35,
                timeout=35,
            )
            return response.choices[0].message.content
        except Exception as exc:
            raise AIProviderError("OpenAI request failed.") from exc

