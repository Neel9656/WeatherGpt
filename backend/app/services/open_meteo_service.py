import asyncio
from typing import Any

import httpx

from app.config import settings


class OpenMeteoError(RuntimeError):
    """Raised when Open-Meteo cannot provide a valid response."""


class OpenMeteoService:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client

    async def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                if self.client:
                    response = await self.client.get(url, params=params)
                else:
                    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                        response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise OpenMeteoError("Open-Meteo returned an unexpected response.")
                return data
            except (httpx.HTTPError, ValueError, OpenMeteoError) as exc:
                last_error = exc
                if attempt == 0:
                    await asyncio.sleep(0.25)
        raise OpenMeteoError("Open-Meteo is unavailable or returned invalid data.") from last_error

    async def get_current_weather(self, latitude: float, longitude: float) -> dict[str, Any]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": ",".join([
                "temperature_2m", "relative_humidity_2m", "precipitation",
                "wind_speed_10m", "surface_pressure", "cloud_cover", "weather_code",
            ]),
            "timezone": "auto",
        }
        return await self._get(settings.open_meteo_forecast_url, params)

    async def get_hourly_forecast(self, latitude: float, longitude: float) -> dict[str, Any]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,precipitation,precipitation_probability,wind_speed_10m,weather_code",
            "forecast_days": 2,
            "timezone": "auto",
        }
        return await self._get(settings.open_meteo_forecast_url, params)

    async def get_daily_forecast(self, latitude: float, longitude: float) -> dict[str, Any]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,wind_speed_10m_max,weather_code",
            "forecast_days": 7,
            "timezone": "auto",
        }
        return await self._get(settings.open_meteo_forecast_url, params)


open_meteo_service = OpenMeteoService()