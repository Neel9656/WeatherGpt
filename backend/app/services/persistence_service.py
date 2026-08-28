from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.database.database import SessionLocal
from app.database.models import ChatHistory, LocationRecord, WeatherForecast, WeatherObservation


def _location(session, data: dict[str, Any]) -> LocationRecord:
    record = session.scalar(select(LocationRecord).where(
        LocationRecord.latitude == data["latitude"], LocationRecord.longitude == data["longitude"]
    ))
    if record is None:
        record = LocationRecord(name=data["name"], latitude=data["latitude"], longitude=data["longitude"],
                                timezone=data.get("timezone"), country=data.get("country"))
        session.add(record)
        session.flush()
    return record


def save_weather(location: dict[str, Any], current: dict[str, Any], daily: list[dict[str, Any]]) -> None:
    if SessionLocal is None:
        return
    with SessionLocal() as session:
        record = _location(session, location)
        session.add(WeatherObservation(location_id=record.id, timestamp=current["time"],
            temperature=current["temperature"], humidity=current["humidity"], precipitation=current["precipitation"],
            wind_speed=current["wind_speed"], pressure=current["pressure"], weather_code=current["weather_code"]))
        session.add_all(WeatherForecast(location_id=record.id, forecast_date=item["date"],
            temperature_max=item["temperature_max"], temperature_min=item["temperature_min"],
            precipitation_probability=item["precipitation_probability"], precipitation_sum=item["precipitation_sum"],
            wind_speed_max=item["wind_speed_max"], weather_code=item["weather_code"]) for item in daily)
        session.commit()


def save_chat(question: str, answer: str, audience: str, location_name: str) -> None:
    if SessionLocal is None:
        return
    with SessionLocal() as session:
        session.add(ChatHistory(question=question, answer=answer, audience=audience, location_name=location_name))
        session.commit()