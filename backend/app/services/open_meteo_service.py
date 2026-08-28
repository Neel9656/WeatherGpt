import asyncio
import time
from typing import Any

import httpx

from app.config import settings


class OpenMeteoError(RuntimeError):
    """Raised when Open-Meteo cannot provide a valid response."""


class OpenMeteoService:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client

        # Cache responses for 5 minutes.
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._cache_ttl = 300

        # Only one Open-Meteo request at a time.
        self._request_lock = asyncio.Lock()
        self._last_request_time = 0.0
        self._minimum_request_interval = 2.0

    def _cache_key(
        self,
        url: str,
        params: dict[str, Any],
    ) -> str:
        return f"{url}?{tuple(sorted(params.items()))}"

    async def _get(
        self,
        url: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:

        cache_key = self._cache_key(url, params)

        # First cache check.
        now = time.monotonic()
        cached = self._cache.get(cache_key)

        if cached:
            cached_time, cached_data = cached

            if now - cached_time < self._cache_ttl:
                return cached_data

        async with self._request_lock:

            # IMPORTANT:
            # Check cache AGAIN after acquiring the lock.
            # Another request may have already fetched the same data
            # while this request was waiting.
            now = time.monotonic()
            cached = self._cache.get(cache_key)

            if cached:
                cached_time, cached_data = cached

                if now - cached_time < self._cache_ttl:
                    return cached_data

            elapsed = (
                time.monotonic() - self._last_request_time
            )

            if elapsed < self._minimum_request_interval:
                await asyncio.sleep(
                    self._minimum_request_interval - elapsed
                )

            self._last_request_time = time.monotonic()

            for attempt in range(3):
                try:
                    if self.client:
                        response = await self.client.get(url, params=params)
                    else:
                        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, follow_redirects=True) as client:
                            response = await client.get(url, params=params)

                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt == 2:
                            raise OpenMeteoError(f"Open-Meteo returned HTTP {response.status_code}.")
                        retry_after = response.headers.get("Retry-After")
                        try:
                            delay = min(float(retry_after), 8.0) if retry_after else 0.5 * (2 ** attempt)
                        except ValueError:
                            delay = 0.5 * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue

                    response.raise_for_status()
                    data = response.json()
                    if not isinstance(data, dict):
                        raise OpenMeteoError("Unexpected Open-Meteo response.")
                    self._cache[cache_key] = (time.monotonic(), data)
                    return data
                except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                    if attempt == 2:
                        raise OpenMeteoError("Open-Meteo network request failed after retries.") from exc
                    await asyncio.sleep(0.5 * (2 ** attempt))
                except OpenMeteoError:
                    raise
                except (httpx.HTTPError, ValueError) as exc:
                    raise OpenMeteoError("Open-Meteo returned an invalid response.") from exc

            raise OpenMeteoError("Open-Meteo request failed after retries.")

    async def _get_weather_bundle(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:

        params = {
            "latitude": latitude,
            "longitude": longitude,

            "current": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "precipitation,"
                "wind_speed_10m,"
                "surface_pressure,"
                "cloud_cover,"
                "weather_code"
            ),

            "hourly": (
                "temperature_2m,"
                "precipitation,"
                "precipitation_probability,"
                "wind_speed_10m,"
                "weather_code"
            ),

            "daily": (
                "temperature_2m_max,"
                "temperature_2m_min,"
                "precipitation_probability_max,"
                "precipitation_sum,"
                "wind_speed_10m_max,"
                "weather_code"
            ),

            "forecast_days": 7,
            "timezone": "auto",
        }

        return await self._get(
            settings.open_meteo_forecast_url,
            params,
        )

    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:

        return await self._get_weather_bundle(
            latitude,
            longitude,
        )

    async def get_hourly_forecast(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:

        return await self._get_weather_bundle(
            latitude,
            longitude,
        )

    async def get_daily_forecast(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:

        return await self._get_weather_bundle(
            latitude,
            longitude,
        )

    async def get_weather_overview(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:
        return await self._get_weather_bundle(latitude, longitude)


open_meteo_service = OpenMeteoService()