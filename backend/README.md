# Setu Backend (FastAPI)

A secure, high-performance Python FastAPI backend for IoT environmental monitoring, automated relay control, real-time worldwide weather geocoding, and explainable AI for sericulture sheds worldwide.

`PostgreSQL` is the supported development database in the current backend. `SQLite` is not a drop-in alternative here because the service layer is built directly on `psycopg2`.

## Core Features:
- **JWT & Role-Based Access Control (`app/core/security.py`, `app/routers/auth.py`):** Protects all shed telemetry and actuator endpoints with user role separation (Super Admin & Farmers).
- **Worldwide Weather & Reverse Geocoding (`app/services/weather_service.py`):** Live weather forecast integration via Open-Meteo and reverse geocoding for any location worldwide based on GPS coordinates or manual search.
- **Deterministic Rules & Hysteresis Engine (`app/services/rules_engine.py`):** Multi-variable control evaluating indoor temp/humidity, outside weather, growth stage parameters, and hysteresis to prevent rapid equipment switching.
- **Safety Interlocks:** Strictly prevents simultaneous operation of heaters and coolers.
- **Explainable AI (`app/services/ai_explainer.py`, `app/routers/ai.py`):** Generates contextual natural-language explanations in English, Kannada, and Telugu.
- **Telemetry & CSV Export (`app/services/telemetry_service.py`, `app/routers/telemetry.py`):** Stores real-time readings, historical series, and exports raw CSV data.

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
