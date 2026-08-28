from fastapi.testclient import TestClient

from app.main import app
from app.api import chat_routes


def test_seven_distinct_chat_queries_use_current_message(monkeypatch) -> None:
    async def fake_current(latitude, longitude):
        return {"timezone": "Asia/Kolkata", "current": {"time": "2026-08-27T12:00", "temperature_2m": 30, "relative_humidity_2m": 70, "wind_speed_10m": 12, "precipitation": 0, "weather_code": 0, "surface_pressure": 1008}}

    async def fake_daily(latitude, longitude):
        return {"daily": {"time": ["2026-08-27", "2026-08-28", "2026-08-29"], "temperature_2m_max": [31, 34, 29], "temperature_2m_min": [25, 26, 24], "precipitation_probability_max": [40, 10, 90], "precipitation_sum": [3, 0, 18], "wind_speed_10m_max": [20, 18, 30], "weather_code": [61, 0, 95]}}

    async def failing_llm(*args, **kwargs):
        raise chat_routes.LLMError("disabled for test")

    monkeypatch.setattr(chat_routes.open_meteo_service, "get_current_weather", fake_current)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_daily_forecast", fake_daily)
    monkeypatch.setattr(chat_routes.llm_service, "generate_weather_response", failing_llm)
    location = {"name": "Bhubaneswar", "latitude": 20.2961, "longitude": 85.8245, "timezone": "Asia/Kolkata"}
    questions = ["What is the weather right now?", "Will it rain today?", "What about tomorrow?", "Should I carry an umbrella today?", "Should I plan travel around the weather this week?", "Is there any flood risk?", "Kya kal baarish hogi?"]
    answers = []
    with TestClient(app) as client:
        for question in questions:
            response = client.post("/api/chat", json={"message": question, "location": location})
            assert response.status_code == 200, response.text
            payload = response.json()
            assert isinstance(payload["answer"], str) and payload["answer"]
            answers.append(payload["answer"])
    assert len(set(answers)) == len(questions)
    assert "tomorrow" in answers[2].lower()
    assert "umbrella" in answers[3].lower()