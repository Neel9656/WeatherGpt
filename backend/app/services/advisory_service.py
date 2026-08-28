from typing import Any


def advisory_guidance(audience: str, daily: list[dict[str, Any]]) -> str:
    if not daily:
        return "No forecast period is available for an advisory."
    tomorrow = daily[1] if len(daily) > 1 else daily[0]
    probability = tomorrow["precipitation_probability"]
    rain = tomorrow["precipitation_sum"]
    if audience == "farmer":
        action = "Consider delaying irrigation" if probability >= 50 or rain >= 2 else "Irrigation may be reasonable"
        return f"Farmer guidance: {action} tomorrow based on the forecast. Confirm soil conditions locally."
    if audience == "traveller":
        action = "Carry rain protection and allow extra travel time" if probability >= 50 or rain >= 2 else "Travel conditions look comparatively drier"
        return f"Traveller guidance: {action} tomorrow. Check official warnings before departure."
    if audience == "urban":
        action = "Avoid low-lying roads and monitor local authority advisories" if probability >= 50 or rain >= 2 else "Normal urban travel precautions are reasonable"
        return f"Urban resident guidance: {action} tomorrow. This is weather decision support, not emergency instruction."
    return "General guidance: Monitor the forecast and follow official warnings for hazardous weather."


def advisory_for_intent(intent: str, daily: list[dict[str, Any]]) -> str:
    if not daily:
        return "No forecast period is available for an advisory."
    forecast = daily[1] if len(daily) > 1 else daily[0]
    probability = forecast.get("precipitation_probability", 0)
    rain = forecast.get("precipitation_sum", 0)
    if intent == "agriculture_advisory":
        action = "Consider delaying irrigation" if probability >= 50 or rain >= 2 else "Irrigation may be reasonable"
        return f"Agriculture advisory: {action} based on the forecast. Check soil moisture and local conditions before deciding."
    if intent == "travel_advisory":
        action = "Carry rain protection and allow extra travel time" if probability >= 50 or rain >= 2 else "Travel conditions look comparatively drier"
        return f"Travel advisory: {action}. Check the latest forecast before departure."
    if intent == "precipitation":
        return "Weather advisory: keep an eye on rain intensity and the forecast timing for the next period."
    return "General guidance: Monitor the forecast and follow official warnings for hazardous weather."