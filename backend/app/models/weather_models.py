from datetime import datetime

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class CurrentWeather(BaseModel):
    time: datetime
    temperature: float
    humidity: float
    wind_speed: float
    precipitation: float
    pressure: float
    cloud_cover: float
    weather_code: int
    description: str


class Location(BaseModel):
    name: str
    latitude: float
    longitude: float
    timezone: str
    country: str | None = None


class WeatherResponse(BaseModel):
    location: Location
    current: CurrentWeather


class HourlyForecast(BaseModel):
    time: datetime
    temperature: float
    precipitation: float
    precipitation_probability: float
    wind_speed: float
    weather_code: int
    description: str


class DailyForecast(BaseModel):
    date: str
    temperature_max: float
    temperature_min: float
    precipitation_probability: float
    precipitation_sum: float
    wind_speed_max: float
    weather_code: int
    description: str