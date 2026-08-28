import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.schemas.weather_schema import ChatRequest
from app.services.advisory_service import advisory_guidance
from app.services.agriculture_advisory_service import agriculture_advisory
from app.services.intent_service import WeatherIntent, detect_intent, extract_location_candidates
from app.services.llm_service import LLMError, llm_service
from app.services.location_service import canonical_location, resolve_display_location, resolve_location_candidates, search_locations
from app.services.open_meteo_service import OpenMeteoError, open_meteo_service
from app.services.persistence_service import save_chat
from app.services.translation_service import grounded_weather_answer
from app.services.weather_risk_service import detect_weather_risks
from app.utils.weather_utils import weather_description

router = APIRouter(tags=["chat"])
MAX_LLM_HISTORY = 8
logger = logging.getLogger(__name__)


def build_daily_context(data: dict[str, Any]) -> list[dict[str, Any]]:
    daily = data.get("daily", {})
    keys = ("time", "temperature_2m_max", "temperature_2m_min", "precipitation_probability_max", "precipitation_sum", "wind_speed_10m_max", "weather_code")
    if not all(key in daily for key in keys):
        return []
    return [{"date": date, "temperature_max": high, "temperature_min": low, "precipitation_probability": probability, "precipitation_sum": rain, "wind_speed_max": wind, "description": weather_description(code)} for date, high, low, probability, rain, wind, code in zip(*(daily[key] for key in keys))]


def build_hourly_context(data: dict[str, Any]) -> list[dict[str, Any]]:
    hourly = data.get("hourly", {})
    keys = ("time", "temperature_2m", "precipitation", "precipitation_probability", "wind_speed_10m", "weather_code")
    if not all(key in hourly for key in keys):
        return []
    return [{"time": time, "temperature": temperature, "precipitation": rain, "precipitation_probability": probability, "wind_speed": wind, "weather_code": code} for time, temperature, rain, probability, wind, code in zip(*(hourly[key] for key in keys))]


def target_date(reference: str | None, current_data: dict[str, Any]) -> str | None:
    offsets = {"today": 0, "tomorrow": 1, "day_after_tomorrow": 2}
    if reference not in offsets:
        return None
    try:
        current_time = current_data["current"].get("time")
        if not current_time:
            return None
        current_date = datetime.fromisoformat(str(current_time).replace("Z", "+00:00")).date()
    except (KeyError, TypeError, ValueError):
        current_date = datetime.now().date()
    return (current_date + timedelta(days=offsets[reference])).isoformat()


def select_forecast(daily: list[dict[str, Any]], reference: str | None, current_data: dict[str, Any]) -> dict[str, Any] | None:
    if not daily:
        return None
    date = target_date(reference, current_data)
    return next((item for item in daily if item["date"] == date), None) if date else daily[0]


def _name(value: Any) -> str | None:
    return value.name if hasattr(value, "name") else value


async def resolve_location(request: ChatRequest, parsed: WeatherIntent) -> dict[str, Any]:
    selected = request.selected_location
    candidates = extract_location_candidates(request.message, parsed.language)
    query = parsed.location or _name(selected)
    if not parsed.location and request.latitude is not None and (not selected or str(_name(selected)).casefold() in {"current location", "your location", "selected location", "unknown location"}):
        return await resolve_display_location(request.latitude, request.longitude, _name(selected))
    if not parsed.location and hasattr(selected, "latitude"):
        if selected.name.casefold() in {"current location", "your location", "selected location", "unknown location"}:
            return await resolve_display_location(selected.latitude, selected.longitude, selected.name)
        return {"name": selected.name, "displayName": selected.name, "latitude": selected.latitude, "longitude": selected.longitude, "country": None, "timezone": selected.timezone, "location_type": "dashboard", "type": "city", "source": "selected"}
    if not query and request.latitude is not None:
        return await resolve_display_location(request.latitude, request.longitude)
    if not query:
        raise HTTPException(status_code=400, detail="Please select a location or mention a location in your question.")
    if candidates:
        try:
            return await resolve_location_candidates(candidates, searcher=search_locations)
        except OpenMeteoError as exc:
            raise HTTPException(status_code=404, detail=f"I couldn't identify '{candidates[0]}' as a location. Please provide the city, district, state or country name again.") from exc
    locations = await search_locations(str(query))
    if not locations:
        raise HTTPException(status_code=404, detail=f"I couldn't identify '{query}' as a location. Please provide the city, district, state or country name again.")
    return canonical_location(locations[0], "selected")


def current_context(data: dict[str, Any]) -> dict[str, Any]:
    current = data.get("current", {})
    return {"time": current.get("time"), "temperature": current.get("temperature_2m"), "humidity": current.get("relative_humidity_2m"), "wind_speed": current.get("wind_speed_10m"), "precipitation": current.get("precipitation"), "pressure": current.get("surface_pressure"), "weather_code": current.get("weather_code"), "description": weather_description(current.get("weather_code"))}


def fallback_intent(parsed: WeatherIntent) -> str:
    return {"precipitation": "rain_today", "rain_tomorrow": "rain_tomorrow", "rain_today": "rain_today", "forecast_tomorrow": "forecast_tomorrow", "current_weather": "current_weather", "umbrella_advice": "umbrella_advice", "travel_advisory": "travel_advisory", "flood_risk": "flood_risk"}.get(parsed.intent, parsed.intent)


