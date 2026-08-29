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
    weekend_forecasts: list[dict[str, Any]] | None = None,
) -> str:
    """Return a direct, easy-to-read response using the verified weather data."""
    legacy_date_guess = selected_forecast is None and time_period is None and any(token in question.casefold() for token in ("tomorrow", "kal", "আগামীকাল", "ଆସନ୍ତାକାଲି"))
    forecast = selected_forecast or (daily[1] if legacy_date_guess and len(daily) > 1 else (daily[0] if daily else {}))
    effective_period = time_period or ("tomorrow" if legacy_date_guess else "today")
    period = {"current": "now", "today": "today", "tomorrow": "tomorrow", "day_after_tomorrow": "the day after tomorrow"}.get(effective_period, "today")
    period_labels = {
        "hinglish": {"today": "aaj", "tomorrow": "kal", "day_after_tomorrow": "parso"},
        "hi": {"today": "आज", "tomorrow": "कल", "day_after_tomorrow": "परसों"},
        "bn": {"today": "আজ", "tomorrow": "আগামীকাল", "day_after_tomorrow": "পরশু"},
        "or": {"today": "ଆଜି", "tomorrow": "ଆସନ୍ତାକାଲି", "day_after_tomorrow": "ପରଦିନ"},
    }
    period = period_labels.get(language, {}).get(effective_period, period)

    if effective_period == "weekend" and weekend_forecasts:
        days = " while ".join(
            f"{item.get('date')} is expected to have {item.get('description')} with a {item.get('precipitation_probability')}% rain probability and about {item.get('precipitation_sum')} mm expected"
            for item in weekend_forecasts
        )
        return f"This weekend in {location}, {days}."

    probability = forecast.get("precipitation_probability")
    rain = forecast.get("precipitation_sum")
    if probability is None or rain is None:
        return f"Verified weather data for {location} is incomplete for this forecast question. Please try again shortly."

    description = str(forecast.get("description", current.get("description", "unknown conditions")))
    lowered_description = description.lower()
    rain_expected = probability >= 50 or rain > 0 or any(word in lowered_description for word in ("rain", "drizzle", "thunderstorm", "snow"))
    wind_speed = forecast.get("wind_speed_max") or current.get("wind_speed") or 0
    severe_weather = any(word in lowered_description for word in ("thunderstorm", "storm", "rain", "heavy rain", "hail")) or probability >= 80 or wind_speed >= 25

    def rain_status_text(value: float) -> str:
        if value >= 76:
            return "Rain is very likely." if language == "en" else ("বৃষ্টির সম্ভাবনা খুব বেশি।" if language == "bn" else "बारिश बहुत अधिक संभावना है।")
        if value >= 51:
            return "Rain is likely." if language == "en" else ("বৃষ্টি likely।" if language == "bn" else "बारिश की संभावना है।")
        if value >= 21:
            return "There is a chance of rain." if language == "en" else ("বৃষ্টির সম্ভাবনা আছে।" if language == "bn" else "बारिश की संभावना है।")
        return "Rain is unlikely." if language == "en" else ("বৃষ্টির সম্ভাবনা কম।" if language == "bn" else "बारिश की संभावना कम है।")

    def wind_status_text(value: float) -> str:
        if value >= 30:
            return "Expect strong winds." if language == "en" else ("শক্তিশালী বাতাসের সম্ভাবনা আছে।" if language == "bn" else "मजबूत हवा की उम्मीद है।")
        if value >= 18:
            return "It may be a little breezy." if language == "en" else ("বাতাস কিছুটা বইতে পারে।" if language == "bn" else "हल्की हवा चल सकती है।")
        return "Conditions are fairly calm." if language == "en" else ("পরিস্থিতি比較ভাবে শান্ত।" if language == "bn" else "हालात काफी शांत हैं।")

    def short_follow_up(language_code: str, intent_name: str) -> str:
        if language_code == "bn":
            if intent_name in {"travel_advisory", "travel"}:
                return "আপনি জিজ্ঞেস করতে পারেন: কখন বৃষ্টি শুরু হবে? ছাতা নিতে হবে?"
            if intent_name in {"umbrella_advice", "rain_today", "rain_tomorrow", "precipitation"}:
                return "আপনি জিজ্ঞেস করতে পারেন: সন্ধ্যায় বৃষ্টি হবে কি? পরের ৩ দিনে আবহাওয়া কেমন?"
            if intent_name in {"temperature"}:
                return "আপনি জিজ্ঞেস করতে পারেন: পরের ৩ দিনে তাপমাত্রা কেমন হবে?"
            return "আপনি জিজ্ঞেস করতে পারেন: পরের ৩ দিনে আবহাওয়া কেমন?"
        if language_code == "hi":
            if intent_name in {"travel_advisory", "travel"}:
                return "आप पूछ सकते हैं: बारिश कब शुरू होगी? क्या छाता ले जाना चाहिए?"
            if intent_name in {"umbrella_advice", "rain_today", "rain_tomorrow", "precipitation"}:
                return "आप पूछ सकते हैं: शाम को बारिश होगी? अगले 3 दिनों का मौसम कैसा रहेगा?"
            return "आप पूछ सकते हैं: अगले 3 दिनों का मौसम कैसा रहेगा?"
        if intent_name in {"travel_advisory", "travel"}:
            return "You could ask: What time will it rain? Should I carry an umbrella?"
        if intent_name in {"umbrella_advice", "rain_today", "rain_tomorrow", "precipitation"}:
            return "You could ask: When will the rain start? Will it rain in the evening?"
        if intent_name in {"temperature"}:
            return "You could ask: How hot will it be over the next few days?"
        return "You could ask: How is the weather for the next 3 days?"

    def decision_prefix(value: str, decision: str) -> str:
        return f"{value} {decision}"

    if language == "bn":
        if intent == "travel_advisory":
            status = "🔴 ভ্রমণ: সম্ভব হলে এড়িয়ে চলুন" if severe_weather else "🟡 ভ্রমণ: সতর্কতার সাথে চলুন"
            direct = "ভ্রমণ করা সম্ভব, কিন্তু আগামীকাল ভুবনেশ্বরের আবহাওয়া ভেজা ও ঝড়ের মতো থাকতে পারে।" if not severe_weather else "মোটেই অপ্রয়োজনীয় ভ্রমণ এড়িয়ে যাওয়াই ভালো হবে।"
            reason = f"কারণ? {rain_status_text(probability)} {wind_status_text(wind_speed)}"
            advice = "💡 যদি ভ্রমণ জরুরি হয়, ছাতা বা রেইনকোট নিয়ে নিন এবং একটু বেশি সময় রাখুন।" if not severe_weather else "💡 যদি ভ্রমণ জরুরি না হয়, অন্য দিন বা সময়ের কথা ভাবুন।"
            return f"{status}\n\n{direct}\n\n{reason}\n\n{advice}\n\n{short_follow_up('bn', intent)}"
        if intent == "umbrella_advice":
            return f"☔ হ্যাঁ, ছাতা অবশ্যই নিতে হবে। {period_labels['bn'].get(effective_period, 'আগামীকাল')} {location}-এ বৃষ্টির সম্ভাবনা {probability:g}%।\n\nকারণ? {rain_status_text(probability)}\n\n💡 ছোট্ট ভ্রমণেও ছাতা বা রেইনকোট রাখুন।\n\n{short_follow_up('bn', intent)}"
        if intent in {"rain_today", "rain_tomorrow", "precipitation"}:
            certainty = "খুব সম্ভব" if probability >= 76 else "সম্ভব" if probability >= 51 else "একটু সম্ভাবনা"
            return f"☔ হ্যাঁ, {period_labels['bn'].get(effective_period, 'আগামীকাল')} বৃষ্টি {certainty}। {location}-এ বৃষ্টির সম্ভাবনা {probability:g}%।\n\nকারণ? {rain_status_text(probability)} {('আবহাওয়া ঝড়মুখী হতে পারে।' if severe_weather else '')}\n\n💡 ছাতা নিয়ে বেরোনো ভালো।\n\n{short_follow_up('bn', intent)}"
        if intent in {"temperature", "hot"}:
            return f"🌡️ {location}-এ {period} তাপমাত্রা {'গরম' if (current.get('temperature') or forecast.get('temperature_max') or 0) >= 30 else 'মোটামুটি'} থাকবে।\n\nকারণ? {forecast.get('temperature_max', current.get('temperature', '—'))}°C পর্যন্ত উঠতে পারে।\n\n💡 গরমে পানি পান করুন এবং দিনের প্রধান সময়ে বাইরে কম থাকুন।\n\n{short_follow_up('bn', intent)}"
        if intent == "current_weather":
            return f"🌤️ {location}-এ এখন {current.get('description', 'আবহাওয়া')} অনুভূত হচ্ছে। {current.get('temperature', '—')}°C, আর {current.get('humidity', '—')}% আর্দ্রতা আছে।\n\n💡 এখন বাইরে গেলে ছাতা ও পানি রাখুন।\n\n{short_follow_up('bn', intent)}"
        if intent in {"forecast_tomorrow", "forecast", "general_weather"}:
            return f"📌 {period_labels['bn'].get(effective_period, 'আগামীকাল')} {location}-এ আবহাওয়া {'ভেজা ও ঝড়মুখী' if severe_weather else 'মোটামুটি অনুকূল'} হতে পারে।\n\nকারণ? {rain_status_text(probability)} {wind_status_text(wind_speed)}\n\n💡 প্রয়োজনে ছাতা নিয়ে বের হন।\n\n{short_follow_up('bn', intent)}"

    if language == "hi":
        if intent == "travel_advisory":
            status = "🔴 यात्रा: संभव हो तो बचें" if severe_weather else "🟡 यात्रा: सावधानी से जाएँ"
            direct = "यात्रा संभव है, लेकिन कल Bhubaneswar में मौसम गीला और आंधी जैसा रह सकता है।" if not severe_weather else "अनावश्यक यात्रा से बचना ठीक रहेगा।"
            reason = f"कारण? {rain_status_text(probability)} {wind_status_text(wind_speed)}"
            advice = "💡 अगर यात्रा जरूरी है, छाता या रेनकोट साथ रखें और थोड़ा अतिरिक्त समय ले लें।" if not severe_weather else "💡 अगर जरूरी नहीं है, तो अलग समय या दिन की योजना बनाएं।"
            return f"{status}\n\n{direct}\n\n{reason}\n\n{advice}\n\n{short_follow_up('hi', intent)}"
        if intent == "umbrella_advice":
            return f"☔ हाँ, छाता जरूर लें। {location} में {period} बारिश की संभावना {probability:g}% है।\n\nकारण? {rain_status_text(probability)}\n\n💡 छोटा सफर भी छाता साथ रखें।\n\n{short_follow_up('hi', intent)}"
        if intent in {"rain_today", "rain_tomorrow", "precipitation"}:
            return f"☔ हाँ, {period} बारिश की संभावना है। {location} में बारिश की संभावना {probability:g}% है।\n\nकारण? {rain_status_text(probability)} {wind_status_text(wind_speed)}\n\n💡 छाता या रेनकोट साथ लें।\n\n{short_follow_up('hi', intent)}"

    if intent == "travel_advisory":
        status = "🔴 Travel: Avoid if possible" if severe_weather else "🟡 Travel: Use caution"
        direct = "You can travel tomorrow, but expect wet and stormy weather in {location}.".format(location=location) if not severe_weather else "I would avoid non-essential travel tomorrow if possible."
        reason = f"Why? {rain_status_text(probability)} {wind_status_text(wind_speed)}"
        advice = "💡 If your trip is necessary, carry rain protection and allow extra time for travel." if not severe_weather else "💡 Avoid unnecessary trips, especially in low-lying or exposed areas."
        return f"{status}\n\n{direct}\n\n{reason}\n\n{advice}\n\n{short_follow_up('en', intent)}"
    if intent == "umbrella_advice":
        return f"☔ Yes, definitely carry an umbrella. There is a {probability:g}% chance of rain {period} in {location}.\n\nWhy? {rain_status_text(probability)}\n\n💡 A rain jacket or umbrella will make the day much easier.\n\n{short_follow_up('en', intent)}"
    if intent in {"rain_today", "rain_tomorrow", "precipitation"}:
        certainty = "very likely" if probability >= 76 else "likely" if probability >= 51 else "possible"
        return f"☔ Yes, rain is {certainty} {period}. There is a {probability:g}% chance of rain in {location}.\n\nWhy? {rain_status_text(probability)} {('Thunderstorms are possible.' if severe_weather else '')}\n\n💡 Carry an umbrella or rain jacket if you are going out.\n\n{short_follow_up('en', intent)}"
    if intent == "current_weather":
        return f"🌤️ Right now, {location} feels {current.get('description', 'mild')} with a temperature of {current.get('temperature', '—')}°C.\n\nWhy? The air is {current.get('humidity', '—')}% humid and conditions are {current.get('description', 'changeable')}.\n\n💡 It is a good idea to carry light rain protection if you are heading out.\n\n{short_follow_up('en', intent)}"
    if intent in {"temperature", "hot"}:
        feel = "hot" if (current.get('temperature') or forecast.get('temperature_max') or 0) >= 30 else "mild"
        return f"🌡️ It will feel {feel} tomorrow in {location}.\n\nWhy? The daytime high is around {forecast.get('temperature_max', current.get('temperature', '—'))}°C.\n\n💡 Stay hydrated and avoid long periods in the midday sun.\n\n{short_follow_up('en', intent)}"
    if intent in {"forecast_tomorrow", "forecast", "general_weather"}:
        summary = "wet and stormy" if severe_weather else "pleasant with a chance of rain" if probability >= 21 else "mostly calm"
        return f"📌 Tomorrow in {location} is likely to be {summary}.\n\nWhy? {rain_status_text(probability)} {wind_status_text(wind_speed)}\n\n💡 Keep a light rain plan ready if you are out during the day.\n\n{short_follow_up('en', intent)}"

    base = (
        f"Using verified weather data for {location} {period}: "
        f"{description} "
        f"with a {probability:g}% chance of precipitation."
    )
    if rain_expected:
        return f"☔ Yes, rain is likely in {location} {period}. There is a {probability:g}% chance of rain.\n\nWhy? {rain_status_text(probability)}\n\n{base}"
    return f"☀️ Rain is not expected to be a major issue in {location} {period}.\n\nWhy? {rain_status_text(probability)}\n\n{base}"


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