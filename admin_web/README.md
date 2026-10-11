# Setu Super Admin Command Portal

The Super Admin Command Portal provides centralized monitoring, control, and management of silkworm rearing sheds, registered farmers, IoT sensors, and environmental actuators across global sericulture sheds.

---

## Live Deployment

- **Production Portal (Vercel)**: [https://setu-adminweb.vercel.app](https://setu-adminweb.vercel.app)
- **Connected Cloud Backend (Render)**: [https://setu-8vh9.onrender.com/api/v1](https://setu-8vh9.onrender.com/api/v1)

---

## Key Features

1. **Secure Admin Authentication**:
   - JWT token-based authentication via the FastAPI backend (`/api/v1/auth/login`).
   - Role-based authorization (`superadmin` access).
   - Password visibility toggle (eye button) for secure and accessible login.

2. **Cluster Health & Real-time Metrics**:
   - Total registered farmers, active rearing sheds, healthy vs warning shed counters.
   - Connected ESP32 nodes and operational status.

3. **Live Shed Environment Monitoring (4-Metric Gauges)**:
   - Live temperature, relative humidity, outside ambient conditions (via Open-Meteo worldwide), and growth stage indicators.
   - **Air Quality & CO₂ dial**: Shows fresh air percentage (`>=80%` healthy zone; alerts when exhaust fan is engaged).
   - **Light Intensity dial**: Shows real-time Lux levels and active photoperiod mode (Day, Night Rest, Spinning).
   - Automatic evaluation against stage-specific thresholds (Instars 1–5).

4. **Farmer & Batch Management**:
   - Register and manage farmers, shed locations worldwide, batch identifiers, and silkworm breed types.
   - Multilingual preferences (English, Kannada, Telugu).
   - Shows users registered directly or authenticated via Google Auth.

5. **Manual Actuator Overrides & Interlocks**:
   - Manual override controls for cooling, heating, ventilation, and misting systems.
   - **Dimmable Photoperiod Bulb Control**: Live PWM indicator (0–100%) and override toggles.
   - Built-in hardware safety interlocks ensuring mutual exclusion between heating and cooling elements.

6. **Audit Trails & CSV Reporting**:
   - Tamper-evident logging of actuator commands and environmental state changes.
   - One-click CSV export of historical sensor telemetry including temperature, humidity, air quality, light lux, and relay states.

---

## Architecture & Integration

- **Frontend Tech**: Vanilla HTML5, Modern CSS3 (CSS Variables, Flexbox/Grid), JavaScript (ES6+), and Lucide Icons.
- **Backend Host**: Mounted directly by the FastAPI backend at `/admin` (via `FastAPI.mount()`), or can be hosted on any static HTTP web server (e.g., Nginx, Caddy, Vercel).
- **Default Credentials** (Initial Seed):
  - **Username**: `admin`
  - **Password**: `admin`

---

## How to Run

### Option 1: Via the FastAPI Backend (Recommended)
When the backend is running, the portal is automatically served at:
```
http://localhost:8000/admin
```

### Option 2: Standalone Static Server
You can also serve the portal independently using Python or any static file server:
```bash
cd admin_web
python -m http.server 3000
```
Open your browser at `http://localhost:3000`.
