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

        # Cache API responses to avoid repeated requests.
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._cache_ttl = 60  # seconds

        # Prevent many Open-Meteo requests from firing simultaneously.
        self._request_lock = asyncio.Lock()
        self._last_request_time = 0.0
        self._minimum_request_interval = 1.0  # seconds

    def _cache_key(self, url: str, params: dict[str, Any]) -> str:
        return f"{url}?{tuple(sorted(params.items()))}"

    async def _get(
        self,
        url: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        cache_key = self._cache_key(url, params)
        now = time.monotonic()

        # Return cached data if it is still fresh.
        cached = self._cache.get(cache_key)
        if cached:
            cached_time, cached_data = cached

            if now - cached_time < self._cache_ttl:
                return cached_data

        last_error: Exception | None = None

        for attempt in range(3):
            try:
                # Space requests apart so simultaneous frontend calls
                # do not hit Open-Meteo at the same instant.
                async with self._request_lock:
                    elapsed = (
                        time.monotonic() - self._last_request_time
                    )

                    if elapsed < self._minimum_request_interval:
                        await asyncio.sleep(
                            self._minimum_request_interval - elapsed
                        )

                    self._last_request_time = time.monotonic()

                    if self.client:
                        response = await self.client.get(
                            url,
                            params=params,
                        )
                    else:
                        async with httpx.AsyncClient(
                            timeout=settings.request_timeout_seconds,
                            follow_redirects=True,
                        ) as client:
                            response = await client.get(
                                url,
                                params=params,
                            )

                # Handle rate limiting separately.
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")

                    if retry_after and retry_after.isdigit():
                        wait_time = min(float(retry_after), 10.0)
                    else:
                        wait_time = 2.0 * (attempt + 1)

                    print(
                        f"OPEN_METEO_RATE_LIMITED attempt={attempt + 1}. "
                        f"Waiting {wait_time} seconds.",
                        flush=True,
                    )

                    last_error = OpenMeteoError(
                        "Open-Meteo rate limit reached."
                    )

                    if attempt < 2:
                        await asyncio.sleep(wait_time)
                        continue

                    raise last_error

                response.raise_for_status()

                data = response.json()

                if not isinstance(data, dict):
                    raise OpenMeteoError(
                        f"Unexpected Open-Meteo response type: {type(data)}"
                    )

                # Save successful response in cache.
                self._cache[cache_key] = (
                    time.monotonic(),
                    data,
                )

                return data

            except Exception as exc:
                last_error = exc

                print(
                    f"OPEN_METEO_ERROR attempt={attempt + 1}: "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )

                if attempt < 2:
                    await asyncio.sleep(2.0 * (attempt + 1))

        raise OpenMeteoError(
            f"Open-Meteo request failed: "
            f"{type(last_error).__name__}: {last_error}"
        ) from last_error

    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": ",".join([
                "temperature_2m",
                "relative_humidity_2m",
                "precipitation",
                "wind_speed_10m",
                "surface_pressure",
                "cloud_cover",
                "weather_code",
            ]),
            "timezone": "auto",
        }

        return await self._get(
            settings.open_meteo_forecast_url,
            params,
        )

    async def get_hourly_forecast(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": (
                "temperature_2m,"
                "precipitation,"
                "precipitation_probability,"
                "wind_speed_10m,"
                "weather_code"
            ),
            "forecast_days": 2,
            "timezone": "auto",
        }

        return await self._get(
            settings.open_meteo_forecast_url,
            params,
        )

    async def get_daily_forecast(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
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


open_meteo_service = OpenMeteoService()