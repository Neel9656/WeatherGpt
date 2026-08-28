import pytest
from fastapi.testclient import TestClient

from app.api import chat_routes
from app.main import app
from app.services.translation_service import grounded_weather_answer
from app.services.intent_service import detect_intent, extract_location_from_message
from app.services.location_service import resolve_location


async def fake_current(latitude, longitude):
    return {"timezone": "Asia/Kolkata", "current": {"time": "2026-08-28T12:00", "temperature_2m": 30, "relative_humidity_2m": 70, "wind_speed_10m": 12, "precipitation": 0, "surface_pressure": 1008, "weather_code": 0}}


async def fake_daily(latitude, longitude):
    return {"daily": {"time": ["2026-08-28", "2026-08-29", "2026-08-30"], "temperature_2m_max": [31, 32, 33], "temperature_2m_min": [25, 26, 27], "precipitation_probability_max": [10, 78, 90], "precipitation_sum": [0, 12, 18], "wind_speed_10m_max": [15, 20, 25], "weather_code": [0, 61, 95]}}


def test_plain_english_tomorrow_uses_tomorrow_forecast(monkeypatch):
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_current_weather", fake_current)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_daily_forecast", fake_daily)
    response = TestClient(app).post("/api/chat", json={"message": "will it rain tomorrow", "selected_location": {"name": "Bhubaneswar", "latitude": 20.2961, "longitude": 85.8245}})
    payload = response.json()
    assert response.status_code == 200
    assert payload["time_period"] == "tomorrow"
    assert payload["weather"]["selected_forecast"]["date"] == "2026-08-29"
    assert "today" not in payload["answer"].lower()


def test_weekend_forecast_keeps_active_location(monkeypatch):
    async def unexpected_location_search(query):
        raise AssertionError(f"weekend phrase must not be geocoded: {query}")

    monkeypatch.setattr(chat_routes, "search_locations", unexpected_location_search)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_current_weather", fake_current)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_daily_forecast", fake_daily)
    response = TestClient(app).post("/api/chat", json={
        "message": "What is the weekend forecast?",
        "selected_location": {"name": "Bhubaneswar", "latitude": 20.356, "longitude": 85.819},
    })
    assert response.status_code == 200
    assert response.json()["location"]["name"] == "Bhubaneswar"
    assert response.json()["time_period"] == "weekend"
    assert [item["date"] for item in response.json()["weekend_forecasts"]] == ["2026-08-29", "2026-08-30"]
    assert "2026-08-29" in response.json()["answer"]
    assert "2026-08-30" in response.json()["answer"]


def test_generic_coordinates_get_real_display_name(monkeypatch):
    async def fake_display_location(latitude, longitude, fallback_name=None):
        return {"name": "Bhubaneswar", "displayName": "Bhubaneswar, Odisha, India", "admin1": "Odisha", "state": "Odisha", "country": "India", "latitude": latitude, "longitude": longitude, "location_type": "city", "type": "city", "source": "gps"}

    monkeypatch.setattr(chat_routes, "resolve_display_location", fake_display_location)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_current_weather", fake_current)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_daily_forecast", fake_daily)
    response = TestClient(app).post("/api/chat", json={"message": "What is the weather right now?", "selected_location": {"name": "Current location", "latitude": 20.2961, "longitude": 85.8245}})
    assert response.json()["resolved_location"]["name"] == "Bhubaneswar"


def test_multilingual_fallback_uses_verified_values():
    current = {"temperature": 30, "humidity": 70, "wind_speed": 12, "description": "Clear sky"}
    forecast = {"date": "2026-08-29", "description": "Slight rain", "temperature_max": 32, "temperature_min": 26, "precipitation_probability": 78, "precipitation_sum": 12, "wind_speed_max": 20}
    answers = [grounded_weather_answer(language, "Kolkata", "rain", current, [forecast], "rain_tomorrow", forecast, "tomorrow") for language in ("en", "hinglish", "hi", "bn", "or")]
    assert all("78" in answer and "12" in answer for answer in answers)
    assert any("baarish" in answer for answer in answers)
    assert any("বৃষ্ট" in answer for answer in answers)
    assert any("ବର୍ଷା" in answer for answer in answers)


def test_dynamic_location_extraction_supports_requested_scripts():
    assert extract_location_from_message("What is the weather in London?") == "London"
    assert extract_location_from_message("Kya kal Ranchi me baarish hogi?") == "Ranchi"
    assert extract_location_from_message("कल रांची में बारिश होगी?") == "रांची"
    assert extract_location_from_message("কাল কলকাতায় বৃষ্টি হবে?") == "Kolkata"
    assert extract_location_from_message("ଭୁବନେଶ୍ୱରରେ କାଲି ବର୍ଷା ହେବ କି?") == "ଭୁବନେଶ୍ୱର"
    assert detect_intent("will it rain tomorrow").date_reference == "tomorrow"
    assert detect_intent("কাল কলকাতায় বৃষ্টি হবে?").date_reference == "tomorrow"
    assert detect_intent("ଭୁବନେଶ୍ୱରରେ କାଲି ବର୍ଷା ହେବ କି?").date_reference == "tomorrow"


@pytest.mark.asyncio
async def test_location_resolver_returns_dynamic_canonical_object():
    class FakeLocationService:
        async def _get(self, url, params):
            return {"results": [{"name": params["name"], "latitude": 51.5074, "longitude": -0.1278, "country": "United Kingdom", "admin1": "England", "country_code": "gb", "feature_code": "PPL"}]}

    location = await resolve_location("London", FakeLocationService())
    assert location["name"] == "London"
    assert location["displayName"] == "London, England, United Kingdom"
    assert location["source"] == "explicit_query"


def test_unknown_explicit_location_does_not_fall_back_to_dashboard(monkeypatch):
    async def no_results(query):
        return []

    monkeypatch.setattr(chat_routes, "search_locations", no_results)
    response = TestClient(app).post("/api/chat", json={
        "message": "What is the weather in NotARealPlace?",
        "selected_location": {"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639},
    })
    assert response.status_code == 404
    assert "couldn't identify" in response.json()["detail"]
