# Setu Backend (FastAPI)

A secure, high-performance Python FastAPI backend for IoT environmental monitoring, automated relay control, real-time worldwide weather geocoding, and explainable AI for sericulture sheds worldwide.

`PostgreSQL` is the supported development database in the current backend. `SQLite` is not a drop-in alternative here because the service layer is built directly on `psycopg2`.

## Live Cloud Deployment:
- **Base URL**: `https://setu-8vh9.onrender.com/api/v1`
- **Interactive OpenAPI Documentation (Swagger)**: `https://setu-8vh9.onrender.com/docs`
- **Alternative Docs (ReDoc)**: `https://setu-8vh9.onrender.com/redoc`

## Core Features:
- **JWT, Google Auth & RBAC (`app/core/security.py`, `app/routers/auth.py`):** User registration, login, and `/auth/google-sync` endpoint linking Firebase Google Auth users directly into PostgreSQL with duplicate username collision prevention.
- **IoT Air Quality & CO₂ Automation (`app/services/rules_engine.py`):** Monitors indoor air freshness percentage (`air_quality`). Automatically turns ON the ventilation/exhaust fan if air quality falls below target (`< 80%` / high CO₂), with a `+4%` hysteresis recovery band (`>= 84%`).
- **Research Photoperiod & Light Dimming (`app/services/rules_engine.py`):** Evaluates circadian schedules (Day: 15–30 Lux, Night: <5 Lux / 0% PWM, 5th Instar Spinning: ~10 Lux) and dynamically adjusts bulb PWM duty cycle (`light_brightness`: 0–100%).
- **Worldwide Weather & Reverse Geocoding (`app/services/weather_service.py`):** Live weather forecast integration via Open-Meteo and reverse geocoding for any location worldwide based on GPS coordinates or manual search.
- **Deterministic Rules & Hysteresis Engine (`app/services/rules_engine.py`):** Multi-variable control evaluating indoor temp/humidity, outside weather, growth stage parameters, and hysteresis to prevent rapid equipment switching.
- **Safety Interlocks:** Strictly prevents simultaneous operation of heaters and coolers under any condition.
- **Explainable AI (`app/services/ai_explainer.py`, `app/routers/ai.py`):** Contextual natural-language explanations in English, Kannada, and Telugu.
- **Telemetry & CSV Export (`app/services/telemetry_service.py`, `app/routers/telemetry.py`):** Stores real-time readings, historical series, and exports raw CSV data with automatic schema evolution.

## Running the Backend:
```bash
uv sync
uv run uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```
Interactive OpenAPI documentation will be available at: `http://localhost:8000/docs`.

## Local PostgreSQL Setup:
```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable --now postgresql
sudo -u postgres psql
```

Then run:
```sql
CREATE USER setu_user WITH PASSWORD 'setu_password';
CREATE DATABASE setu OWNER setu_user;
GRANT ALL PRIVILEGES ON DATABASE setu TO setu_user;
\q
```

Copy one of the provided env templates and keep this database URL:

```env
DATABASE_URL="postgresql://setu_user:setu_password@127.0.0.1:5432/setu"
```

## Running the Automated Test Suite:
```bash
uv run pytest backend/tests -v
```
