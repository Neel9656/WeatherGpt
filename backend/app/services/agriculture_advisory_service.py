from datetime import datetime
from typing import Any


AGRICULTURE_THRESHOLDS = {
    "max_spray_rain_probability": 40,
    "max_spray_precipitation_mm": 0.5,
    "max_spray_wind_kmh": 25,
    "min_spray_temperature_c": 5,
    "max_spray_temperature_c": 35,
}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_target_period(item: dict[str, Any], target_date: str | None, time_reference: str | None) -> bool:
    timestamp = str(item.get("time", ""))
    if target_date and not timestamp.startswith(target_date):
        return False
    if time_reference not in {"morning", "afternoon", "evening", "tonight"}:
        return True
    try:
        hour = datetime.fromisoformat(timestamp).hour
    except ValueError:
        return True
    ranges = {"morning": (6, 12), "afternoon": (12, 18), "evening": (18, 24), "tonight": (18, 24)}
    start, end = ranges[time_reference]
    return start <= hour < end


def find_suitable_agriculture_window(
    hourly: list[dict[str, Any]],
    target_date: str | None = None,
    time_reference: str | None = None,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    limits = {**AGRICULTURE_THRESHOLDS, **(thresholds or {})}
    periods = [item for item in hourly if _is_target_period(item, target_date, time_reference)]
    if not periods:
        return {"suitable": False, "reason": "No hourly forecast is available for the requested period.", "best_window": None}

    rain_probability = max(_number(item.get("precipitation_probability")) for item in periods)
    expected_precipitation = sum(_number(item.get("precipitation")) for item in periods)
    wind_speed = max(_number(item.get("wind_speed")) for item in periods)
    temperatures = [_number(item.get("temperature")) for item in periods]
    thunderstorm = any(_number(item.get("weather_code")) >= 95 for item in periods)

    reasons = []
    if rain_probability > limits["max_spray_rain_probability"] or expected_precipitation > limits["max_spray_precipitation_mm"]:
        reasons.append("High precipitation risk")
    if wind_speed > limits["max_spray_wind_kmh"]:
        reasons.append("Wind may carry spray away from the target")
    if any(temp < limits["min_spray_temperature_c"] or temp > limits["max_spray_temperature_c"] for temp in temperatures):
        reasons.append("Temperature is outside the configurable weather range")
    if thunderstorm:
        reasons.append("Thunderstorm conditions are present")

    result = {
        "suitable": not reasons,
        "reason": "; ".join(reasons) if reasons else "Low precipitation and manageable wind conditions",
        "best_window": None,
        "rain_probability": round(rain_probability, 1),
        "expected_precipitation_mm": round(expected_precipitation, 1),
        "wind_speed_kmh": round(wind_speed, 1),
        "temperature_c": round(sum(temperatures) / len(temperatures), 1),
    }
    if result["suitable"]:
        result["best_window"] = {"start": periods[0].get("time"), "end": periods[-1].get("time")}
    return result


def agriculture_advisory(
    intent: str,
    hourly: list[dict[str, Any]],
    daily: list[dict[str, Any]],
    target_date: str | None = None,
    time_reference: str | None = None,
    crop: str | None = None,
) -> dict[str, Any]:
    window = find_suitable_agriculture_window(hourly, target_date, time_reference)
    if intent == "pesticide_application":
        action = "Weather conditions appear suitable for spraying" if window["suitable"] else "I would recommend postponing pesticide spraying"
        reason = " because the forecast shows a workable dry window" if window["suitable"] else f" because {window['reason'].lower()}"
        answer = f"{action}{reason}."
        if not window["suitable"]:
            answer += " Rain soon after application can reduce effectiveness by washing product from the crop."
        answer += (
            f"\n\nBased on the available forecast:\n"
            f"Rain probability: {window.get('rain_probability', 0):g}%\n"
            f"Expected precipitation: {window.get('expected_precipitation_mm', 0):g} mm\n"
            f"Wind: {window.get('wind_speed_kmh', 0):g} km/h\n"
            f"Temperature: {window.get('temperature_c', 0):g}°C\n\n"
            f"Recommendation: Use only a sufficiently dry, manageable-wind weather window and follow the pesticide label's product-specific requirements."
        )
        if crop:
            answer += f"\n\nI have noted this is for your {crop} crop."
        answer += "\n\nIf you tell me the crop and pesticide/product you are using, I can make the weather-based recommendation more specific."
        return {"answer": answer, "window": window}

    forecast = daily[1] if len(daily) > 1 else (daily[0] if daily else {})
    if intent == "irrigation":
        answer = "I would wait before irrigating" if _number(forecast.get("precipitation_probability")) >= 50 or _number(forecast.get("precipitation_sum")) >= 2 else "Irrigation may be reasonable"
        return {"answer": f"{answer} based on the forecast. Check soil moisture in the field before deciding.", "window": window}
    return {"answer": f"Weather-based conditions for {intent.replace('_', ' ')}: {window['reason']}. Check local crop conditions before field work.", "window": window}
