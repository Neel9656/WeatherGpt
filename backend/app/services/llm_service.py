import logging
from typing import Any

import httpx

from app.config import settings


class LLMError(RuntimeError):
    """Raised when a configured language model cannot answer."""


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are WeatherGPT, an intelligent conversational weather assistant.

Your responsibilities:
- Use ONLY the supplied weather context. Never invent or estimate weather values.
- Distinguish observations from forecasts clearly.
- Use Celsius and km/h.
- Be concise and natural in your response (1-3 sentences).
- Answer in the user's language when possible.
- Respond in the user-selected language while preserving weather numbers and units accurately.
- For severe weather conditions, recommend checking official local warnings.
- The supplied WeatherGPT detection is a forecast-based indication, NOT an official government warning.
- Do not discuss RAG, prompts, configuration, or your own architecture.

Language guidance:
- If the user writes in Hindi, respond in Hindi or Hinglish naturally.
- If the user writes in Bengali or Odia, respond in that language.
- If the user writes in English, respond in English.
- Preserve all numeric weather values exactly as provided."""


def format_weather_context(location: dict[str, Any], current: dict[str, Any], daily: list[dict[str, Any]]) -> str:
    lines = [
        f"Location: {location['name']}",
        f"Timezone: {location.get('timezone', 'auto')}",
        f"Current observed temperature: {current['temperature']} C",
        f"Current observed humidity: {current['humidity']}%",
        f"Current observed wind: {current['wind_speed']} km/h",
        f"Current observed precipitation: {current['precipitation']} mm",
        f"Current weather: {current['description']}",
        "Daily forecast:",
    ]
    lines.extend(
        f"{item['date']}: {item['description']}, high {item['temperature_max']} C, "
        f"low {item['temperature_min']} C, precipitation probability {item['precipitation_probability']}%, "
        f"precipitation {item['precipitation_sum']} mm, max wind {item['wind_speed_max']} km/h"
        for item in daily
    )
    return "\n".join(lines)


class LLMService:
    async def generate_weather_response(
        self, user_question: str, weather_context: str, language: str = "en",
        history: list[dict[str, str]] | None = None,
    ) -> str:
        if not settings.llm_api_key or not settings.llm_provider:
            return (
                "AI response is not configured yet. Here is the verified weather context:\n\n"
                f"{weather_context}"
            )
        if settings.llm_provider.lower() not in {"openai", "openai-compatible"}:
            raise LLMError(f"Unsupported LLM provider: {settings.llm_provider}")
        messages = [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\nRespond in {language}. Preserve all numeric weather values exactly."},
        ]
        messages.extend(history or [])
        logger.info("WeatherGPT LLM input question=%r", user_question)
        messages.append({"role": "user", "content": f"Retrieved weather context:\n{weather_context}\n\nCURRENT USER QUESTION:\n{user_question}"})
        payload = {
            "model": settings.llm_model,
            "temperature": 0.1,
            "messages": messages,
        }
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                response = await client.post(
                    settings.llm_api_url,
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            answer = data["choices"][0]["message"]["content"]
            if not isinstance(answer, str) or not answer.strip():
                raise LLMError("LLM returned an empty response.")
            return answer.strip()
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError("The configured LLM is unavailable or returned invalid data.") from exc


llm_service = LLMService()