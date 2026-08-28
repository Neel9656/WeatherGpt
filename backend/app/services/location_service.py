from typing import Any

import httpx

from app.config import settings
from app.services.open_meteo_service import (
    OpenMeteoError,
    OpenMeteoService,
)


INDIAN_REGION_ALIASES = {
    "mp": "madhya pradesh",
    "m.p.": "madhya pradesh",
    "orissa": "odisha",
    "wb": "west bengal",
    "w.b.": "west bengal",
}


def normalize_location_query(query: str) -> str:
    return " ".join(query.strip().casefold().split())


async def _search_nominatim(query: str) -> list[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, headers={"User-Agent": "WeatherGPT/1.0"}) as client:
            response = await client.get("https://nominatim.openstreetmap.org/search", params={"q": query, "format": "jsonv2", "limit": 10, "addressdetails": 1})
            response.raise_for_status()
            results = response.json()
        normalized = []
        for item in results if isinstance(results, list) else []:
            address = item.get("address", {})
            name = address.get("city") or address.get("town") or address.get("state") or item.get("display_name", "").split(",")[0]
            normalized.append({"name": name, "display_name": item.get("display_name"), "latitude": float(item["lat"]), "longitude": float(item["lon"]), "country": address.get("country"), "admin1": address.get("state"), "country_code": address.get("country_code"), "feature_code": "ADM" if item.get("type") in {"administrative", "state", "county", "region"} else "PPL"})
        return normalized
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return []


async def resolve_display_location(latitude: float, longitude: float, fallback_name: str | None = None) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, headers={"User-Agent": "WeatherGPT/1.0"}) as client:
            response = await client.get("https://nominatim.openstreetmap.org/reverse", params={"lat": latitude, "lon": longitude, "format": "jsonv2", "zoom": 10})
            response.raise_for_status()
            address = response.json().get("address", {})
        name = address.get("city") or address.get("town") or address.get("village") or address.get("state")
        if name:
            name = name.removesuffix(" Municipal Corporation").strip()
        if name:
            return {"name": name, "displayName": ", ".join(part for part in (name, address.get("state"), address.get("country")) if part), "admin1": address.get("state"), "state": address.get("state"), "country": address.get("country"), "latitude": latitude, "longitude": longitude, "location_type": "region" if address.get("state") == name else "city", "type": "region" if address.get("state") == name else "city", "source": "gps"}
    except (httpx.HTTPError, ValueError, TypeError):
        pass
    name = fallback_name or "Current location"
    return {"name": name, "displayName": name, "admin1": None, "country": None, "latitude": latitude, "longitude": longitude, "location_type": "device", "type": "device", "source": "gps"}


async def search_locations(
    query: str,
    service: OpenMeteoService | None = None
) -> list[dict[str, Any]]:

    normalized_query = query.strip()

    if not normalized_query:
        raise ValueError(
            "Location query cannot be empty."
        )

    normalized_key = normalize_location_query(
        normalized_query
    )
    normalized_key = INDIAN_REGION_ALIASES.get(normalized_key, normalized_key)

    weather_service = service or OpenMeteoService()

    queries = [normalized_query]
    if normalized_key in INDIAN_REGION_ALIASES:
        queries.insert(0, INDIAN_REGION_ALIASES[normalized_key])
    explicit_country = any(country in normalized_key for country in ("india", "uk", "united kingdom", "usa", "united states", "japan"))
    if "," not in normalized_query and not explicit_country:
        queries.append(f"{normalized_query}, India")

    results = []
    for candidate in queries:
        try:
            data = await weather_service._get(settings.open_meteo_geocoding_url, {"name": candidate, "count": 10, "language": "en", "format": "json"})
            results = data.get("results", [])
        except OpenMeteoError:
            results = []
        if results:
            break
    if not results:
        results = await _search_nominatim(normalized_query)

    if not isinstance(results, list):
        raise OpenMeteoError(
            "Geocoding returned an unexpected response."
        )

    return sorted(
        results,
        key=lambda item: (
            0 if normalize_location_query(str(item.get("name", ""))) == normalized_key else 1,
            0 if item.get("feature_code", "").startswith(("PPL", "ADM")) else 1,
        ),
    )


def canonical_location(result: dict[str, Any], source: str) -> dict[str, Any]:
    location_type = result.get("feature_code", "")
    is_region = result.get("admin1") and not location_type.startswith("PPL")
    name = result.get("name") or result.get("admin2") or result.get("admin1") or result.get("country")
    country = result.get("country")
    state = result.get("admin1")
    display_parts = [part for part in (name, state, country) if part and part != name]
    return {
        "name": name,
        "displayName": ", ".join([name, *display_parts]),
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "country": country,
        "state": state,
        "admin1": state,
        "type": "region" if is_region else "city",
        "location_type": "region" if is_region else "city",
        "source": source,
        "timezone": result.get("timezone"),
    }


async def resolve_location(location_text: str, service: OpenMeteoService | None = None) -> dict[str, Any]:
    results = await search_locations(location_text, service)
    if not results:
        raise OpenMeteoError(f"No location found for '{location_text}'.")
    return canonical_location(results[0], "explicit_query")


async def resolve_location_candidates(candidates: list[str], context: dict[str, Any] | None = None, service: OpenMeteoService | None = None, searcher=None) -> dict[str, Any]:
    """Resolve clean candidates in order, never sending the full user message."""
    for candidate in candidates:
        try:
            results = await (searcher(candidate) if searcher else search_locations(candidate, service))
            if results:
                return canonical_location(results[0], "explicit")
        except OpenMeteoError:
            continue
    raise OpenMeteoError(f"No location found for '{candidates[0] if candidates else 'unknown location'}'.")