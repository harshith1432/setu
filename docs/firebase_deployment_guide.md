# SeriCare Firebase Cloud Firestore Deployment & Operations Guide

This guide details the deployment, configuration, security rules enforcement, and maintenance procedures for the Firebase Cloud Firestore infrastructure of SeriCare.

---

## 1. Firebase Project Overview

- **Firebase Project ID:** `setu-a767c`
- **Region:** `asia-south1` (Mumbai) / Multi-region `nam5`
- **Supported Platforms:**
  - Android (`mobile/android/app/google-services.json`)
  - Web (`admin_web/firebase-db.js`, `mobile/web`)
  - Windows (`mobile/windows/`)

---

## 2. Deploying Security Rules & Composite Indexes

SeriCare defines fine-grained Role-Based Access Control (RBAC) in `firestore.rules` and composite query indexes in `firestore.indexes.json`.

### Prerequisites
Install the Firebase CLI:
```bash
npm install -g firebase-tools
firebase login
```

### Deploy Rules and Indexes
From the project root:
```bash
# Verify selected project
firebase use setu-a767c

# Deploy Firestore Security Rules
firebase deploy --only firestore:rules

# Deploy Firestore Indexes
firebase deploy --only firestore:indexes
```

---

## 3. Backend Service Account Setup

To allow privileged server operations (e.g. background telemetry processing, admin reports, and automated maintenance) from the Python backend:

### Step 1: Generate Service Account Key
1. Go to the [Firebase Console](https://console.firebase.google.com/project/setu-a767c/settings/serviceaccounts/adminsdk).
2. Click **Generate New Private Key**.
3. Save the JSON file securely (e.g. `credentials/firebase-service-account.json`).
4. **Never commit this JSON file to version control.** (Included in `.gitignore`).

### Step 2: Configure Environment Variable
In your `.env` or deployment settings:
```bash
FIREBASE_SERVICE_ACCOUNT_KEY="credentials/firebase-service-account.json"
# Or provide the JSON string directly:
# FIREBASE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"setu-a767c",...}'
```

The backend singleton (`backend/app/services/firestore_service.py`) automatically discovers and initializes the Admin SDK when either variable is present, or falls back to default application credentials.

---

## 4. Running the PostgreSQL to Firestore Migration

The migration utility `scripts/migrate_postgres_to_firestore.py` reads from PostgreSQL and populates Firestore collections in transactional batches.

### Step 1: Run Dry-Run Verification
Extracts and converts all records, outputting clean JSON document dumps and verifying foreign-key integrity without writing to Firestore:
```bash
python scripts/migrate_postgres_to_firestore.py --dry-run
```

### Step 2: Execute Live Migration
Once the service account key is configured:
```bash
python scripts/migrate_postgres_to_firestore.py --batch-size=500
```

### Step 3: Verify Document Counts
Compare the generated migration report `docs/firestore_migration_report.md` against the Firestore dashboard in Firebase Console.

---

## 5. Security Rules Architecture

The rules in `firestore.rules` enforce:
- **`users`:** Users can read and write only their own profile; administrators can inspect user lists.
- **`shed_telemetry`:** Readable by authenticated farmers owning the shed; writeable by authenticated IoT gateway devices and administrators.
- **`products`:** Public read access for the catalog; writeable only by technicians and administrators.
- **`orders`:** Farmers can create and view their own orders; admins can manage order statuses.
- **`device_commands`:** Farmers can issue commands for their own sheds; gateways can poll pending commands; history is preserved.
- **`audit_logs`:** Append-only (create allowed); updates and deletes are permanently rejected.

---

## 6. Monitoring and Operations

- **Firestore Console:** Monitor document reads/writes and latency in the Firebase Console.
- **Composite Indexes:** Check build status of composite indexes under **Firestore > Indexes**.
- **Backend Logs:** Check Python server logs for `[FirestoreService]` entries confirming live synchronization.
