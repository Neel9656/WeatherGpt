from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class LocationRecord(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    timezone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    observations: Mapped[list["WeatherObservation"]] = relationship(back_populates="location")
    forecasts: Mapped[list["WeatherForecast"]] = relationship(back_populates="location")


class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    temperature: Mapped[float] = mapped_column(Float)
    humidity: Mapped[float] = mapped_column(Float)
    precipitation: Mapped[float] = mapped_column(Float)
    wind_speed: Mapped[float] = mapped_column(Float)
    pressure: Mapped[float] = mapped_column(Float)
    weather_code: Mapped[int] = mapped_column(Integer)
    location: Mapped[LocationRecord] = relationship(back_populates="observations")


class WeatherForecast(Base):
    __tablename__ = "weather_forecasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    forecast_date: Mapped[str] = mapped_column(String(20), index=True)
    temperature_max: Mapped[float] = mapped_column(Float)
    temperature_min: Mapped[float] = mapped_column(Float)
    precipitation_probability: Mapped[float] = mapped_column(Float)
    precipitation_sum: Mapped[float] = mapped_column(Float)
    wind_speed_max: Mapped[float] = mapped_column(Float)
    weather_code: Mapped[int] = mapped_column(Integer)
    location: Mapped[LocationRecord] = relationship(back_populates="forecasts")


class AlertRecord(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    type: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    audience: Mapped[str] = mapped_column(String(30))
    location_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)