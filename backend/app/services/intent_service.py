import re
import unicodedata

from pydantic import BaseModel


class WeatherIntent(BaseModel):
    intent: str
    domain: str
    location: str | None = None
    date_reference: str | None = None
    time_reference: str | None = None
    requires_forecast: bool = False
    requires_current_weather: bool = False
    requires_advisory: bool = False
    requires_alert_check: bool = False
    language: str = "en"
    crop: str | None = None


def _normalize_time_reference(text: str) -> str | None:
    lowered = unicodedata.normalize("NFKC", text).lower()
    specific_patterns = [
        ("evening", r"\b(tomorrow evening|this evening|evening|tonight)\b"),
        ("afternoon", r"\b(tomorrow afternoon|this afternoon|afternoon)\b"),
        ("morning", r"\b(tomorrow morning|this morning|morning)\b"),
        ("day_after_tomorrow", r"\b(day after tomorrow|parso|परसों|পরশু|ପରଦିନ)\b"),
        ("tomorrow", r"\b(tomorrow|kal|कल|ଆସନ୍ତାକାଲି|କାଲି|আগামীকাল|কাল)\b"),
        ("today", r"\b(today|aaj|आज|ଆଜି|আজ)\b"),
        ("this_week", r"\b(this week|next 3 days|ଏହି ସପ୍ତାହ|এই সপ্তাহ)\b"),
        ("weekend", r"\b(this weekend|weekend)\b"),
        ("tonight", r"\btonight\b"),
        ("tomorrow", r"\btomorrow\b"),
        ("today", r"\btoday\b"),
    ]
    for normalized, pattern in specific_patterns:
        if re.search(pattern, lowered):
            return normalized
    return None


def detect_language(text: str) -> str:
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    if re.search(r"[\u0B00-\u0B7F]", text):
        return "or"
    if re.search(r"[\u0980-\u09FF]", text):
        return "bn"
    if re.search(r"\b(kya|hai|hoga|hogi|baarish|barish|mausam|kaisa|kal|aaj|parso|chhata)\b", text, re.IGNORECASE):
        return "hinglish"
    return "en"


_detect_language = detect_language


def _extract_location(text: str) -> str | None:
    normalized = unicodedata.normalize("NFKC", text)
    matches = re.findall(
        r"(?:weather\s+(?:of|for)\s+|(?:\bin\b|\bat\b|\bnear\b|\baround\b|में|ରେ|এ|তে)\s+)([A-Za-z][A-Za-z .'-]{1,80}?)(?=\s+(?:in|at|near|around|today|tomorrow|kal|aaj|this|next|if|and|but|right|will|should|can|evening|morning|afternoon|night|में|ରେ|এ|তে)|[?.!,]|$)",
        normalized,
        re.IGNORECASE,
    )
    if matches:
        candidate = matches[-1].strip(" .")
        if candidate.lower() not in {"the weather", "weather", "the forecast", "forecast", "kal", "aaj", "ka", "ki", "ke"}:
            return candidate
    roman_location = re.search(r"\b([A-Za-z][A-Za-z .'-]{1,80}?)\s+(?:me|mein)\b", normalized, re.IGNORECASE)
    if roman_location:
        candidate = roman_location.group(1).split()[-1].strip(" .")
        if candidate.casefold() not in {"kal", "aaj", "parso", "weather", "mausam"}:
            return candidate
    mixed_script = re.search(r"\b([A-Za-z][A-Za-z .'-]{1,80}?)\s+(?:में|ରେ|এ|তে)(?:\s|$|[?.!,])", normalized, re.IGNORECASE)
    if mixed_script:
        candidate = mixed_script.group(1).strip(" .")
        if candidate.lower() not in {"kal", "aaj", "parso", "weather", "mausam"}:
            return candidate
    colloquial = re.search(r"\b([A-Za-z][A-Za-z .'-]{2,60})\s+(?:ka|ki|ke)\s+(?:weather|mausam)\b", normalized, re.IGNORECASE)
    if colloquial:
        candidate = colloquial.group(1).strip(" .")
        if candidate.lower() not in {"kal", "aaj", "parso", "weather", "mausam"}:
            return candidate
    for pattern in (
        r"([\u0980-\u09FF][\u0980-\u09FF\s]{1,40}?)(?:য়|য়|তে|এ)",
        r"([\u0B00-\u0B7F][\u0B00-\u0B7F\s]{1,40}?)(?:ରେ)",
        r"([\u0900-\u097F][\u0900-\u097F\s]{1,40}?)(?:में|मे)",
    ):
        match = re.search(pattern, normalized)
        if match and match.group(1).strip():
            candidate = re.sub(r"^(?:আজ|কাল|আগামীকাল|পরশু|ଆଜି|କାଲି|ଆସନ୍ତାକାଲି|ପରଦିନ|आज|कल|परसों)\s+", "", match.group(1).strip())
            if candidate:
                return {"কলকাতা": "Kolkata"}.get(candidate, candidate)
    script_locations = {
        "কলকাতা": "Kolkata", "কলকাতায়": "Kolkata", "কলকাতায়": "Kolkata",
        "कोलकाता": "Kolkata", "रांची": "Ranchi", "ରାଞ୍ଚି": "Ranchi",
        "ଭୁବନେଶ୍ୱର": "Bhubaneswar", "ଭୁବନେଶ୍ୱରରେ": "Bhubaneswar",
    }
    for phrase, location in script_locations.items():
        if phrase in normalized:
            return location
    return None


