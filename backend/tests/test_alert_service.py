from app.services.alert_service import detect_alerts


def test_detect_alerts_identifies_severe_forecast_conditions() -> None:
    alerts = detect_alerts(
        "Test location",
        {"time": "2026-08-23T12:00", "weather_code": 0},
        {"weather_code": [0, 95], "precipitation_probability": [20, 80],
         "precipitation": [0, 16], "wind_speed_10m": [10, 55]},
        {"temperature_2m_max": [30], "temperature_2m_min": [20]},
    )
    assert {alert["type"] for alert in alerts} == {"thunderstorm", "heavy_rain", "strong_wind"}
    assert all(alert["official"] is False for alert in alerts)


def test_detect_alerts_identifies_extreme_temperatures() -> None:
    alerts = detect_alerts(
        "Test location",
        {"time": "2026-08-23T12:00", "weather_code": 0},
        {"weather_code": [0], "precipitation_probability": [0], "precipitation": [0], "wind_speed_10m": [0]},
        {"temperature_2m_max": [41], "temperature_2m_min": [-1]},
    )
    assert {alert["type"] for alert in alerts} == {"extreme_heat", "extreme_cold"}