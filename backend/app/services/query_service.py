from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class TimePeriod(StrEnum):
    CURRENT = "current"
    TODAY = "today"
    TOMORROW = "tomorrow"
    DAY_AFTER_TOMORROW = "day_after_tomorrow"
    NEXT_3_DAYS = "next_3_days"


class Intent(StrEnum):
    CURRENT_WEATHER = "current_weather"
    RAIN_QUERY = "rain_query"
    UMBRELLA_ADVICE = "umbrella_advice"
    TRAVEL_ADVICE = "travel_advice"
    FORECAST = "forecast"


@dataclass
class ParsedQuery:
    original_message: str
    normalized_message: str
    intent: Intent
    time_period: TimePeriod
    explicit_location: str | None


TEMPORAL_PATTERNS = [
    (
        TimePeriod.DAY_AFTER_TOMORROW,
        [
            r"\bday\s+after\s+tomorrow\b",
            r"\bparso\b",
            r"परसों",
        ],
    ),
    (
        TimePeriod.NEXT_3_DAYS,
        [
            r"\bnext\s+3\s+days?\b",
            r"\bnext\s+three\s+days?\b",
        ],
    ),
    (
        TimePeriod.TOMORROW,
        [
            r"\btomorrow\b",
            r"\bkal\b",
            r"\bkal\s+ka\b",
            r"कल",
            r"ଆସନ୍ତାକାଲି",
            r"আগামীকাল",
        ],
    ),
    (
        TimePeriod.TODAY,
        [
            r"\btoday\b",
            r"\baaj\b",
            r"\baaj\s+ka\b",
            r"आज",
            r"ଆଜି",
            r"আজ",
        ],
    ),
    (
        TimePeriod.CURRENT,
        [
            r"\bright\s+now\b",
            r"\bcurrently\b",
            r"\bcurrent\b",
            r"\bnow\b",
            r"\babhi\b",
            r"अभी",
        ],
    ),
]


def normalize_message(message: str) -> str:
    return re.sub(r"\s+", " ", message.strip())


def detect_time_period(message: str) -> TimePeriod:
    text = message.casefold()

    for period, patterns in TEMPORAL_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return period

    return TimePeriod.CURRENT


def detect_intent(message: str) -> Intent:
    text = message.casefold()

    if any(word in text for word in [
        "umbrella",
        "छाता",
        "chhata",
        "छतरी",
    ]):
        return Intent.UMBRELLA_ADVICE

    if any(word in text for word in [
        "travel",
        "journey",
        "trip",
        "यात्रा",
        "safar",
    ]):
        return Intent.TRAVEL_ADVICE

    if any(word in text for word in [
        "rain",
        "rainfall",
        "baarish",
        "barish",
        "बारिश",
        "बৃষ্টি",
        "ବର୍ଷା",
    ]):
        return Intent.RAIN_QUERY

    if any(word in text for word in [
        "today",
        "tomorrow",
        "kal",
        "aaj",
        "forecast",
        "week",
        "आज",
        "कल",
        "আগামীকাল",
        "ଆସନ୍ତାକାଲି",
    ]):
        return Intent.FORECAST

    return Intent.CURRENT_WEATHER


def protect_temporal_words(message: str) -> str:
    text = message

    for _, patterns in TEMPORAL_PATTERNS:
        for pattern in patterns:
            text = re.sub(
                pattern,
                " ",
                text,
                flags=re.IGNORECASE
            )

    return re.sub(r"\s+", " ", text).strip()


def extract_explicit_location(message: str) -> str | None:
    """
    Extract a plausible explicit location.

    IMPORTANT:
    Temporal words such as 'kal', 'aaj' and 'parso'
    are removed before this logic runs.
    """

    cleaned = protect_temporal_words(message)

    patterns = [
        r"\b(?:in|at|near|around)\s+([A-Za-z][A-Za-z .'-]{1,80}?)(?=\s+(?:in|at|near|around|if|i\s+am|today|tomorrow|right|will|should|can)\b|[?.!,]|$)",
        r"\bweather\s+(?:of|in)\s+([A-Za-z][A-Za-z .'-]{1,80}?)(?=\s+(?:in|at|near|around|if|i\s+am|today|tomorrow|right|will|should|can)\b|[?.!,]|$)",
        r"\b(?:in|में|में\s+ही)\s+([A-Za-z][A-Za-z .'-]{1,80}?)(?=\s+(?:in|at|near|around|if|i\s+am|today|tomorrow|right|will|should|can)\b|[?.!,]|$)",
    ]

    for pattern in patterns:
        matches = list(re.finditer(pattern, cleaned, re.IGNORECASE))

        if matches:
            match = matches[-1]
            candidate = match.group(1)

            candidate = re.split(
                r"\b(?:weather|mausam|rain|baarish|barish|will|is|be|today|tomorrow|right|how|what|kya|hoga|hai)\b",
                candidate,
                flags=re.IGNORECASE,
            )[0]

            candidate = candidate.strip(" .,'?-")

            if len(candidate) >= 2:
                return candidate

    # Special case:
    # "... Madhya Pradesh"
    # "... Ranchi"
    #
    # We deliberately do NOT treat a temporal word as a location.
    return None


def parse_weather_query(message: str) -> ParsedQuery:
    normalized = normalize_message(message)

    return ParsedQuery(
        original_message=message,
        normalized_message=normalized,
        intent=detect_intent(normalized),
        time_period=detect_time_period(normalized),
        explicit_location=extract_explicit_location(normalized),
    )