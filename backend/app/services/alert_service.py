from datetime import datetime
from typing import Any


def _maximum(values: list[Any]) -> float | None:
    valid = [float(value) for value in values if isinstance(value, (int, float))]
    return max(valid) if valid else None


def _minimum(values: list[Any]) -> float | None:
    valid = [float(value) for value in values if isinstance(value, (int, float))]
    return min(valid) if valid else None


def detect_alerts(location: str, current: dict[str, Any], hourly: dict[str, Any], daily: dict[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    timestamp = datetime.fromisoformat(current["time"]).isoformat()

    def add_alert(alert_type: str, severity: str, title: str, message: str, reason: str, recommendations: list[str]) -> None:
        alerts.append({"id": f"{alert_type}-{timestamp}", "type": alert_type, "severity": severity, "title": title,
                       "message": message, "reason": reason, "location": location, "affected_location": location,
                       "start_time": timestamp, "timestamp": timestamp, "recommendations": recommendations,
                       "source": "WeatherGPT Risk Engine", "official": False})

    if current["weather_code"] in {95, 96, 99} or any(code in {95, 96, 99} for code in hourly["weather_code"][:24]):
        add_alert("thunderstorm", "high", "Thunderstorm Risk", "Thunderstorm conditions are possible in the next 24-hour forecast.", "Thunderstorm weather codes were found in live forecast data.", ["Stay indoors during lightning.", "Monitor official local guidance."])
    max_rain = _maximum(hourly["precipitation"][:24])
    max_probability = _maximum(hourly["precipitation_probability"][:24])
    if max_rain is not None and max_probability is not None:
        if max_rain >= 50:
            add_alert("heavy_rain", "severe", "Heavy Rain Alert", "Extremely heavy rainfall is possible in the next 24-hour forecast.", "Forecast rainfall exceeded 50 mm in an hourly period.", ["Avoid waterlogged roads.", "Follow local authority instructions."])
        elif max_rain >= 30 or max_probability >= 85:
            add_alert("heavy_rain", "high", "Heavy Rain Alert", "Heavy rainfall is possible in the next 24-hour forecast.", "Forecast rainfall or precipitation probability exceeded the configured threshold.", ["Avoid waterlogged roads.", "Allow extra travel time."])
        elif max_rain >= 8 or max_probability >= 60:
            add_alert("heavy_rain", "moderate", "Rainfall Risk", "Significant rain is possible in the next 24-hour forecast.", "Forecast rainfall or precipitation probability indicates a moderate rain risk.", ["Carry rain protection.", "Check the forecast before travelling."])
    daily_rain = _maximum(daily.get("precipitation_sum", [])[:7])
    if (max_rain is not None and max_rain >= 30) or (daily_rain is not None and daily_rain >= 50):
        add_alert("flood_risk", "high", "Possible Urban Flooding", "Intense or accumulated rainfall may cause waterlogging in vulnerable areas.", "WeatherGPT forecast risk assessment based on rainfall intensity and accumulation; this is not an official flood warning.", ["Avoid low-lying and waterlogged roads.", "Follow local authority instructions."])
    max_wind = _maximum(hourly["wind_speed_10m"][:24])
    if max_wind is not None and max_wind >= 50:
        add_alert("strong_wind", "high", "Strong Wind Alert", "Strong winds are possible in the next 24-hour forecast.", "Forecast wind speed exceeded 50 km/h.", ["Secure loose outdoor items.", "Check transport status before departure."])
    max_temp = _maximum(daily["temperature_2m_max"][:7])
    if max_temp is not None and max_temp >= 40:
        add_alert("extreme_heat", "high", "Extreme Heat Alert", "Very high temperatures are expected in the 7-day forecast.", "Forecast maximum temperature reached 40 C or higher.", ["Limit prolonged outdoor exposure.", "Drink water regularly."])
    min_temp = _minimum(daily["temperature_2m_min"][:7])
    if min_temp is not None and min_temp <= 0:
        add_alert("extreme_cold", "moderate", "Extreme Cold Risk", "Very low temperatures are possible in the 7-day forecast.", "Forecast minimum temperature reached 0 C or lower.", ["Dress warmly and protect sensitive crops."])
    return alerts


def normalize_alert_inputs(current_data: dict[str, Any], hourly_data: dict[str, Any], daily_data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    current, hourly, daily = current_data["current"], hourly_data["hourly"], daily_data["daily"]
    return ({"time": current["time"], "weather_code": current["weather_code"]},
            {"weather_code": hourly["weather_code"], "precipitation_probability": hourly["precipitation_probability"], "precipitation": hourly["precipitation"], "wind_speed_10m": hourly["wind_speed_10m"]},
            {"temperature_2m_max": daily["temperature_2m_max"], "temperature_2m_min": daily["temperature_2m_min"], "precipitation_sum": daily["precipitation_sum"]})
