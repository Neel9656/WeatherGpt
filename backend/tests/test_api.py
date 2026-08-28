from fastapi.testclient import TestClient

from app.main import app
from app.api import chat_routes


def test_health_check() -> None:
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_requires_a_location() -> None:
    response = TestClient(app).post("/api/chat", json={"message": "Weather?"})
    assert response.status_code == 400
    assert "location" in response.json()["detail"]


def test_chat_accepts_selected_location_object_without_audience(monkeypatch) -> None:
    async def fake_locations(query):
        return []

    async def fake_current(latitude, longitude):
        return {"timezone": "Asia/Kolkata", "current": {"temperature_2m": 30, "relative_humidity_2m": 70,
            "wind_speed_10m": 12, "precipitation": 0, "weather_code": 0}}

    async def fake_daily(latitude, longitude):
        return {"daily": {"time": ["2026-08-23", "2026-08-24"], "temperature_2m_max": [31, 32],
            "temperature_2m_min": [25, 25], "precipitation_probability_max": [10, 70],
            "precipitation_sum": [0, 4], "wind_speed_10m_max": [15, 20], "weather_code": [0, 61]}}

    async def fake_llm(question, context, language, history=None):
        return "Rain is likely tomorrow in Bhubaneswar."

    monkeypatch.setattr(chat_routes, "search_locations", fake_locations)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_current_weather", fake_current)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_daily_forecast", fake_daily)
    monkeypatch.setattr(chat_routes.llm_service, "generate_weather_response", fake_llm)

    response = TestClient(app).post(
        "/api/chat",
        json={
            "message": "Will it rain tomorrow?",
            "location": {"name": "Bhubaneswar", "latitude": 20.2961, "longitude": 85.8245, "timezone": "Asia/Kolkata"},
            "conversation_history": [
                {"role": "user", "content": "Will it rain tomorrow?"},
                {"role": "assistant", "content": "There is a chance of rain."},
                {"role": "user", "content": "What about the evening?"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["location"]["name"] == "Bhubaneswar"
    assert "audience" not in response.json()


def test_chat_returns_verified_fallback_when_llm_is_unavailable(monkeypatch) -> None:
    async def fake_locations(query):
        return [{"name": "Bhubaneswar", "latitude": 20.2961, "longitude": 85.8245}]

    async def fake_current(latitude, longitude):
        return {"timezone": "Asia/Kolkata", "current": {"temperature_2m": 30, "relative_humidity_2m": 70,
            "wind_speed_10m": 12, "precipitation": 0, "weather_code": 0}}

    async def fake_daily(latitude, longitude):
        return {"daily": {"time": ["2026-08-23", "2026-08-24"], "temperature_2m_max": [31, 32],
            "temperature_2m_min": [25, 25], "precipitation_probability_max": [10, 70],
            "precipitation_sum": [0, 4], "wind_speed_10m_max": [15, 20], "weather_code": [0, 61]}}

    async def failing_llm(question, context, language):
        raise chat_routes.LLMError("provider unavailable")

    monkeypatch.setattr(chat_routes, "search_locations", fake_locations)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_current_weather", fake_current)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_daily_forecast", fake_daily)
    monkeypatch.setattr(chat_routes.llm_service, "generate_weather_response", failing_llm)
    response = TestClient(app).post("/api/chat", json={"message": "Will it rain tomorrow in Bhubaneswar?"})
    assert response.status_code == 200
    assert response.json()["llm_available"] is False
    assert "verified weather context" in response.json()["answer"] or "verified weather data" in response.json()["answer"]


def test_chat_explicit_kolkata_overrides_dashboard_and_uses_agriculture_hourly(monkeypatch) -> None:
    calls = {"location": [], "hourly": 0}

    async def fake_locations(query):
        calls["location"].append(query)
        return [{"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639, "timezone": "Asia/Kolkata"}]

    async def fake_current(latitude, longitude):
        assert (latitude, longitude) == (22.5726, 88.3639)
        return {"timezone": "Asia/Kolkata", "current": {"temperature_2m": 30, "relative_humidity_2m": 70,
            "wind_speed_10m": 12, "precipitation": 0, "weather_code": 0}}

    async def fake_daily(latitude, longitude):
        return {"daily": {"time": ["2026-08-26", "2026-08-27"], "temperature_2m_max": [31, 32],
            "temperature_2m_min": [25, 25], "precipitation_probability_max": [10, 92],
            "precipitation_sum": [0, 11.2], "wind_speed_10m_max": [15, 20], "weather_code": [0, 61]}}

    async def fake_hourly(latitude, longitude):
        calls["hourly"] += 1
        return {"hourly": {"time": ["2026-08-27T08:00", "2026-08-27T09:00"], "temperature_2m": [29, 30],
            "precipitation": [4, 7.2], "precipitation_probability": [92, 85], "wind_speed_10m": [14, 16], "weather_code": [61, 63]}}

    async def fake_llm(question, context, language, history=None):
        return "Generic weather context."

    monkeypatch.setattr(chat_routes, "search_locations", fake_locations)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_current_weather", fake_current)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_daily_forecast", fake_daily)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_hourly_forecast", fake_hourly)
    monkeypatch.setattr(chat_routes.llm_service, "generate_weather_response", fake_llm)

    response = TestClient(app).post("/api/chat", json={
        "message": "Can I use pesticides in my farm tomorrow if I am in Kolkata?",
        "location": {"name": "Bhubaneswar", "latitude": 20.2961, "longitude": 85.8245, "timezone": "Asia/Kolkata"},
    })

    payload = response.json()
    assert response.status_code == 200
    assert calls["location"] == ["Kolkata"]
    assert calls["hourly"] == 1
    assert payload["location"]["name"] == "Kolkata"
    assert payload["location"]["latitude"] == 22.5726
    assert payload["location"]["longitude"] == 88.3639
    assert payload["intent"]["domain"] == "agriculture"
    assert payload["intent"]["intent"] == "pesticide_application"
    assert "postponing pesticide spraying" in payload["answer"]
    assert payload["agriculture_advisory"]["window"]["expected_precipitation_mm"] == 11.2


def test_chat_explicit_delhi_overrides_dashboard_for_normal_weather(monkeypatch) -> None:
    async def fake_locations(query):
        assert query == "Delhi"
        return [{"name": "Delhi", "latitude": 28.6139, "longitude": 77.2090}]

    async def fake_current(latitude, longitude):
        assert (latitude, longitude) == (28.6139, 77.2090)
        return {"timezone": "Asia/Kolkata", "current": {"temperature_2m": 30, "relative_humidity_2m": 70,
            "wind_speed_10m": 12, "precipitation": 0, "weather_code": 0}}

    async def fake_daily(latitude, longitude):
        return {"daily": {"time": ["2026-08-26", "2026-08-27"], "temperature_2m_max": [31, 32],
            "temperature_2m_min": [25, 25], "precipitation_probability_max": [10, 20],
            "precipitation_sum": [0, 0], "wind_speed_10m_max": [15, 20], "weather_code": [0, 0]}}

    async def fake_llm(question, context, language, history=None):
        return "Delhi forecast."

    monkeypatch.setattr(chat_routes, "search_locations", fake_locations)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_current_weather", fake_current)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_daily_forecast", fake_daily)
    monkeypatch.setattr(chat_routes.llm_service, "generate_weather_response", fake_llm)
    response = TestClient(app).post("/api/chat", json={
        "message": "What is the weather in Delhi tomorrow?",
        "location": {"name": "Bhubaneswar", "latitude": 20.2961, "longitude": 85.8245},
    })
    assert response.status_code == 200
    assert response.json()["location"]["name"] == "Delhi"


def test_chat_natural_farm_location_extracts_kolkata(monkeypatch) -> None:
    async def fake_locations(query):
        assert query == "Kolkata"
        return [{"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639, "timezone": "Asia/Kolkata"}]

    async def fake_current(latitude, longitude):
        assert (latitude, longitude) == (22.5726, 88.3639)
        return {"timezone": "Asia/Kolkata", "current": {"temperature_2m": 30, "relative_humidity_2m": 70,
            "wind_speed_10m": 12, "precipitation": 0, "weather_code": 0}}

    async def fake_daily(latitude, longitude):
        return {"daily": {"time": ["2026-08-26", "2026-08-27"], "temperature_2m_max": [31, 32],
            "temperature_2m_min": [25, 25], "precipitation_probability_max": [10, 92],
            "precipitation_sum": [0, 11.2], "wind_speed_10m_max": [15, 20], "weather_code": [0, 61]}}

    async def fake_hourly(latitude, longitude):
        return {"hourly": {"time": ["2026-08-27T08:00"], "temperature_2m": [29],
            "precipitation": [4], "precipitation_probability": [92], "wind_speed_10m": [14], "weather_code": [61]}}

    async def fake_llm(question, context, language, history=None):
        return "Generic weather context."

    monkeypatch.setattr(chat_routes, "search_locations", fake_locations)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_current_weather", fake_current)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_daily_forecast", fake_daily)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_hourly_forecast", fake_hourly)
    monkeypatch.setattr(chat_routes.llm_service, "generate_weather_response", fake_llm)
    response = TestClient(app).post("/api/chat", json={
        "message": "Will it be a good thing to spray pesticides in my farm in Kolkata",
        "location": {"name": "Bhubaneswar", "latitude": 20.2961, "longitude": 85.8245},
    })
    payload = response.json()
    assert response.status_code == 200
    assert payload["location"]["name"] == "Kolkata"
    assert payload["intent"]["domain"] == "agriculture"
    assert payload["intent"]["intent"] == "pesticide_application"
    assert payload["agriculture_advisory"]["window"]["expected_precipitation_mm"] == 4


def test_chat_uses_selected_location_alias_and_recent_history(monkeypatch) -> None:
    async def fake_locations(query):
        assert query == "Kolkata"
        return [{"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639}]

    async def fake_current(latitude, longitude):
        return {"timezone": "Asia/Kolkata", "current": {"time": "2026-08-28T12:00", "temperature_2m": 30, "relative_humidity_2m": 70, "wind_speed_10m": 12, "precipitation": 0, "surface_pressure": 1008, "weather_code": 0}}

    async def fake_daily(latitude, longitude):
        return {"daily": {"time": ["2026-08-28", "2026-08-29", "2026-08-30"], "temperature_2m_max": [31, 32, 33], "temperature_2m_min": [25, 26, 27], "precipitation_probability_max": [10, 20, 30], "precipitation_sum": [0, 1, 2], "wind_speed_10m_max": [15, 20, 25], "weather_code": [0, 61, 63]}}

    monkeypatch.setattr(chat_routes, "search_locations", fake_locations)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_current_weather", fake_current)
    monkeypatch.setattr(chat_routes.open_meteo_service, "get_daily_forecast", fake_daily)
    response = TestClient(app).post("/api/chat", json={
        "message": "What about tomorrow?",
        "selected_location": {"name": "Bhubaneswar", "latitude": 20.2961, "longitude": 85.8245},
        "conversation_history": [{"role": "user", "content": "Will it rain in Kolkata?"}],
    })
    assert response.status_code == 200
    assert response.json()["location"]["name"] == "Kolkata"
    assert response.json()["weather"]["selected_forecast"]["date"] == "2026-08-29"