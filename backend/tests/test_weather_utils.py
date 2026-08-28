from app.utils.weather_utils import weather_description


def test_weather_description_uses_wmo_code() -> None:
    assert weather_description(61) == "Slight rain"
    assert weather_description(999) == "Unknown weather condition"