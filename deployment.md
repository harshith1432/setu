# SeriCare / Setu Deployment & Operations Runbook

This guide covers deployment procedures for local development, Docker Compose, and production environments.

---

## 1. Prerequisites

- **Python**: 3.12+ / 3.13+
- **PostgreSQL**: 15+ / 18+
- **Nginx** (for reverse proxy & TLS termination)
- **Node.js**: (optional, for asset tooling)
- **Docker & Docker Compose**: (for containerized deployments)

---

## 2. Local Development Setup

### 2.1 Database Setup
Ensure PostgreSQL is running locally on port 5432 with database `setu`:
```bash
# Verify PostgreSQL connectivity
psql -U postgres -h 127.0.0.1 -c "CREATE DATABASE setu;"
```

### 2.2 Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Ensure `DATABASE_URL` matches your local credentials:
```env
DATABASE_URL="postgresql://postgres:your_password@127.0.0.1:5432/setu"
SETU_SECRET_KEY="your-secure-random-key"
```

### 2.3 Python Dependencies
Install backend dependencies:
```bash
pip install -r backend/requirements.txt
```

### 2.4 Automated Database Schema Verification & Table Creation
The software automatically checks the database every time it boots:
- If all tables already exist, it verifies the schema and proceeds immediately.
- If tables are missing (e.g. fresh database or new deployment), it automatically creates all 36+ required tables, indexes, and baseline seeds before starting the web server.

You can also run the verification manually at any time or as a deployment release command:
```bash
python backend/init_db.py
```

### 2.5 Run Development Server
```bash
# Start backend on port 8000 (automated DB check runs on startup)
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

Access portals:
- **Enterprise Web Dashboard**: `http://localhost:8000/admin`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **Health Probe**: `http://localhost:8000/health`
- **Readiness Probe**: `http://localhost:8000/ready`

---

## 3. Docker Compose Production Deployment

The repository includes a production multi-service configuration in `docker-compose.prod.yml`:
- **FastAPI Backend Cluster**: High-concurrency uvicorn workers.
- **PostgreSQL**: Partitioned database with persistence volume.
- **Nginx Reverse Proxy**: TLS termination, rate-limiting, static asset caching.
- **Prometheus & Grafana**: System & telemetry monitoring.

### 3.1 Launch Stack
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 3.2 Health Check Verification
```bash
curl -f http://localhost:8000/health
curl -f http://localhost:8000/ready
```

---

## 4. Default Seed Administrative Accounts

| Username | Password | Role | Permitted Scope |
| :--- | :--- | :--- | :--- |
| `admin` | `admin` | `superadmin` | Full platform administration |
| `ceo` | `ceo2026` | `ceo` | Executive analytics, reports, revenue |
| `tech_kiran` | `tech2026` | `technician` | Installations, sensor calibration |
| `support_priya` | `support2026` | `support` | Customer support helpdesk |
| `sales_anand` | `sales2026` | `sales` | Products, orders, billing |
| `ramesh_farmer` | `setu2026` | `farmer` | Own shed telemetry & orders |

---

## 5. Production Hardening Checklist

- [x] Rotate `SETU_SECRET_KEY` and database passwords in production `.env`.
- [x] Configure strict CORS with allowed production domains.
- [x] Enforce TLS/HTTPS using Nginx or Cloudflare.
- [x] Secure edge IoT endpoints using `X-Device-Key` or mTLS client certificates.
- [x] Configure automated daily PostgreSQL backups (`pg_dump`).
- [x] Monitor rate limits and audit logs under `/api/v1/platform/audit-logs`.
