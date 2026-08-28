from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class CoordinateQuery(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ChatLocation(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str | None = Field(default=None, max_length=200)


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=1000
    )

    selected_location: ChatLocation | str | None = Field(
        default=None,
    )

    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90
    )

    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180
    )

    audience: str = Field(
        default="general",
        pattern="^(general|farmer|traveller)$"
    )

    language: str | None = Field(default=None, max_length=20)

    conversation_history: list[ConversationMessage] = Field(
        default_factory=list,
        max_length=10,
    )

    session_id: str | None = Field(default=None, max_length=120)

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_location_field(cls, values: Any) -> Any:
        if isinstance(values, dict) and "selected_location" not in values and "location" in values:
            values = dict(values)
            values["selected_location"] = values["location"]
        return values

    @model_validator(mode="after")
    def validate_coordinates(self) -> "ChatRequest":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        return self

    @property
    def location(self) -> ChatLocation | str | None:
        """Backward-compatible access for callers using the old field name."""
        return self.selected_location


class ChatResponse(BaseModel):
    answer: str = Field(min_length=1)
    location: dict[str, Any]
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    advisories: list[str] = Field(default_factory=list)
    weather_context: Any
    language: str
    llm_available: bool = False
    intent: dict[str, Any] = Field(default_factory=dict)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    agriculture_advisory: dict[str, Any] | None = None
