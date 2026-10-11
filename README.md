# Setu — Smart IoT Sericulture Environment Management & Control System

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B.svg)](https://flutter.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-336791.svg)](https://www.postgresql.org/)

> **"The farmer should not have to interpret technical sensor data. Setu interprets the environment and tells the farmer what is happening, why it matters, and what action is being taken."**

---

## 📌 Overview

**Setu** is an end-to-end, IoT-enabled environmental management and automation system purpose-built for silkworm rearing sheds worldwide.

Silkworms (*Bombyx mori*) are highly sensitive to microclimate variations. Even minor deviations in temperature and relative humidity across growth instars (Instars 1 through 5) can cause crop failure, disease outbreak (Flacherie, Grasserie), or inferior cocoon quality. Setu solves this by combining IoT sensing, real-time worldwide weather tracking, deterministic automation rules, hardware safety interlocks, and multilingual explainable AI recommendations in **English, Kannada (ಕನ್ನಡ), and Telugu (తెలుగు)**.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph IoT["IoT Shed Hardware (ESP32)"]
        Sensors["DHT22 / SHT3x Sensors<br/>(Temperature & Humidity)"]
        Actuators["Relay Modules<br/>(Fan, Cooler, Heater, Humidifier)"]
        ESP32["ESP32 Microcontroller<br/>Local Fail-Safe Logic"]
        Sensors --> ESP32
        ESP32 --> Actuators
    end

    subgraph Backend["FastAPI Backend Services"]
        Ingest["Telemetry Ingestion & REST API"]
        Rules["Deterministic Rules Engine<br/>Hysteresis & Safety Interlocks"]
        AI["Explainable AI Engine<br/>(EN, KN, TE Explanations)"]
        Weather["Live Weather Service<br/>(Worldwide Open-Meteo & Geocoding)"]
        Auth["JWT & Role-Based Security"]
        DB[(PostgreSQL Database)]
        
        Ingest --> Rules
        Rules --> AI
        Weather --> Rules
        Rules --> DB
        Auth --> DB
    end

    subgraph Clients["User & Operator Interfaces"]
        MobileApp["Farmer Mobile App (Flutter)<br/>• Trilingual (EN, KN, TE)<br/>• Real-time Shed Monitoring<br/>• Growth Stage Guidance<br/>• Manual Override Stepper"]
        AdminWeb["Super Admin Portal (Web)<br/>• Cluster Health & Analytics<br/>• Farmer & Batch Registry<br/>• Actuator Manual Controls<br/>• CSV Telemetry Export"]
    end

    ESP32 <-->|HTTP / MQTT| Ingest
    Backend <-->|Secure REST / JWT| MobileApp
    Backend <-->|Secure REST / JWT| AdminWeb
```

---

## 🚀 Key Features

- **Growth-Stage Aware Control**: Automatically adjusts target temperature and humidity bands based on silkworm development stage:
  - **Instar 1 (Chawki)**: 27–28°C, 85–90% RH
  - **Instar 2 (Chawki)**: 26–27°C, 80–85% RH
  - **Instar 3**: 25–26°C, 75–80% RH
  - **Instar 4**: 24–25°C, 70–75% RH
  - **Instar 5**: 23–24°C, 65–70% RH
- **Deterministic Rules & Hysteresis Engine**: Prevents rapid equipment toggling and relay wear by enforcing deadbands and minimum cycling intervals.
- **Hardware Safety Interlocks**: Strict mutual exclusion preventing simultaneous operation of heaters and coolers under any condition.
- **Explainable AI (XAI)**: Generates clear, plain-language reasoning for farmers in **English, Kannada, and Telugu**, explaining *why* a particular actuator is running.
- **Farmer Mobile Application (Flutter)**: Clean, intuitive mobile interface offering instant status cards, environmental graphs, stage selector, and manual override dialogs.
- **Super Admin Command Portal (Web)**: Real-time dashboard for sericulture officers and cluster managers to oversee multiple rearing sheds, manage farmer batches, and export telemetry data.
- **Audit Logging & Telemetry Export**: Tamper-evident logging of actuator operations and one-click CSV export for research and agricultural extension services.

---

## 📁 Repository Structure

```
setu/
├── admin_web/                  # Super Admin Command Web Application
│   ├── index.html              # Modern, responsive single-page dashboard
│   ├── app.js                  # Frontend state, API integration, and telemetry charts
│   ├── style.css               # Clean styling with light/dark accents
│   └── README.md               # Admin Portal documentation
│
├── backend/                    # Core Python FastAPI Backend
│   ├── app/
│   │   ├── core/               # Configuration, JWT security, and settings
│   │   ├── models/             # Pydantic data validation schemas
│   │   ├── routers/            # API endpoints (Auth, Sheds, Telemetry, Control, AI, Admin)
│   │   ├── services/           # Rules engine, DB service, AI explainer, Weather
│   │   └── main.py             # FastAPI application entrypoint
│   ├── tests/                  # Pytest test suite (100% passing)
│   ├── .env.example            # Environment variables template
│   ├── requirements.txt        # Python dependency specifications
│   └── README.md               # Backend documentation
│
├── mobile/                     # Cross-Platform Native Mobile App (Flutter)
│   ├── lib/
│   │   ├── l10n/               # Internationalization strings (EN, KN, TE)
│   │   ├── models/             # Dart data models
│   │   ├── providers/          # State management providers
│   │   ├── screens/            # Application screens (Home, AI, Environment, Stages, Insights)
│   │   ├── services/           # API and mock data services
│   │   ├── widgets/            # Custom reusable widgets and modals
│   │   └── main.dart           # Flutter app entrypoint
│   ├── pubspec.yaml            # Flutter package dependencies
│   └── README.md               # Mobile App documentation
│
├── doc/                        # Technical Specifications & Documentation
│   ├── architecture.md         # Full system architecture specification
│   ├── prd.md                  # Comprehensive Product Requirements Document (PRD)
│   ├── rules.md                # Environmental rules, thresholds & safety specification
│   ├── design.md               # UI/UX design specifications
│   ├── tasks.md                # Engineering task list & implementation roadmap
│   └── memory.md               # Technical decisions and architectural memory
│
├── .env.example                # Root environment template
├── .gitignore                  # Global Git ignore file
└── LICENSE                     # MIT License
```

---

## 🛠️ Getting Started

### 1. Prerequisites

- **Python**: 3.12+ (`uv` uses the root `pyproject.toml`)
- **PostgreSQL**: 14+ or 15+
- **Flutter SDK**: 3.x+
- **Git**
- **uv**: recommended for backend dependency and test commands

---

### 2. Backend Setup

`PostgreSQL` is the right choice for this codebase today. The backend is wired directly to `psycopg2` and PostgreSQL SQL semantics, so SQLite would require a real refactor instead of a config change.

1. **Install and start PostgreSQL locally (Ubuntu/Debian)**:
   ```bash
   sudo apt update
   sudo apt install -y postgresql postgresql-contrib
   sudo systemctl enable --now postgresql
   ```

2. **Create the local Setu database and user**:
   ```bash
   sudo -u postgres psql
   ```
   Then run:
   ```sql
   CREATE USER setu_user WITH PASSWORD 'setu_password';
   CREATE DATABASE setu OWNER setu_user;
   GRANT ALL PRIVILEGES ON DATABASE setu TO setu_user;
   \q
   ```

3. **Install Python dependencies with `uv` from the repo root**:
   ```bash
   uv sync
   ```

4. **Configure environment variables**:
   A local `.env` file can live either at the repo root or inside `backend/`. Use:
   ```bash
   cp .env.example .env
   cp backend/.env.example backend/.env
   ```
   The default local development values are:
   ```env
   PROJECT_NAME="Setu"
   API_V1_STR="/api/v1"
   SETU_SECRET_KEY="setu-local-dev-secret-change-me"
   DATABASE_URL="postgresql://setu_user:setu_password@127.0.0.1:5432/setu"
   DEFAULT_REGION="Global Sericulture Network"
   DEFAULT_LATITUDE=0.0
   DEFAULT_LONGITUDE=0.0
   ```

5. **Start the API server**:
   ```bash
   uv run uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
   ```
   - **Interactive API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Alternative Docs (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
   - **Super Admin Portal**: [http://localhost:8000/admin](http://localhost:8000/admin)

6. **Run the automated test suite**:
   ```bash
   uv run pytest backend/tests -v
   ```

---

### 3. Super Admin Command Portal Setup

The Super Admin portal is pre-mounted at `/admin` on the FastAPI server. Simply open:
```
http://localhost:8000/admin
```

Default credentials (pre-seeded):
- **Username**: `admin`
- **Password**: `admin`
*(Includes eye button toggle to show/hide password)*

Alternatively, you can run it as a standalone static site:
```bash
cd admin_web
python -m http.server 3000
```
Then visit [http://localhost:3000](http://localhost:3000).

---

### 4. Mobile App Setup (Flutter)

1. **Navigate to the mobile directory**:
   ```bash
   cd mobile
   ```

2. **Install Flutter packages**:
   ```bash
   flutter pub get
   ```

3. **Run on an emulator or physical device**:
   ```bash
   flutter run
   ```

4. **Build an installable Android APK**:
   ```bash
   flutter build apk --release
   ```
   The generated APK will be at:
   ```bash
   mobile/build/app/outputs/flutter-apk/app-release.apk
   ```
   For a quick test build, use:
   ```bash
   flutter build apk --debug
   ```

5. **If you run the app on a physical Android phone**:
   - Keep the backend running on your computer.
   - Connect both phone and computer to the same Wi-Fi network.
   - In the app settings, set the backend host to your computer's LAN IP, for example `192.168.1.25:8000`.

---

## 🔒 Security & Safety Controls

- **Hardware Safety Interlocks**: Evaluated at the deterministic service level before issuing actuator commands. Cooling and heating circuits cannot be active simultaneously.
- **Hysteresis Deadband**: Enforces a ±0.5°C temperature buffer and ±2% RH buffer around setpoints to prevent rapid relay wear.
- **Fail-Safe Fallbacks**: If sensor communication is interrupted, actuators fall back into a safe default state (ventilation on, heater/cooler off).
- **JWT Authorization**: All telemetry and remote control endpoints require valid Bearer token authentication.

---

## 📖 Detailed Documentation

For in-depth architectural and biological specifications, see the `doc/` directory:
- [Product Requirements Document (PRD)](doc/prd.md)
- [System Architecture](doc/architecture.md)
- [Rules, Automation & Control Specification](doc/rules.md)
- [UI/UX Design Specification](doc/design.md)
- [Implementation Roadmap & Tasks](doc/tasks.md)
- [System Architectural Memory](doc/memory.md)

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
