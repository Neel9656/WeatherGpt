from typing import Any

SUPPORTED_LANGUAGES = {"en": "English", "hi": "Hindi", "bn": "Bengali", "or": "Odia", "te": "Telugu", "ta": "Tamil"}

TRANSLATIONS = {
    "hi": {
        "fallback": "AI प्रदाता अस्थायी रूप से उपलब्ध नहीं है। यह उत्तर केवल सत्यापित मौसम डेटा पर आधारित है:",
        "current": "वर्तमान अवलोकन",
        "humidity": "नमी",
        "wind": "हवा",
        "precipitation": "वर्षा",
        "forecast": "दैनिक पूर्वानुमान",
        "rain_probability": "वर्षा की संभावना",
        "advisory": "यह AI-जनित सलाह है। आधिकारिक चेतावनियों को प्राथमिकता दें।",
    },
    "bn": {
        "fallback": "AI প্রদানকারী সাময়িকভাবে অনুপলব্ধ। এই উত্তরটি শুধুমাত্র যাচাইকৃত আবহাওয়ার তথ্যের উপর ভিত্তি করে:",
        "current": "বর্তমান পর্যবেক্ষণ",
        "humidity": "আর্দ্রতা",
        "wind": "বাতাস",
        "precipitation": "বৃষ্টিপাত",
        "forecast": "দৈনিক পূর্বাভাস",
        "rain_probability": "বৃষ্টির সম্ভাবনা",
        "advisory": "এটি AI-উৎপাদিত পরামর্শ। সরকারি সতর্কতাকে অগ্রাধিকার দিন।",
    },
    "or": {"fallback": "AI ସେବା ବର୍ତ୍ତମାନ ଉପଲବ୍ଧ ନାହିଁ। ଏହି ଉତ୍ତର ଯାଞ୍ଚିତ ପାଣିପାଗ ତଥ୍ୟ ଉପରେ ଆଧାରିତ:", "advisory": "ଏହା WeatherGPT ର ପାଣିପାଗ ନିଷ୍ପତ୍ତି ସହାୟତା। ସରକାରୀ ସତର୍କତାକୁ ପ୍ରାଥମିକତା ଦିଅନ୍ତୁ।"},
    "te": {"fallback": "AI సేవ ప్రస్తుతం అందుబాటులో లేదు. ఈ సమాధానం ధృవీకరించిన వాతావరణ సమాచారం ఆధారంగా ఉంది:", "advisory": "ఇది WeatherGPT వాతావరణ నిర్ణయ సహాయం. అధికారిక హెచ్చరికలకు ప్రాధాన్యత ఇవ్వండి."},
    "ta": {"fallback": "AI சேவை தற்போது கிடைக்கவில்லை. இந்த பதில் சரிபார்க்கப்பட்ட வானிலைத் தரவை அடிப்படையாகக் கொண்டது:", "advisory": "இது WeatherGPT வானிலை முடிவு ஆதரவு. அதிகாரப்பூர்வ எச்சரிக்கைகளுக்கு முன்னுரிமை அளிக்கவும்."},
}


def language_name(language: str) -> str:
    return SUPPORTED_LANGUAGES[language]


def localized_fallback(language: str, context: str) -> str:
    if language == "en":
        return f"AI response is not configured yet. Here is the verified weather context:\n\n{context}"
    labels = TRANSLATIONS[language]
    return f"{labels['fallback']}\n\n{context}"


