from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat_routes import router as chat_router
from app.api.location_routes import router as location_router
from app.api.weather_routes import router as weather_router
from app.config import settings
from app.database.database import init_db

app = FastAPI(
    title="WeatherGPT API",
    description="Real-time weather intelligence powered by Open-Meteo.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(weather_router, prefix="/api")
app.include_router(location_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", tags=["health"])
def health_check() -> dict[str, str]:
    return {"name": "WeatherGPT API", "status": "ok"}