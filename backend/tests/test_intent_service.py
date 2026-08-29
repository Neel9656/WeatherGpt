from app.services.intent_service import _extract_location, detect_intent


def test_extract_natural_language_locations() -> None:
    examples = {
        "Will it be a good thing to spray pesticides in my farm in Kolkata": "Kolkata",
        "Can I spray pesticides on my rice farm near Bhubaneswar?": "Bhubaneswar",
        "I am farming in Kolkata": "Kolkata",
        "My farm is in Kolkata.": "Kolkata",
        "Should I irrigate my wheat field in Ranchi tomorrow?": "Ranchi",
    }
    for message, expected in examples.items():
        assert _extract_location(message) == expected


def test_detect_agriculture_intent_for_irrigation_question() -> None:
    intent = detect_intent("Should I irrigate my wheat field tomorrow?")
    assert intent.domain == "agriculture"
    assert intent.intent == "irrigation"
    assert intent.date_reference == "tomorrow"
    assert intent.requires_advisory is True
    assert intent.requires_forecast is True


def test_detect_pesticide_application_and_explicit_location() -> None:
    intent = detect_intent("Can I use pesticides in my farm tomorrow if I am in Kolkata?")
    assert intent.domain == "agriculture"
    assert intent.intent == "pesticide_application"
    assert intent.location == "Kolkata"
    assert intent.date_reference == "tomorrow"


def test_detect_agriculture_follow_up_context() -> None:
    intent = detect_intent("What about the evening?", ["Can I spray pesticides tomorrow in Kolkata?"])
    assert intent.domain == "agriculture"
    assert intent.intent == "pesticide_application"
    assert intent.location == "Kolkata"
    assert intent.time_reference == "evening"


def test_extract_crop_context() -> None:
    intent = detect_intent("My crop is rice.")
    assert intent.domain == "agriculture"
    assert intent.crop == "rice"


def test_weekday_follow_up_preserves_agriculture_context() -> None:
    intent = detect_intent("What about Friday?", ["Can I spray pesticides tomorrow in Kolkata?"])
    assert intent.domain == "agriculture"
    assert intent.intent == "pesticide_application"
    assert intent.location == "Kolkata"
    assert intent.date_reference == "friday"


def test_detect_travel_intent_for_umbrella_question() -> None:
    intent = detect_intent("I'm travelling tomorrow evening. Should I carry an umbrella?")
    assert intent.domain == "travel"
    assert intent.intent == "travel_advisory"
    assert intent.time_reference == "evening"
    assert intent.requires_advisory is True


def test_detect_current_weather_intent() -> None:
    intent = detect_intent("What's the weather like right now?")
    assert intent.intent == "current_weather"
    assert intent.requires_current_weather is True
    assert intent.requires_forecast is False


def test_detect_forecast_precipitation_intent() -> None:
    intent = detect_intent("Will it rain tomorrow evening in Bhubaneswar?")
    assert intent.intent == "precipitation"
    assert intent.date_reference == "tomorrow"
    assert intent.time_reference == "evening"
    assert intent.requires_forecast is True


def test_multilingual_time_words_are_not_locations() -> None:
    assert _extract_location("KAL KA MAUSAM KAISA HOGA?") is None
    assert detect_intent("KAL KA MAUSAM KAISA HOGA?").date_reference == "tomorrow"
    assert detect_intent("Kal barish hogi kya?").intent == "rain_tomorrow"
    assert detect_intent("कल बारिश होगी क्या?").date_reference == "tomorrow"
    assert detect_intent("ଆସନ୍ତାକାଲି ବର୍ଷା ହେବ କି?").date_reference == "tomorrow"
    assert detect_intent("আগামীকাল বৃষ্টি হবে কি?").date_reference == "tomorrow"


def test_bengali_weather_question_is_not_treated_as_location() -> None:
    message = "কালকে কেমন বৃষ্টি হবে?"
    assert _extract_location(message) is None
    intent = detect_intent(message)
    assert intent.intent in {"precipitation", "general_weather", "rain_tomorrow", "forecast_tomorrow"}
    assert intent.location is None
    assert intent.date_reference == "tomorrow"


def test_explicit_city_and_time_are_extracted_without_partial_matches() -> None:
    ranchi_today = detect_intent("What will be the weather of Ranchi today?")
    ranchi_tomorrow = detect_intent("What will be the weather of Ranchi tomorrow?")
    assert ranchi_today.location == "Ranchi"
    assert ranchi_today.date_reference == "today"
    assert ranchi_tomorrow.location == "Ranchi"
    assert ranchi_tomorrow.date_reference == "tomorrow"
    assert _extract_location("कल Ranchi में बारिश होगी क्या?") == "Ranchi"
    assert _extract_location("আগামীকাল কলকাতায় বৃষ্টি হবে?") == "Kolkata"
