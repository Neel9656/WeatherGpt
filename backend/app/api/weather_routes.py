from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

import asyncio

from app.models.weather_models import DailyForecast, HourlyForecast, Location, WeatherResponse
from app.services.alert_service import detect_alerts, normalize_alert_inputs
from app.services.open_meteo_service import OpenMeteoError, open_meteo_service
from app.utils.weather_utils import weather_description

router = APIRouter(tags=["weather"])


def _coordinates(latitude: float, longitude: float) -> dict[str, float]:
    return {"latitude": latitude, "longitude": longitude}


@router.get("/weather", response_model=WeatherResponse)
async def current_weather(
    latitude: float = Query(..., ge=-90, le=90), longitude: float = Query(..., ge=-180, le=180)
) -> WeatherResponse:
    try:
        data = await open_meteo_service.get_current_weather(latitude, longitude)
        current = data["current"]
        return WeatherResponse(
            location=Location(
                name="Selected location", **_coordinates(latitude, longitude), timezone=data.get("timezone", "auto")
            ),
            current={
                "time": datetime.fromisoformat(current["time"]),
                "temperature": current["temperature_2m"],
                "humidity": current["relative_humidity_2m"],
                "wind_speed": current["wind_speed_10m"],
                "precipitation": current["precipitation"],
                "pressure": current["surface_pressure"],
                "cloud_cover": current["cloud_cover"],
                "weather_code": current["weather_code"],
                "description": weather_description(current["weather_code"]),
            },
        )
    except (OpenMeteoError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Unable to retrieve current weather.") from exc


@router.get("/forecast")
async def forecast(
    latitude: float = Query(..., ge=-90, le=90), longitude: float = Query(..., ge=-180, le=180),
    forecast_type: str = Query("daily", pattern="^(hourly|daily)$"),
) -> list[HourlyForecast | DailyForecast]:
    try:
        if forecast_type == "hourly":
            data = await open_meteo_service.get_hourly_forecast(latitude, longitude)
            hourly = data["hourly"]
            return [HourlyForecast(time=datetime.fromisoformat(time), temperature=temp, precipitation=rain,
                precipitation_probability=probability, wind_speed=wind, weather_code=code,
                description=weather_description(code)) for time, temp, rain, probability, wind, code in zip(
                    hourly["time"], hourly["temperature_2m"], hourly["precipitation"],
                    hourly["precipitation_probability"], hourly["wind_speed_10m"], hourly["weather_code"])]
        data = await open_meteo_service.get_daily_forecast(latitude, longitude)
        daily = data["daily"]
        return [DailyForecast(date=date, temperature_max=temp_max, temperature_min=temp_min,
            precipitation_probability=probability, precipitation_sum=rain, wind_speed_max=wind,
            weather_code=code, description=weather_description(code)) for date, temp_max, temp_min, probability,
            rain, wind, code in zip(daily["time"], daily["temperature_2m_max"], daily["temperature_2m_min"],
                daily["precipitation_probability_max"], daily["precipitation_sum"], daily["wind_speed_10m_max"],
                daily["weather_code"])]
    except (OpenMeteoError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Unable to retrieve forecast data.") from exc


@router.get("/alerts")
async def alerts(
    latitude: float = Query(..., ge=-90, le=90), longitude: float = Query(..., ge=-180, le=180),
) -> dict:
    try:
        current_data, hourly_data, daily_data = await asyncio.gather(
            open_meteo_service.get_current_weather(latitude, longitude),
            open_meteo_service.get_hourly_forecast(latitude, longitude),
            open_meteo_service.get_daily_forecast(latitude, longitude),
        )
        current, hourly, daily = normalize_alert_inputs(current_data, hourly_data, daily_data)
        detected = detect_alerts("Selected location", current, hourly, daily)
        severity_rank = {"low": 0, "moderate": 1, "high": 2, "severe": 3}
        risk_level = max((alert["severity"] for alert in detected), key=lambda value: severity_rank[value], default="low").upper()
        return {"risk_level": risk_level, "alerts": detected, "official_alerts": []}
    except (OpenMeteoError, KeyError, TypeError, ValueError, IndexError) as exc:
        raise HTTPException(status_code=502, detail="Unable to detect weather conditions.") from exc