def grounded_weather_answer(
    language: str,
    location: str,
    question: str,
    current: dict[str, Any],
    daily: list[dict[str, Any]],
    intent: str = "rain_today",
    selected_forecast: dict[str, Any] | None = None,
    time_period: str | None = None,
) -> str:
    """Return a response from the route's already selected verified forecast."""
    legacy_date_guess = selected_forecast is None and time_period is None and any(token in question.casefold() for token in ("tomorrow", "kal", "আগামীকাল", "ଆସନ୍ତାକାଲି"))
    forecast = selected_forecast or (daily[1] if legacy_date_guess and len(daily) > 1 else (daily[0] if daily else {}))
    effective_period = time_period or ("tomorrow" if legacy_date_guess else "today")
    period = {"current": "now", "today": "today", "tomorrow": "tomorrow", "day_after_tomorrow": "the day after tomorrow"}.get(effective_period, "today")
    period = {
        "hinglish": {"today": "aaj", "tomorrow": "kal", "day_after_tomorrow": "parso"},
        "hi": {"today": "आज", "tomorrow": "कल", "day_after_tomorrow": "परसों"},
        "bn": {"today": "আজ", "tomorrow": "আগামীকাল", "day_after_tomorrow": "পরশু"},
        "or": {"today": "ଆଜି", "tomorrow": "ଆସନ୍ତାକାଲି", "day_after_tomorrow": "ପରଦିନ"},
    }.get(language, {}).get(effective_period, period)
    probability = forecast.get("precipitation_probability")
    rain = forecast.get("precipitation_sum")
    if probability is None or rain is None:
        return f"Verified weather data for {location} is incomplete for this forecast question. Please try again shortly."
    description = str(forecast.get("description", current.get("description", "unknown conditions")))
    lowered_description = description.lower()
    rain_expected = probability >= 50 or rain > 0 or any(word in lowered_description for word in ("rain", "drizzle", "thunderstorm", "snow"))
    if language == "hinglish":
        if intent == "current_weather":
            return f"{location} mein abhi {current.get('description', 'weather conditions')} hai, temperature {current.get('temperature', '—')}°C hai."
        if intent == "umbrella_advice":
            return f"{'Haan' if rain_expected else 'Nahi'}, {location} mein {period} umbrella le jana {'better rahega' if rain_expected else 'shayad zaroori nahi hai'}. Rain probability {probability:g}% aur expected rain {rain:g} mm hai."
        return f"{location} mein {period} baarish {'hone ki sambhavna hai' if rain_expected else 'ki sambhavna kam hai'}. Rain probability {probability:g}% aur lagbhag {rain:g} mm rain expected hai."
    if language == "hi":
        if intent == "umbrella_advice":
            return f"{'हाँ' if rain_expected else 'नहीं'}, {location} में {period} छाता {'ले जाना बेहतर है' if rain_expected else 'ज़रूरी नहीं लगता'}। वर्षा की संभावना {probability:g}% और अनुमानित वर्षा {rain:g} mm है।"
        if intent in {"rain_today", "rain_tomorrow"}:
            return f"{location} में {period} बारिश {'संभावित है' if rain_expected else 'संभावित नहीं है'}। वर्षा की संभावना {probability:g}% और अनुमानित वर्षा {rain:g} mm है।"
        return f"{location} में अभी {current.get('description', 'मौसम की स्थिति')} है और तापमान {current.get('temperature', '—')}°C है। {period} वर्षा की संभावना {probability:g}% है।"
    if language == "bn":
        if intent == "current_weather":
            return f"{location}-এ এখন {current.get('description', 'আবহাওয়ার অবস্থা')} এবং তাপমাত্রা {current.get('temperature', '—')}°C।"
        if intent == "umbrella_advice":
            return f"{'হ্যাঁ' if rain_expected else 'না'}, {period} {location}-এ ছাতা নেওয়া {'ভালো হবে' if rain_expected else 'সম্ভবত দরকার নেই'}। বৃষ্টির সম্ভাবনা {probability:g}% এবং আনুমানিক বৃষ্টি {rain:g} মিমি।"
        return f"{period} {location}-এ বৃষ্টির সম্ভাবনা {'আছে' if rain_expected else 'কম'}। বৃষ্টির সম্ভাবনা {probability:g}% এবং আনুমানিক বৃষ্টি {rain:g} মিমি।"
    if language == "or":
        if intent == "current_weather":
            return f"{location}ରେ ବର୍ତ୍ତମାନ {current.get('description', 'ପାଣିପାଗର ସ୍ଥିତି')} ଏବଂ ତାପମାତ୍ରା {current.get('temperature', '—')}°C।"
        if intent == "umbrella_advice":
            return f"{'ହଁ' if rain_expected else 'ନା'}, {period} {location}ରେ ଛତା ନେବା {'ଭଲ ହେବ' if rain_expected else 'ସମ୍ଭବତଃ ଦରକାର ନାହିଁ'}। ବର୍ଷାର ସମ୍ଭାବନା {probability:g}% ଏବଂ ପ୍ରାୟ {rain:g} ମି.ମି. ବର୍ଷା।"
        return f"{period} {location}ରେ ବର୍ଷାର ସମ୍ଭାବନା {'ଅଛି' if rain_expected else 'କମ୍'}। ବର୍ଷାର ସମ୍ଭାବନା {probability:g}% ଏବଂ ପ୍ରାୟ {rain:g} ମି.ମି. ବର୍ଷା।"
    if intent == "current_weather":
        return f"In {location}, current conditions are {current.get('description', 'unavailable')} at {current.get('temperature', '—')}°C, with {current.get('humidity', '—')}% humidity and wind at {current.get('wind_speed', '—')} km/h."
    if intent == "umbrella_advice":
        return f"{'Yes' if rain_expected else 'No'}, carrying an umbrella is {'recommended' if rain_expected else 'probably not necessary'} in {location} {period}. Rain probability is {probability:g}% with about {rain:g} mm expected."
    if intent == "travel_advisory":
        return f"For travel in {location} this week, plan around the forecast: rain probability reaches {max((day.get('precipitation_probability', 0) or 0) for day in daily):g}% and maximum wind reaches {max((day.get('wind_speed_max', 0) or 0) for day in daily):g} km/h. Check official travel updates."
    if intent == "flood_risk":
        return f"WeatherGPT does not detect an official flood warning for {location}. Forecast rainfall reaches {max((day.get('precipitation_sum', 0) or 0) for day in daily):g} mm; avoid low-lying roads if intense rain develops and follow local authority guidance."
    if intent in {"forecast_tomorrow", "forecast", "general_weather"}:
        return f"In {location} {period}, expect {description} with a high of {forecast.get('temperature_max', '—')}°C and a low of {forecast.get('temperature_min', '—')}°C. Rain probability is {probability:g}% with about {rain:g} mm expected."
    base = (
        f"Using verified weather data for {location} {period}: "
        f"{description} "
        f"with a {probability:g}% chance of precipitation."
    )
    if rain_expected:
        return f"Yes, rain is likely in {location} {period}. There is a {probability:g}% chance of rain, with about {rain:g} mm expected.\n\n{base}"
    return f"No, rain is not expected in {location} {period}. There is only a {probability:g}% chance of rain.\n\n{base}"


def format_fallback_context(location: str, current: dict[str, Any], daily: list[dict[str, Any]]) -> str:
    forecast = daily[0] if daily else {}
    return (
        f"Location: {location}\n"
        f"Current weather: {current.get('description', 'unknown')}\n"
        f"Today's rain probability: {forecast.get('precipitation_probability', '—')}%\n"
        f"Today's expected precipitation: {forecast.get('precipitation_sum', '—')} mm"
    )


def localized_advisory(language: str, audience: str, daily: list[dict[str, Any]]) -> str:
    if language == "en":
        from app.services.advisory_service import advisory_guidance

        return advisory_guidance(audience, daily)
    return TRANSLATIONS[language]["advisory"]