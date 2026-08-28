import pytest

from app.services.location_service import search_locations


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