# SeriCare Super Admin Command Portal

The Super Admin Command Portal provides centralized monitoring, control, and management of silkworm rearing sheds, registered farmers, IoT sensors, and environmental actuators across the Mulbagal sericulture cluster.

---

## Key Features

1. **Secure Admin Authentication**:
   - JWT token-based authentication via the FastAPI backend (`/api/v1/auth/login`).
   - Role-based authorization (`superadmin` access).

2. **Cluster Health & Real-time Metrics**:
   - Total registered farmers, active rearing sheds, healthy vs warning shed counters.
   - Connected ESP32 nodes and operational status.

3. **Live Shed Environment Monitoring**:
   - Live temperature, relative humidity, outside ambient conditions, and growth stage indicators.
   - Automatic evaluation against stage-specific thresholds (Instars 1–5).

4. **Farmer & Batch Management**:
   - Register and manage farmers, shed locations, batch identifiers, and silkworm breed types.
   - Multilingual preferences (English, Kannada, Telugu).

5. **Manual Actuator Overrides & Interlocks**:
   - Manual override control for cooling, heating, ventilation, and misting systems.
   - Built-in hardware safety interlocks ensuring mutual exclusion between heating and cooling elements.

6. **Audit Trails & CSV Reporting**:
   - Tamper-evident logging of actuator commands and environmental state changes.
   - One-click CSV export of historical sensor telemetry.

---

## Architecture & Integration

- **Frontend Tech**: Vanilla HTML5, Modern CSS3 (CSS Variables, Flexbox/Grid), JavaScript (ES6+), and Lucide Icons.
- **Backend Host**: Mounted directly by the FastAPI backend at `/admin` (via `FastAPI.mount()`), or can be hosted on any static HTTP web server (e.g., Nginx, Caddy, Vercel).
- **Default Credentials** (Initial Seed):
  - **Username**: `superadmin`
  - **Password**: `adminsecure2026`

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
