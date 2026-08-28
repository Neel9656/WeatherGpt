from fastapi import APIRouter, HTTPException, Query

from app.services.location_service import resolve_display_location, search_locations
from app.services.open_meteo_service import OpenMeteoError

router = APIRouter(tags=["locations"])


@router.get("/location")
async def location(query: str = Query(..., min_length=1, max_length=100)) -> list[dict]:
    try:
        return await search_locations(query)
    except (OpenMeteoError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Unable to search for that location.") from exc


@router.get("/location/reverse")
async def reverse_location(latitude: float, longitude: float) -> dict:
    return await resolve_display_location(latitude, longitude)