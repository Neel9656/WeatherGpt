from fastapi.testclient import TestClient

from app.api import chat_routes
from app.main import app


def test_previous_temporary_location_does_not_override_dashboard(monkeypatch) -> None:
    locations = []

    async def fake_locations(query):
        locations.append(query)
        return [{"name": query, "latitude": 23.34, "longitude": 85.31, "timezone": "Asia/Kolkata"}]

    async def fake_current(latitude, longitude):
        return {"timezone": "Asia/Kolkata", "current": {"time": "2026-08-27T12:00", "temperature_2m": 30, "relative_humidity_2m": 70, "wind_speed_10m": 12, "precipitation": 0, "weather_code": 0, "surface_pressure": 1008}}

    async def fake_daily(latitude, longitude):
        return {"daily": {"time": ["2026-08-27", "2026-08-28"], "temperature_2m_max": [31, 32], "temperature_2m_min": [25, 26], "precipitation_probability_max": [10, 20], "precipitation_sum": [0, 0], "wind_speed_10m_max": [15, 20], "weather_code": [0, 0]}}

    async def failing_llm(*args, **kwargs):
        raise chat_routes.LLMError("disabled")

    monkeypatch.setattr(chat_routes, "search_locations", fake_locations)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_current_weather", fake_current)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_daily_forecast", fake_daily)
    monkeypatch.setattr(chat_routes.llm_service, "generate_weather_response", failing_llm)
    dashboard = {"name": "Bhubaneswar", "latitude": 20.2961, "longitude": 85.8245, "timezone": "Asia/Kolkata"}
    with TestClient(app) as client:
        first = client.post("/api/chat", json={"message": "Weather in Ranchi today?", "location": dashboard})
        second = client.post("/api/chat", json={"message": "Will it rain tomorrow?", "location": dashboard, "conversation_history": [{"role": "user", "content": "Weather in Ranchi today?"}]})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["location"]["name"] == "Ranchi"
    assert second.json()["location"]["name"] == "Ranchi"
    assert locations == ["Ranchi", "Ranchi"]
