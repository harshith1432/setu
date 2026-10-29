# SeriCare PostgreSQL Rollback & Disaster Recovery Procedure

This document provides step-by-step instructions to safely revert SeriCare from Firebase Cloud Firestore to PostgreSQL without data loss or downtime.

---

## 1. Dual-Sync Architecture Overview

During the migration period, SeriCare runs in a **Dual-Sync** architecture:
- **Telemetry Service (`backend/app/services/telemetry_service.py`):** Every sensor reading from IoT gateways or field devices is saved into PostgreSQL table `shed_telemetry` and asynchronously mirrored to Firestore collection `shed_telemetry`.
- **Commerce & Orders:** Orders placed via mobile or web are registered in both `orders` table (PostgreSQL) and `orders` collection (Firestore).
- **PostgreSQL as Source of Truth / Hot Backup:** The PostgreSQL relational database remains online, continuously receiving schema updates and keeping full historical fidelity.

---

## 2. Instant Failover to PostgreSQL (Zero Code Changes)

If Firebase Cloud Firestore experiences an outage, quota exhaustion, or operational issue:

### Step 1: Set Database Provider Variable
In your deployment environment (Render, local server, or container):
```bash
SERICARE_DB_BACKEND=postgres
SERICARE_FIRESTORE_ENABLED=false
```

### Step 2: Restart the Backend Service
The backend's `FirestoreService` gracefully handles disconnections or disabled flags. If `SERICARE_FIRESTORE_ENABLED=false`, all reads and writes route directly to PostgreSQL via `db_service.get_db_cursor()`.

### Step 3: Mobile & Web Automatic Fallback
- **Mobile (`mobile/lib/services/firestore_service.dart`):** Built-in defensive fallback automatically delegates to `ApiService` (REST backend over PostgreSQL) if Firestore is unreachable or returns permissions errors.
- **Web (`admin_web/firebase-db.js`):** If Firestore is unreachable, `admin_web/app.js` falls back to REST `/api/v1` endpoints served by the Python backend.

---

## 3. Reverse Synchronization: Export Firestore to PostgreSQL

If data was created in Firestore during an active session and needs to be synchronized back into PostgreSQL:

### Script: `scripts/sync_firestore_to_postgres.py`
Run the reverse sync utility:
```bash
python scripts/sync_firestore_to_postgres.py --since="2026-10-29T00:00:00Z"
```

This utility performs:
1. Queries Firestore collections (`orders`, `device_commands`, `shed_telemetry`, `audit_logs`) for documents with `created_at` or `timestamp` greater than `--since`.
2. Matches foreign keys to existing PostgreSQL records (`user_id`, `shed_id`).
3. Executes `ON CONFLICT (id) DO UPDATE` or `DO NOTHING` to ensure idempotence.
4. Generates a reconciliation report comparing row counts between Firestore and PostgreSQL.

---

## 4. Rollback Verification Checklist

Before opening the platform back up to full farmer traffic after a rollback:

- [ ] **Health Endpoint:** Verify `GET /health` or `GET /api/v1/health` returns `status: "healthy"` and `database: "connected"`.
- [ ] **Telemetry Ingestion:** Post a sample telemetry payload via `POST /api/v1/telemetry` and verify it appears in `SELECT * FROM shed_telemetry ORDER BY timestamp DESC LIMIT 1;`.
- [ ] **Farmer Mobile Login:** Log in via Mobile App using existing phone or Google Auth and verify the dashboard loads shed metrics.
- [ ] **Orders & Catalog:** Open Products screen and verify prices and orders are displayed correctly from PostgreSQL.
- [ ] **Audit Trail:** Check `audit_logs` table has logged the failover event.
