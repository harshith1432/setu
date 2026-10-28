# Setu — Smart IoT Sericulture Environment Management & Enterprise Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B.svg)](https://flutter.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-336791.svg)](https://www.postgresql.org/)
[![OWASP ASVS 5.0](https://img.shields.io/badge/OWASP-ASVS%20Level%202-success.svg)](docs/security/ASVS_5_IMPLEMENTATION_MATRIX.md)
[![Tests Passing](https://img.shields.io/badge/Tests-103%20Passing-brightgreen.svg)](backend/tests/)

> **"The farmer should not have to interpret technical sensor data. Setu interprets the environment and tells the farmer what is happening, why it matters, and what action is being taken."**

---

## 📌 Executive Overview

**Setu** is an enterprise-grade, distributed Internet of Things (IoT) precision sericulture management and microclimate automation platform purpose-built for silkworm rearing sheds worldwide.

Silkworms (*Bombyx mori*) are poikilothermic and exceptionally sensitive to microclimate variations. Minor fluctuations in temperature, relative humidity, air quality ($CO_2$), or lighting during growth instars (Instars 1 through 5) can trigger devastating disease outbreaks (Flacherie, Grasserie), stunted development, or inferior cocoon harvest yields. 

Setu provides a full-stack solution combining industrial edge sensing, automated actuator regulation, live worldwide weather integration, deterministic biological rules, and explainable AI recommendations in **English, Kannada (ಕನ್ನಡ), and Telugu (తెలుగు)**.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph EdgeLayer["1. IoT Edge Hardware Layer (ESP32)"]
        Sensors["Sensors<br/>• SHT3x/DHT22 (Temp & Humidity)<br/>• MQ-135 (Air Quality & CO₂)<br/>• BH1750 / LDR (Circadian Lux)"]
        Actuators["Actuators & Relays<br/>• Exhaust / Cross-Ventilation Fan<br/>• Evaporative Cooler / Fogger<br/>• PTC Ceramic Heating Element<br/>• PWM Dimmable Grow Light"]
        ESP32["ESP32 Microcontroller<br/>Local Fail-Safe & Hardware Interlocks"]
        Sensors --> ESP32
        ESP32 --> Actuators
    end

    subgraph BackendLayer["2. Enterprise Cloud Backend (FastAPI & PostgreSQL)"]
        Ingress["API Ingress & Rate Limiting (OWASP Top 10)"]
        AuthService["Unified Auth & Per-Tab Session Engine<br/>• Independent Multi-Tab Isolation<br/>• Server-Side Session Tracking<br/>• Token Revocation & JTI Blacklist"]
        RulesEngine["Biological Hysteresis Rules Engine<br/>(Instars 1-5 Setpoints & Circadian Timers)"]
        RBAC["Role-Authoritative Access Controller<br/>(10 Personas: Admin to Farmer)"]
        WeatherService["Worldwide GPS Weather Service<br/>(Open-Meteo & WMO Code Resolvers)"]
        XAI["Explainable AI & Voice Synthesizer<br/>(Trilingual: EN, KN, TE)"]
        Postgres[(PostgreSQL Relational Store<br/>Partitioned Telemetry & Audit Logs)]
        
        Ingress --> AuthService
        Ingress --> RulesEngine
        AuthService --> RBAC
        RulesEngine --> XAI
        WeatherService --> RulesEngine
        RulesEngine --> Postgres
        AuthService --> Postgres
    end

    subgraph ClientLayer["3. Unified Client Interfaces"]
        Landing["Public Landing Page (/ or /home)<br/>• Interactive Feature Tours<br/>• Live Global Sericulture Metrics"]
        UnifiedAuth["Unified Auth Gateway (/login)<br/>• Single Sign-In for All Roles<br/>• Role-Based Auto-Redirection"]
        FarmerReg["Farmer Registration (/register)<br/>• Self-Service Onboarding<br/>• Breed & DFL Capacity Profiling"]
        EnterpriseWeb["Enterprise Operations Portal (/admin)<br/>• 21 Dedicated Operations Modules<br/>• Tab-Isolated Concurrent Sessions"]
        MobileApp["Farmer Mobile App (Flutter)<br/>• Live Microclimate Metric Grid<br/>• PWM Dimmer & Offline Fail-Safe"]
    end

    ESP32 <-->|HTTP / MQTT / TLS| Ingress
    BackendLayer <-->|JWT + X-Session-ID + X-Tab-ID| ClientLayer
```

---

## 🚀 Key Platform Capabilities

### 1. Unified Authentication Gateway (`/login`)
- **Single Public Portal:** All users, regardless of organization hierarchy or role, authenticate through a single, official entry point at `/login`.
- **Role-Authoritative Redirection:** The backend evaluates verified identity and access permissions to automatically route the user to their designated workspace:
  - **Super Admin / Platform Admin** $\rightarrow$ Platform Overview & Audit Trail (`overview`)
  - **Company Admin** $\rightarrow$ Enterprise Organizations & Subscriptions (`organizations`)
  - **CEO / Executive** $\rightarrow$ Strategic Analytics & Cocoon Yield Trends (`analytics`)
  - **HR Director** $\rightarrow$ Employee Directory & Department Hierarchy (`employees`)
  - **Operations Manager** $\rightarrow$ Fleet Rearing Sheds & Batches (`sheds`)
  - **Field Technician** $\rightarrow$ Gateway Provisioning & Calibration (`installations`)
  - **Sales Executive** $\rightarrow$ Hardware Catalog & Enterprise Invoicing (`orders`)
  - **Support Specialist** $\rightarrow$ Farmer Resolution & Ticket SLAs (`support`)
  - **Scientific Analyst** $\rightarrow$ Environmental Correlation & Research (`research`)
  - **Registered Farmer** $\rightarrow$ Real-Time Shed Telemetry & Controls (`live-monitoring`)

### 2. Farmer-Only Self-Service Registration (`/register`)
- **Dedicated Route:** Publicly accessible at `/register`.
- **Sericulture Domain Profiling:** Captures essential farm metadata including Silkworm Breed (Bivoltine White FC1 x FC2, Double Hybrid, Multivoltine PM x CSR2), Batch DFL (Disease-Free Layings) Capacity, Shed Name, and Silk Belt Region (28 Indian and global sericulture belts).
- **Anti-Privilege Escalation:** Backend strictly enforces the `farmer` role, ignoring and rejecting any client attempts to elevate privileges. Automatically provisions rearing shed assignments.

### 3. Per-Tab Session Isolation (Concurrent Multi-Account Support)
- **Problem Solved:** Browsers share cookies and `localStorage` across all open tabs, which historically forced users into a single identity and caused silent session overwrites.
- **Setu Isolation Engine:**
  - Each browser tab generates and retains an unguessable UUID `X-Tab-ID` stored exclusively in `window.sessionStorage`.
  - Backend issues an authoritative `session_id` recorded in `user_sessions` and bound inside the JWT token.
  - Transparent fetch interceptor decorates every HTTP request with `X-Tab-ID` and `X-Session-ID`.
  - Enables **simultaneous concurrent logins** in the same browser profile (e.g., Tab 1: Super Admin, Tab 2: Farmer A, Tab 3: Farmer B) with zero cross-tab pollution, state leakage, or unexpected logouts.

### 4. Growth-Stage Aware Microclimate Control
Automatically enforces environmental setpoints grounded in Central Sericultural Research & Training Institute (CSRTI) guidelines:
- **Instar 1 (Chawki Stage 1):** 27–28°C, 85–90% RH
- **Instar 2 (Chawki Stage 2):** 26–27°C, 80–85% RH
- **Instar 3 (Late Stage 3):** 25–26°C, 75–80% RH
- **Instar 4 (Late Stage 4):** 24–25°C, 70–75% RH
- **Instar 5 & Cocooning:** 23–24°C, 65–70% RH

### 5. Automated IAQ ($CO_2$) & Photoperiod Lighting
- **Air Quality & Ventilation:** Continuously samples indoor air freshness via MQ-135. Triggers cross-ventilation exhaust fans when air quality falls below 80% ($CO_2 > 1000\text{ ppm}$), preventing metabolic asphyxiation in dense larval trays.
- **Circadian Photoperiod Regulation:**
  - **Day Activity (06:00–22:00):** Maintains uniform 15–30 Lux illumination via PWM modulation.
  - **Night Rest (22:00–06:00):** Ensures complete resting darkness (< 5 Lux, 0% PWM).
  - **Mounting Stage:** Maintains semi-darkness (~10 Lux) to prevent larvae from wandering off cocooning netrikes.

### 6. Zero Static Data Guarantee
All 21 enterprise frontend modules, telemetry graphs, KPIs, orders, and tickets render 100% authoritative database queries via PostgreSQL. Zero fake or static client-side fallback data.

---

## 📁 Repository Structure

```
setu/
├── admin_web/                  # Enterprise Web Application (Vanilla HTML5/CSS3/ES6)
│   ├── index.html              # Unified Login & Enterprise Portal UI
│   ├── register.html           # Farmer Self-Service Registration UI
│   ├── app.js                  # Frontend Controller, RBAC & Multi-Tab Isolation
│   ├── style.css               # Bespoke Sericulture Design System Stylesheet
│   └── table-manager.js        # Dynamic Data Grid & Pagination Manager
│
├── landing/                    # Public Landing Website
│   ├── index.html              # Product Overview, Features & Value Proposition
│   ├── app.js                  # Public Landing Interactions & Live Demos
│   └── style.css               # Marketing Site Design System
│
├── backend/                    # Core Python FastAPI Application
│   ├── app/
│   │   ├── core/               # JWT Security, Session Tokens & Settings
│   │   ├── models/             # Pydantic Request/Response Schemas
│   │   ├── routers/            # Modular API Routers:
│   │   │   ├── auth.py         # Login, Register, Logout & Multi-Tab Sessions
│   │   │   ├── admin.py        # System Administration & Threshold Configuration
│   │   │   ├── departments.py  # Enterprise Department Hierarchy
│   │   │   ├── employees.py    # Employee Onboarding & Activation Tokens
│   │   │   ├── enterprise_platform.py # 21 Operations Modules (Products, Orders, Tickets)
│   │   │   ├── roles_permissions.py   # RBAC Matrix & Privilege Enforcement
│   │   │   ├── sheds.py        # Sheds Fleet, Batches & Telemetry Queries
│   │   │   ├── telemetry.py    # Ingestion & Relay Automation
│   │   │   ├── control.py      # Actuator Command Dispatch & BOLA Verification
│   │   │   ├── ai.py           # Multilingual Explainable AI (EN, KN, TE)
│   │   │   └── voice.py        # Text-to-Speech Voice Guidance Audio
│   │   ├── services/           # Domain Business Logic:
│   │   │   ├── db_service.py   # PostgreSQL Connection Pools & Tables
│   │   │   ├── org_employee_db.py # Enterprise Organization & Employee Logic
│   │   │   └── enterprise_db.py   # Hardware Inventory, Orders & Support
│   │   └── main.py             # ASGI Application Entrypoint & Middleware
│   ├── tests/                  # Automated Pytest Suite (103 Tests, 100% Passing)
│   │   ├── test_unified_auth.py       # Login, Registration & Escalation Defense
│   │   ├── test_multi_tab_sessions.py # Per-Tab Session Isolation Suite
│   │   ├── test_owasp_hardening.py    # ASVS Level 2 & Top 10 Hardening
│   │   ├── test_org_employee_rbac.py  # Employee Activation & Hierarchy
│   │   ├── test_enterprise_platform.py# Operational Endpoints & Inventory
│   │   ├── test_public_landing.py     # Public Route Serving & Headers
│   │   └── test_api.py                # Core Telemetry & Biological Rules
│   ├── requirements.txt        # Backend Python Dependencies
│   └── pytest.ini              # Test Runner Configuration
│
├── mobile/                     # Cross-Platform Native Mobile Application (Flutter)
│   ├── lib/
│   │   ├── l10n/               # Localization Bundles (English, Kannada, Telugu)
│   │   ├── screens/            # Live Monitoring, Actuator Controls & Advisories
│   │   └── services/           # Secure Storage & WebSocket Telemetry
│   └── pubspec.yaml            # Flutter Dependencies
│
├── docs/                       # Comprehensive Architecture & Compliance Specifications
│   ├── architecture.md         # Distributed Scale-Out Architecture
│   ├── security/               # OWASP Top 10:2025, ASVS 5.0, Incident Runbooks
│   └── performance/            # Load Testing Methodology & Baselines
│
├── api_documentation.md        # Complete REST API Reference Manual
├── database_schema.md          # Relational Entity-Relationship Dictionary
└── deployment.md               # Production Cloud Deployment Guide
```

---

## 🛠️ Getting Started

### 1. Prerequisites

- **Python**: 3.12 or 3.13
- **PostgreSQL**: 14+ or 15+ (Listening on `localhost:5432`)
- **Flutter SDK**: 3.x+ (For mobile app development)
- **Node.js**: Optional (For static syntax verification)

---

### 2. Database Initialization

Setu uses PostgreSQL with dynamic schema migrations on startup.

1. **Create the database in PostgreSQL**:
   ```sql
   CREATE USER setu_user WITH PASSWORD 'setu_password';
   CREATE DATABASE setu OWNER setu_user;
   GRANT ALL PRIVILEGES ON DATABASE setu TO setu_user;
   ```

2. **Configure Environment Variables**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   cp .env.example backend/.env
   ```
   Default local connection string:
   ```env
   DATABASE_URL="postgresql://setu_user:setu_password@127.0.0.1:5432/setu"
   SETU_SECRET_KEY="setu-secure-production-master-secret-key-2026"
   INITIAL_ADMIN_PASSWORD="admin"
   ```

---

### 3. Backend Setup & Startup

1. **Install Python dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

2. **Start the FastAPI Server**:
   ```bash
   cd backend
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

3. **Verify Server Health**:
   - **Public Landing Page**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
   - **Unified Login Gateway**: [http://127.0.0.1:8000/login](http://127.0.0.1:8000/login)
   - **Farmer Registration Page**: [http://127.0.0.1:8000/register](http://127.0.0.1:8000/register)
   - **Enterprise Operations Console**: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)
   - **Interactive API Documentation (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### 4. Running the Automated Test Suite

Setu includes a 103-test verification suite covering authentication, multi-tab isolation, enterprise workflows, and OWASP hardening:

```bash
python -m pytest backend/tests/ -v
```

Expected output:
```
====================== 103 passed, 13 warnings in ~35s ======================
```

To run individual test suites:
```bash
# Test Unified Login & Farmer Registration
python -m pytest backend/tests/test_unified_auth.py -v

# Test Multi-Tab Concurrent Session Isolation
python -m pytest backend/tests/test_multi_tab_sessions.py -v

# Test OWASP Top 10 & ASVS Level 2 Hardening
python -m pytest backend/tests/test_owasp_hardening.py -v

# Test 10-Role RBAC & Employee Onboarding
python -m pytest backend/tests/test_org_employee_rbac.py -v
```

---

## 🔐 Default Administrative Credentials

The database pre-seeds an initial administrative identity for first-time environment setup:

- **Username / Identifier:** `admin` (or `+91 98450 99999`)
- **Default Initial Password:** `admin` *(Configurable via `INITIAL_ADMIN_PASSWORD` in `.env`)*
- **Primary Persona:** `superadmin` (Authoritative platform administration access)

*Note: For self-service farmer testing, register any new account at [http://127.0.0.1:8000/register](http://127.0.0.1:8000/register).*

---

## 🛡️ Security & Compliance Standards

- **OWASP Top 10:2025 Compliance**: 
  - Strict Broken Object Level Authorization (BOLA/IDOR) verification on all shed actuator controls and orders.
  - Transparent payload size limiting (413 Payload Too Large) mitigating denial-of-service.
  - Strict CORS origin regex enforcement restricting untrusted cross-origin domains.
- **OWASP ASVS 5.0 (Level 2)**:
  - Cryptographically secure session management (`user_sessions` table with revocation tracking).
  - Immediate token revocation blacklist (`revoked_tokens` table) upon tab logout.
  - PBKDF2 password hashing with variable salts and minimum 8-character complexity.
- **Hardware Fail-Safe Interlocks**: Software-enforced mutual exclusion prevents cooling and heating circuits from running simultaneously under any circumstance.

---

## 📄 License

This software is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
