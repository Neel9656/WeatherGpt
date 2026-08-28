import pytest

from app.services.llm_service import LLMService, format_weather_context
from app.services.translation_service import localized_fallback


def test_weather_context_contains_only_supplied_values() -> None:
    context = format_weather_context(
        {"name": "Bhubaneswar", "timezone": "Asia/Kolkata"},
        {"temperature": 30, "humidity": 70, "wind_speed": 12, "precipitation": 0, "description": "Clear sky"},
        [{"date": "2026-08-23", "description": "Light rain", "temperature_max": 31, "temperature_min": 25,
          "precipitation_probability": 70, "precipitation_sum": 4, "wind_speed_max": 20}],
    )
    assert "30 C" in context
    assert "70%" in context
    assert "Light rain" in context


@pytest.mark.asyncio
async def test_llm_without_configuration_returns_transparent_context(monkeypatch) -> None:
    monkeypatch.setattr("app.services.llm_service.settings.llm_api_key", None)
    monkeypatch.setattr("app.services.llm_service.settings.llm_provider", None)
    answer = await LLMService().generate_weather_response("Will it rain?", "Rain probability: 70%")
    assert "not configured" in answer
    assert "70%" in answer


def test_hindi_fallback_is_localized_without_changing_context_values() -> None:
    answer = localized_fallback("hi", "Current observed temperature: 30 C")
    assert "AI प्रदाता" in answer
    assert "30 C" in answer