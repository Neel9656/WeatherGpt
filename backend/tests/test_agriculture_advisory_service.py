from app.services.agriculture_advisory_service import agriculture_advisory, find_suitable_agriculture_window


def test_pesticide_window_uses_hourly_rain_and_wind() -> None:
    hourly = [
        {"time": "2026-08-27T08:00", "temperature": 29, "precipitation": 4, "precipitation_probability": 92, "wind_speed": 14, "weather_code": 61},
        {"time": "2026-08-27T09:00", "temperature": 30, "precipitation": 7.2, "precipitation_probability": 85, "wind_speed": 16, "weather_code": 63},
    ]
    window = find_suitable_agriculture_window(hourly, "2026-08-27", "morning")
    assert window["suitable"] is False
    assert window["rain_probability"] == 92
    assert window["expected_precipitation_mm"] == 11.2
    assert window["wind_speed_kmh"] == 16


def test_pesticide_advisory_answers_decision_and_mentions_label() -> None:
    result = agriculture_advisory(
        "pesticide_application",
        [{"time": "2026-08-27T08:00", "temperature": 28, "precipitation": 0, "precipitation_probability": 10, "wind_speed": 12, "weather_code": 0}],
        [{"date": "2026-08-26", "precipitation_probability": 10, "precipitation_sum": 0}],
        "2026-08-27",
        "morning",
        "rice",
    )
    assert "spraying" in result["answer"]
    assert "rice" in result["answer"]
    assert "pesticide label" in result["answer"]