def question_weather_context(location: dict[str, Any], current: dict[str, Any], forecast: dict[str, Any] | None, time_period: str | None) -> str:
    lines = [
        f"RESOLVED LOCATION: {location['name']}",
        f"REQUESTED TIME PERIOD: {time_period or 'current'}",
        f"CURRENT WEATHER: {current.get('description')} at {current.get('temperature')} C; humidity {current.get('humidity')}%; wind {current.get('wind_speed')} km/h",
    ]
    if forecast:
        lines.extend([
            "AUTHORITATIVE FORECAST FOR REQUESTED DATE:",
            f"Date: {forecast.get('date')}",
            f"Description: {forecast.get('description')}",
            f"Temperature max: {forecast.get('temperature_max')} C",
            f"Temperature min: {forecast.get('temperature_min')} C",
            f"Rain probability: {forecast.get('precipitation_probability')}%",
            f"Expected precipitation: {forecast.get('precipitation_sum')} mm",
            f"Wind: {forecast.get('wind_speed_max')} km/h",
        ])
    return "\n".join(lines)


@router.post("/chat")
async def chat(request: ChatRequest) -> dict[str, Any]:
    try:
        history = [item.content for item in request.conversation_history[-MAX_LLM_HISTORY:]]
        parsed = detect_intent(request.message, history)
        selected = await resolve_location(request, parsed)
        latitude, longitude = selected["latitude"], selected["longitude"]
        logger.debug("WeatherGPT chat message=%r extracted_location=%r resolved_location=%r coordinates=(%s, %s) time=%r intent=%r", request.message, parsed.location, selected.get("name"), latitude, longitude, parsed.date_reference, parsed.intent)
        current_data, daily_data = await asyncio.gather(open_meteo_service.get_current_weather(latitude, longitude), open_meteo_service.get_daily_forecast(latitude, longitude))
        current = current_context(current_data)
        daily = build_daily_context(daily_data)
        location = {"name": selected.get("name", "Selected location"), "displayName": selected.get("displayName", selected.get("name", "Selected location")), "admin1": selected.get("admin1", selected.get("state")), "state": selected.get("state", selected.get("admin1")), "country": selected.get("country"), "timezone": current_data.get("timezone", selected.get("timezone", "auto")), "latitude": latitude, "longitude": longitude, "location_type": selected.get("location_type", selected.get("type", "city")), "type": selected.get("type", selected.get("location_type", "city")), "source": selected.get("source", "selected"), "representative_location": selected.get("representative_location")}

        agriculture_result = None
        if parsed.domain == "agriculture":
            hourly = build_hourly_context(await open_meteo_service.get_hourly_forecast(latitude, longitude))
            agriculture_result = agriculture_advisory(parsed.intent, hourly, daily, target_date(parsed.date_reference, current_data), parsed.time_reference, parsed.crop)

        selected_forecast = select_forecast(daily, parsed.date_reference, current_data)
        context = question_weather_context(location, current, selected_forecast, parsed.date_reference)
        language = request.language or parsed.language or "en"
        answer = ""
        llm_available = False
        if settings.llm_api_key and settings.llm_provider:
            try:
                if request.conversation_history:
                    answer = await llm_service.generate_weather_response(request.message, context, language, [{"role": item.role, "content": item.content} for item in request.conversation_history[-MAX_LLM_HISTORY:]])
                else:
                    answer = await llm_service.generate_weather_response(request.message, context, language)
                llm_available = True
            except (LLMError, TypeError):
                answer = ""
        if not answer:
            answer = agriculture_result["answer"] if agriculture_result else grounded_weather_answer(language, location["name"], request.message, current, daily, fallback_intent(parsed), selected_forecast, parsed.date_reference)
        elif agriculture_result:
            answer += f"\n\n{agriculture_result['answer']}"
        if location["location_type"] == "region":
            answer = f"Regional forecast: {answer} Conditions can vary across {location['name']}; this uses the {location.get('representative_location', 'representative')} area."
        if request.audience != "general":
            answer += f"\n\n{advisory_guidance(request.audience, daily)}"

        risks = [{**risk, "title": risk["type"].replace("_", " ").title(), "official": False, "source": "Forecast-based advisory"} for risk in detect_weather_risks(daily)]
        result = {"success": True, "answer": answer, "language": language, "llm_available": llm_available, "location": location, "resolved_location": location, "intent": parsed.model_dump(), "time_period": parsed.date_reference, "weather": {"current": current, "forecast": daily, "selected_forecast": selected_forecast}, "forecast": selected_forecast, "selected_forecast": selected_forecast, "weather_context": context, "daily_forecast": selected_forecast, "alerts": risks, "risks": risks, "source": "Open-Meteo forecast data", "agriculture_advisory": agriculture_result}
        try:
            save_chat(request.message, answer, request.audience, location["name"])
        except Exception:
            pass
        return result
    except HTTPException:
        raise
    except (OpenMeteoError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Weather data is temporarily unavailable. Please try again shortly.") from exc