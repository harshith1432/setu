# SeriCare — Smart IoT Sericulture Environment Management & Control System

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B.svg)](https://flutter.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-336791.svg)](https://www.postgresql.org/)

> **"The farmer should not have to interpret technical sensor data. SeriCare interprets the environment and tells the farmer what is happening, why it matters, and what action is being taken."**

---

## 📌 Overview

**SeriCare** is an end-to-end, IoT-enabled environmental management and automation system purpose-built for silkworm rearing sheds in the **Mulbagal sericulture cluster (Kolar, Karnataka, India)**.

Silkworms (*Bombyx mori*) are highly sensitive to microclimate variations. Even minor deviations in temperature and relative humidity across growth instars (Instars 1 through 5) can cause crop failure, disease outbreak (Flacherie, Grasserie), or inferior cocoon quality. SeriCare solves this by combining IoT sensing, deterministic automation rules, hardware safety interlocks, and multilingual explainable AI recommendations in **English, Kannada (ಕನ್ನಡ), and Telugu (తెలుగు)**.

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
        Weather["Weather Trend Service<br/>(Mulbagal Microclimate)"]
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
sericare/
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

- **Python**: 3.10+ (Recommended: Python 3.11 or 3.13)
- **PostgreSQL**: 14+ (or cloud-hosted PostgreSQL instance)
- **Flutter SDK**: 3.x+ (for mobile app development)
- **Git**

---

### 2. Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # On Windows
   python -m venv venv
   venv\Scripts\activate

   # On Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and update the parameters:
   ```bash
   cp .env.example .env
   ```
   Example `.env` configuration:
   ```env
   PROJECT_NAME="SeriCare IoT Backend"
   API_V1_STR="/api/v1"
   SERICARE_SECRET_KEY="your-secret-key-change-this-in-production"
   DATABASE_URL="postgresql://postgres:password@localhost:5432/sericare"
   DEFAULT_REGION="Mulbagal, Kolar, Karnataka"
   DEFAULT_LATITUDE=13.1633
   DEFAULT_LONGITUDE=78.3944
   ```

5. **Start the API Server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   - **Interactive API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Alternative Docs (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
   - **Super Admin Portal**: [http://localhost:8000/admin](http://localhost:8000/admin)

6. **Run the Automated Test Suite**:
   ```bash
   pytest tests -v
   ```

---

### 3. Super Admin Command Portal Setup

The Super Admin portal is pre-mounted at `/admin` on the FastAPI server. Simply open:
```
http://localhost:8000/admin
```

Default credentials (pre-seeded):
- **Username**: `superadmin`
- **Password**: `adminsecure2026`

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
