import argparse
import csv
from pathlib import Path
from typing import Any

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CSV_COLUMNS = ["location", "latitude", "longitude", "timestamp", "temperature", "humidity",
               "precipitation", "rain", "precipitation_probability", "wind_speed", "pressure",
               "cloud_cover", "weather_code"]


def collect_city(city: dict[str, Any]) -> list[dict[str, Any]]:
    response = requests.get(FORECAST_URL, params={
        "latitude": city["latitude"], "longitude": city["longitude"],
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,rain,precipitation_probability,wind_speed_10m,surface_pressure,cloud_cover,weather_code",
        "forecast_days": 1, "timezone": "auto",
    }, timeout=10)
    response.raise_for_status()
    hourly = response.json()["hourly"]
    return [{"location": city["name"], "latitude": city["latitude"], "longitude": city["longitude"],
             "timestamp": timestamp, "temperature": temperature, "humidity": humidity,
             "precipitation": precipitation, "rain": rain, "precipitation_probability": probability,
             "wind_speed": wind, "pressure": pressure, "cloud_cover": cloud, "weather_code": code}
            for timestamp, temperature, humidity, precipitation, rain, probability, wind, pressure, cloud, code in zip(
                hourly["time"], hourly["temperature_2m"], hourly["relative_humidity_2m"], hourly["precipitation"],
                hourly["rain"], hourly["precipitation_probability"], hourly["wind_speed_10m"], hourly["surface_pressure"],
                hourly["cloud_cover"], hourly["weather_code"])]


def collect(cities: list[dict[str, Any]], output_path: Path) -> None:
    existing: dict[tuple[str, str], dict[str, Any]] = {}
    if output_path.exists():
        with output_path.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                existing[(row["location"], row["timestamp"])] = row
    for city in cities:
        for row in collect_city(city):
            existing[(row["location"], row["timestamp"])] = row
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(existing.values())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect hourly Open-Meteo data for one or more cities.")
    parser.add_argument("--city", action="append", nargs=3, metavar=("NAME", "LATITUDE", "LONGITUDE"), required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "data" / "weather_data.csv")
    args = parser.parse_args()
    collect([{"name": name, "latitude": float(latitude), "longitude": float(longitude)}
             for name, latitude, longitude in args.city], args.output)