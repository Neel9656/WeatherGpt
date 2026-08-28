# WeatherGPT

WeatherGPT is a modular weather intelligence platform. Phase 3 adds grounded conversational weather responses and audience-specific guidance to the responsive React dashboard, using real Open-Meteo location search and forecast data.

## Phase 1 setup

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Interactive API documentation is at `/docs`.

## Phase 2 frontend

Install Node.js 20 or newer, then run:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. For deployment, set `VITE_API_URL` to the public backend URL before running the frontend build, for example `https://api.example.com/api`; Vite embeds this value at build time.

## Endpoints

```text
GET  /                         health check
GET  /api/location?query=...   Open-Meteo geocoding
GET  /api/weather?latitude=...&longitude=...  current weather
GET  /api/forecast?latitude=...&longitude=...&forecast_type=hourly|daily
GET  /api/alerts?latitude=...&longitude=...  WeatherGPT forecast risk assessments
GET  /api/weather/overview?latitude=...&longitude=...  bundled current, hourly, daily, and risk data
POST /api/chat                  grounded weather chat and advisory response
```

Examples:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/location?query=Bhubaneswar"
Invoke-RestMethod "http://127.0.0.1:8000/api/weather?latitude=20.2961&longitude=85.8245"
Invoke-RestMethod "http://127.0.0.1:8000/api/forecast?latitude=20.2961&longitude=85.8245&forecast_type=daily"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/chat" -ContentType "application/json" -Body '{"message":"Will it rain tomorrow?"}'
```

Chat accepts `language` values `en`, `hi`, `bn`, `or`, `te`, or `ta`, plus optional selected coordinates and `audience` values (`general`, `farmer`, `traveller`, or `urban`). Weather numbers remain standardized. Alert results are WeatherGPT forecast risk assessments, never official warnings.

Chat sends recent conversation history and the selected dashboard location to the backend. The backend resolves any location named in the current message first, then recent conversation context, then the selected location. Configure `LLM_API_KEY` and `LLM_PROVIDER=openai` in `backend/.env` to enable grounded LLM responses; without them, the verified deterministic fallback remains available.

## Deployment environment

Backend variables: `LLM_API_KEY`, `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_URL`, `CORS_ORIGINS`, `DATABASE_URL`, and `REQUEST_TIMEOUT_SECONDS`. Set `CORS_ORIGINS` as a comma-separated list. Frontend uses `VITE_API_URL` (for example, `https://api.example.com/api`); never put LLM secrets in frontend variables.

The active weather provider is Open-Meteo. Historical climate analysis, official alerts, GFS, and WRF are adapter points only and are not claimed as integrated data sources.

## CSV collection

```powershell
python data_collector.py --city Bhubaneswar 20.2961 85.8245 --city Ranchi 23.3441 85.3096
```

The collector writes to `backend/data/weather_data.csv` and deduplicates by location and timestamp. It fails clearly when Open-Meteo is unavailable; it never writes fabricated weather values.

## Optional PostgreSQL persistence

Set `DATABASE_URL` in `backend/.env` to enable automatic storage of chat history, current observations, and daily forecasts. To run the complete local stack with Docker:

```powershell
docker compose up --build
```

The backend remains fully functional without PostgreSQL; persistence is skipped when `DATABASE_URL` is empty.

## Architecture roadmap

The backend keeps API routes, external weather access, schemas, and utilities separate. The frontend keeps all backend calls in `frontend/src/services/api.js` and displays live loading, network failure, and deferred-chat states. Later phases can add PostgreSQL/SQLAlchemy persistence, LLM grounding, advisories, official IMD warning adapters, GFS/WRF/ECMWF adapters, voice, and real-time ingestion.