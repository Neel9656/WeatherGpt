import httpx
import pytest

from app.services.location_service import search_locations
from app.services.open_meteo_service import OpenMeteoService


class FakeLocationService:
    async def _get(self, url: str, params: dict) -> dict:
        return {"results": [{"name": params["name"], "latitude": 20.3, "longitude": 85.8}]}


@pytest.mark.asyncio
async def test_search_locations_returns_geocoding_results() -> None:
    result = await search_locations(" Bhubaneswar ", FakeLocationService())
    assert result[0]["name"] == "Bhubaneswar"


@pytest.mark.asyncio
async def test_search_locations_rejects_empty_query() -> None:
    with pytest.raises(ValueError):
        await search_locations("   ", FakeLocationService())


@pytest.mark.asyncio
async def test_open_meteo_retries_rate_limit_then_succeeds(monkeypatch) -> None:
    class FakeClient:
        def __init__(self):
            self.calls = 0

        async def get(self, url, params):
            self.calls += 1
            response = httpx.Response(429, headers={"Retry-After": "0"}) if self.calls == 1 else httpx.Response(200, json={"current": {}})
            response.request = httpx.Request("GET", url)
            return response

    client = FakeClient()
    service = OpenMeteoService(client=client)
    monkeypatch.setattr("app.services.open_meteo_service.asyncio.sleep", lambda delay: _completed_sleep())
    result = await service._get("https://api.open-meteo.com/v1/forecast", {"latitude": 1, "longitude": 2})
    assert result == {"current": {}}
    assert client.calls == 2


async def _completed_sleep():
    return None