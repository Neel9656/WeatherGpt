from app.services.translation_service import grounded_weather_answer
from app.services.intent_service import _extract_location, detect_intent


CURRENT = {"temperature": 30, "humidity": 70, "wind_speed": 12, "description": "Clear sky"}
DAILY = [
    {"date": "2026-08-27", "description": "Light rain", "temperature_max": 31, "temperature_min": 25, "precipitation_probability": 40, "precipitation_sum": 3, "wind_speed_max": 20},
    {"date": "2026-08-28", "description": "Clear sky", "temperature_max": 34, "temperature_min": 26, "precipitation_probability": 10, "precipitation_sum": 0, "wind_speed_max": 18},
    {"date": "2026-08-29", "description": "Thunderstorm", "temperature_max": 29, "temperature_min": 24, "precipitation_probability": 90, "precipitation_sum": 18, "wind_speed_max": 30},
]


def test_distinct_queries_produce_distinct_grounded_answers() -> None:
    queries = [
        ("What is the weather right now?", "current_weather"),
        ("Will it rain today?", "rain_today"),
        ("What about tomorrow?", "forecast_tomorrow"),
        ("Should I carry an umbrella today?", "umbrella_advice"),
        ("Should I plan travel around the weather this week?", "travel_advisory"),
        ("Is there any flood risk?", "flood_risk"),
        ("Kya kal baarish hogi?", "rain_tomorrow"),
    ]
    answers = [grounded_weather_answer("en", "Bhubaneswar", question, CURRENT, DAILY, detect_intent(question).intent) for question, _ in queries]
    assert len(set(answers)) == len(answers)
    assert "tomorrow" in answers[2].lower()
    assert "umbrella" in answers[3].lower()


def test_hinglish_tomorrow_and_colloquial_location_are_detected() -> None:
    assert detect_intent("KYA KAL BAARISH HOGI").intent == "rain_tomorrow"
    assert _extract_location("KOLKATA KA WEATHER KAISA HAI") == "KOLKATA"