extract_location_from_message = _extract_location


def extract_location_candidates(message: str, language: str | None = None) -> list[str]:
    """Return clean location phrases from the current message only."""
    text = unicodedata.normalize("NFKC", message).strip()
    candidates: list[str] = []
    noise = r"(?:kya|kal|aaj|parso|today|tomorrow|tonight|now|currently|please|weather|forecast|temperature|rainfall?|storm|wind|humidity|baarish|barish|hoga|hogi|hai|batao|kitna|what|is|the|will|it|be|how|hot|right|there|a|chance|of|possible|likely|weekend|this|next|later|morning|afternoon|evening|hourly|weekly)"
    patterns = (
        rf"\b(?:in|at|near|around|from|me|mein)\s+([A-Za-z][A-Za-z .'-]*?)(?=\s+(?:{noise})\b|[?.!,]|$)",
        rf"\b([A-Za-z][A-Za-z .'-]*?)\s+(?:in|at|near|around|from|me|mein)\b",
        rf"^\s*([A-Za-z][A-Za-z .'-]*?)\s+(?:weather|forecast|temperature|rain|wind)\b",
        rf"\b(?:weather|forecast|temperature|rain|wind)\s+([A-Za-z][A-Za-z .'-]*?)(?=\s+(?:{noise})\b|[?.!,]|$)",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            candidate = match.group(1).strip(" .,'?-")
            candidate = re.sub(rf"^(?:{noise}|in|at|near|around|from|me|mein)\s+", "", candidate, flags=re.IGNORECASE).strip()
            candidate_words = candidate.casefold().split()
            noise_words = set(re.findall(r"[a-z]+", noise.casefold()))
            if candidate and candidate_words and not all(word in noise_words for word in candidate_words):
                candidates.append(candidate)

    script_patterns = (
        r"([\u0900-\u097F][\u0900-\u097F\s]{1,60}?)(?:में|मे)",
        r"([\u0980-\u09FF][\u0980-\u09FF\s]{1,60}?)(?:য়|য়|তে|এ)",
        r"([\u0B00-\u0B7F][\u0B00-\u0B7F\s]{1,60}?)(?:ରେ)",
    )
    for pattern in script_patterns:
        for match in re.finditer(pattern, text):
            candidate = re.sub(r"^(?:क्या|कल|आज|परसों|আজ|কাল|আগামীকাল|পরশু|ଆଜି|କାଲି|ଆସନ୍ତାକାଲି|ପରଦିନ)\s+", "", match.group(1).strip())
            if candidate:
                candidates.append(candidate)

    extracted = _extract_location(text)
    if extracted:
        candidates.insert(0, extracted)
    unique: list[str] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def _extract_date_reference(message: str, history: str | None = None) -> str | None:
    current = message.lower()
    previous = (history or "").lower()
    for label in ("day after tomorrow", "tomorrow", "today", "tonight", "weekend", "next week", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "this evening", "tomorrow evening", "this afternoon", "tomorrow afternoon", "kal", "aaj", "parso", "कल", "आज", "परसों", "ଆସନ୍ତାକାଲି", "କାଲି", "ଆଜି", "আগামীকাল", "কাল", "পরশু", "আজ"):
        if label in current:
            return {"kal": "tomorrow", "कल": "tomorrow", "ଆସନ୍ତାକାଲି": "tomorrow", "କାଲି": "tomorrow", "আগামীকাল": "tomorrow", "কাল": "tomorrow", "aaj": "today", "आज": "today", "ଆଜି": "today", "আজ": "today", "parso": "day_after_tomorrow", "परसों": "day_after_tomorrow", "পরশু": "day_after_tomorrow", "ପରଦିନ": "day_after_tomorrow"}.get(label, label)
    for label in ("day after tomorrow", "tomorrow", "today", "tonight", "weekend", "next week", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "this evening", "tomorrow evening", "this afternoon", "tomorrow afternoon"):
        if label in previous:
            return label
    return None


def _extract_crop(text: str) -> str | None:
    match = re.search(r"\b(?:my|a|the)\s+([a-z][a-z -]{1,30}?)\s+(?:crop|field)\b|\bcrop\s+is\s+([a-z][a-z -]{1,30})\b", text, re.IGNORECASE)
    if not match:
        return None
    return (match.group(1) or match.group(2)).strip()


def _detect_current_intent(message: str) -> WeatherIntent:
    text = message.strip()
    lowered = text.lower()

    if re.search(r"\b(weekend|this weekend|next weekend|saturday|sunday)\b", lowered):
        return WeatherIntent(
            intent="forecast",
            domain="general",
            location=_extract_location(text),
            date_reference="weekend",
            time_reference="weekend",
            requires_forecast=True,
            language=_detect_language(text),
        )

    is_tomorrow_rain = bool(re.search(r"(?:tomorrow|kal|कल|ଆସନ୍ତାକାଲି|କାଲି|আগামীকাল|কাল).*(?:rain|baarish|barish|rainfall|बारिश|ବର୍ଷା|বৃষ্টি)|(?:rain|baarish|barish|rainfall|बारिश|ବର୍ଷା|বৃষ্টি).*(?:tomorrow|kal|कल|ଆସନ୍ତାକାଲି|କାଲି|আগামীকাল|কাল)", lowered))
    is_today_rain = bool(re.search(r"(?:today|aaj|आज|ଆଜି|আজ).*(?:rain|baarish|barish|rainfall|बारिश|ବର୍ଷା|বৃষ্টি)|(?:rain|baarish|barish|rainfall|बारिश|ବର୍ଷା|বৃষ্টি).*(?:today|aaj|आज|ଆଜି|আজ)", lowered))
    if is_tomorrow_rain and "evening" not in lowered and "afternoon" not in lowered and "morning" not in lowered:
        return WeatherIntent(intent="rain_tomorrow", domain="general", location=_extract_location(text), date_reference="tomorrow", requires_forecast=True, requires_alert_check=True, language=_detect_language(text))
    if is_today_rain:
        return WeatherIntent(intent="rain_today", domain="general", location=_extract_location(text), date_reference="today", requires_forecast=True, requires_alert_check=True, language=_detect_language(text))
    if re.search(r"\b(what about|how about)\b.*\b(tomorrow|kal)\b", lowered):
        return WeatherIntent(intent="forecast_tomorrow", domain="general", location=_extract_location(text), date_reference="tomorrow", requires_forecast=True, language=_detect_language(text))
    if re.search(r"\b(umbrella|chhatr[i]?| छाता)\b", lowered) and not re.search(r"\b(travel|travelling|trip|journey)\b", lowered):
        return WeatherIntent(intent="umbrella_advice", domain="travel", location=_extract_location(text), date_reference=_extract_date_reference(message) or "today", requires_forecast=True, requires_advisory=True, language=_detect_language(text))
    if re.search(r"\b(flood|flooding|waterlogging|baadh|बाढ़)\b", lowered):
        return WeatherIntent(intent="flood_risk", domain="general", location=_extract_location(text), date_reference=_extract_date_reference(message), requires_forecast=True, requires_alert_check=True, language=_detect_language(text))
    if re.search(r"\b(what(?:'s| is) the weather|weather like|current weather|right now|currently|weather kaisa|mausam kaisa)\b|(?:আবহাওয়া|আবহাওয়া|ମୌସମ|ପାଣିପାଗ).*(?:କିପରି|কেমন|कैसा)|(?:weather|mausam).*(?:kaisa|कैसा)", lowered):
        return WeatherIntent(
            intent="current_weather",
            domain="general",
            location=_extract_location(text),
            date_reference=_extract_date_reference(message) or "current",
            time_reference="current",
            requires_current_weather=True,
            requires_forecast=False,
            requires_advisory=False,
            requires_alert_check=False,
            language=_detect_language(text),
        )

    agriculture_intents = [
        ("pesticide_application", r"\b(pesticide|pesticides|spray|spraying)\b"),
        ("fertilizer_application", r"\b(fertilizer|fertiliser|manure)\b"),
        ("irrigation", r"\b(irrigat|watering|water\s+my)\w*\b"),
        ("sowing", r"\b(sow|sowing|planting|seed)\w*\b"),
        ("harvesting", r"\b(harvest|harvesting|reap)\w*\b"),
        ("crop_protection", r"\b(crop\s+protection|protect\s+(?:my|the)\s+crop)\b"),
        ("fungal_disease_risk", r"\b(fungal|fungus|mildew|blight)\b"),
        ("heat_stress", r"\b(heat\s+stress|crop\s+heat|too\s+hot\s+for\s+(?:my|the)\s+crop)\b"),
        ("frost_risk", r"\b(frost|freezing|freeze)\b"),
        ("rainfall_suitability", r"\b(rainfall\s+suitability|suitable\s+rainfall)\b"),
        ("field_work_suitability", r"\b(field\s+work|work\s+in\s+the\s+field)\b"),
    ]
    for agriculture_intent, pattern in agriculture_intents:
        if re.search(pattern, lowered):
            return WeatherIntent(
                intent=agriculture_intent,
                domain="agriculture",
                location=_extract_location(text),
                date_reference=_extract_date_reference(message),
                time_reference=_normalize_time_reference(text),
                requires_forecast=True,
                requires_current_weather=False,
                requires_advisory=True,
                requires_alert_check=True,
                language=_detect_language(text),
                crop=_extract_crop(text),
            )

    if re.search(r"\b(paddy|rice|wheat|crop|field|soil|crops)\b", lowered):
        return WeatherIntent(
            intent="agriculture_advisory",
            domain="agriculture",
            location=_extract_location(text),
                date_reference=_extract_date_reference(message),
            time_reference=_normalize_time_reference(text),
            requires_forecast=True,
            requires_current_weather=False,
            requires_advisory=True,
            requires_alert_check=True,
            language=_detect_language(text),
            crop=_extract_crop(text),
        )

    if re.search(r"\b(travel|trip|carry|go out|travelling|journey|flight|road|safe to travel)\b", lowered):
        return WeatherIntent(
            intent="travel_advisory",
            domain="travel",
            location=_extract_location(text),
                date_reference=_extract_date_reference(message),
            time_reference=_normalize_time_reference(text) or "day",
            requires_forecast=True,
            requires_current_weather=False,
            requires_advisory=True,
            requires_alert_check=True,
            language=_detect_language(text),
        )

    if re.search(r"\b(rain|showers|precipitation|umbrella|storm|heavy rain|wet)\b", lowered):
        return WeatherIntent(
            intent="precipitation",
            domain="general",
            location=_extract_location(text),
                date_reference=_extract_date_reference(message),
            time_reference=_normalize_time_reference(text),
            requires_forecast=True,
            requires_current_weather=False,
            requires_advisory=False,
            requires_alert_check=True,
            language=_detect_language(text),
        )

    if re.search(r"\b(temp(?:erature)?|hot|cold|heat|warm|cool|humid|humidity|wind)\b", lowered):
        return WeatherIntent(
            intent="temperature",
            domain="general",
            location=_extract_location(text),
            date_reference=_extract_date_reference(text),
            time_reference=_normalize_time_reference(text),
            requires_forecast=True,
            requires_current_weather=False,
            requires_advisory=False,
            requires_alert_check=False,
            language=_detect_language(text),
        )

    return WeatherIntent(
        intent="general_weather",
        domain="general",
        location=_extract_location(text),
        date_reference=_extract_date_reference(message),
        time_reference=_normalize_time_reference(text),
        requires_forecast=True,
        requires_current_weather=False,
        requires_advisory=False,
        requires_alert_check=False,
        language=_detect_language(text),
    )


def detect_intent(message: str, history: list[str] | None = None) -> WeatherIntent:
    """Parse the current turn, then fill only missing follow-up context."""
    current = _detect_current_intent(message)
    candidates = extract_location_candidates(message, current.language)
    if candidates:
        current.location = candidates[0]
    if not history or current.location:
        return current

    previous = None
    for previous_message in reversed(history):
        candidate_intent = _detect_current_intent(previous_message)
        previous_candidates = extract_location_candidates(previous_message, candidate_intent.language)
        if previous_candidates:
            candidate_intent.location = previous_candidates[0]
            previous = candidate_intent
            break
    if previous is None:
        return current
    values = current.model_dump()
    values["location"] = previous.location
    if not values.get("date_reference"):
        values["date_reference"] = previous.date_reference
    if not values.get("time_reference"):
        values["time_reference"] = previous.time_reference
    if current.intent in {"general_weather", "current_weather"} and previous.intent not in {"general_weather", "current_weather"}:
        for key in ("intent", "domain", "requires_forecast", "requires_current_weather", "requires_advisory", "requires_alert_check", "crop"):
            values[key] = getattr(previous, key)
    return WeatherIntent(**values)
