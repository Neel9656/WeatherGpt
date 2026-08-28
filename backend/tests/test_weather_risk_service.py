from app.services.weather_risk_service import detect_weather_risks


def test_detect_heavy_rain_risk() -> None:
    daily = [
        {"date": "2026-08-26", "precipitation_probability": 85, "precipitation_sum": 20, "wind_speed_max": 20},
        {"date": "2026-08-27", "precipitation_probability": 70, "precipitation_sum": 15, "wind_speed_max": 18},
    ]
    risks = detect_weather_risks(daily)
    assert len(risks) > 0
    assert any(r["type"] == "heavy_rain" for r in risks)


def test_detect_high_wind_risk() -> None:
    daily = [
        {"date": "2026-08-26", "precipitation_probability": 30, "precipitation_sum": 2, "wind_speed_max": 55},
    ]
    risks = detect_weather_risks(daily)
    assert any(r["type"] == "strong_wind" for r in risks)


def test_detect_extreme_temperature_risk() -> None:
    daily = [
        {"date": "2026-08-26", "temperature_max": 42, "temperature_min": 28, "precipitation_probability": 10, "precipitation_sum": 0, "wind_speed_max": 15},
    ]
    risks = detect_weather_risks(daily)
    assert any(r["type"] == "extreme_heat" for r in risks)


def test_no_risk_when_conditions_normal() -> None:
    daily = [
        {"date": "2026-08-26", "temperature_max": 28, "temperature_min": 20, "precipitation_probability": 20, "precipitation_sum": 1, "wind_speed_max": 12},
    ]
    risks = detect_weather_risks(daily)
    assert len(risks) == 0
