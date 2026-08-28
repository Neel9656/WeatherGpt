from typing import Any


def detect_weather_risks(daily: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Analyze daily forecast data and identify weather risks."""
    risks: list[dict[str, str]] = []

    if not daily:
        return risks

    next_days = daily[:3]

    for day in next_days:
        probability = day.get("precipitation_probability", 0) or 0
        precipitation = day.get("precipitation_sum", 0) or 0

        if probability >= 70 and precipitation >= 10:
            risks.append({
                "type": "heavy_rain",
                "severity": "high",
                "message": f"Heavy rainfall expected on {day.get('date', 'upcoming day')} with {probability}% probability.",
            })

        wind = day.get("wind_speed_max", 0) or 0
        if wind >= 50:
            risks.append({
                "type": "strong_wind",
                "severity": "high",
                "message": f"Strong winds expected on {day.get('date', 'upcoming day')} up to {wind} km/h.",
            })

        temp_max = day.get("temperature_max", 0) or 0
        if temp_max >= 40:
            risks.append({
                "type": "extreme_heat",
                "severity": "high",
                "message": f"Very high temperature expected on {day.get('date', 'upcoming day')}: {temp_max}°C.",
            })

        temp_min = day.get("temperature_min", 0) or 0
        if temp_min <= 0:
            risks.append({
                "type": "extreme_cold",
                "severity": "moderate",
                "message": f"Very low temperature expected on {day.get('date', 'upcoming day')}: {temp_min}°C.",
            })

    return risks
