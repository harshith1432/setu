# SeriCare Backend (FastAPI)

A secure, high-performance Python FastAPI backend for IoT environmental monitoring, automated relay control, and explainable AI for sericulture sheds in Mulbagal.

## Core Features:
- **JWT & Role-Based Access Control (`app/core/security.py`, `app/routers/auth.py`):** Protects all shed telemetry and actuator endpoints.
- **Deterministic Rules & Hysteresis Engine (`app/services/rules_engine.py`):** Multi-variable control evaluating indoor temp/humidity, outside weather, growth stage parameters, and hysteresis to prevent rapid equipment switching.
- **Safety Interlocks:** Strictly prevents simultaneous operation of heaters and coolers.
- **Explainable AI (`app/services/ai_explainer.py`, `app/routers/ai.py`):** Generates contextual natural-language explanations in English, Kannada, and Telugu.
- **Telemetry & CSV Export (`app/services/telemetry_service.py`, `app/routers/telemetry.py`):** Stores real-time readings, historical series, and exports raw CSV data.

## Running the Backend:
```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive OpenAPI documentation will be available at: `http://localhost:8000/docs`.

## Running the Automated Test Suite:
```bash
cd backend
python -m pytest tests -v
```
