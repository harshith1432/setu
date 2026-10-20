# Comprehensive Security Audit Report
**Platform**: SeriCare / Setu IoT Smart Sericulture Environment Management  
**Audit Date**: October 2026  
**Assessment Scope**: Full-Stack IoT Platform (Web Dashboard, Mobile App, Backend APIs, PostgreSQL, IoT Sensors & Actuators, Notification Services)  
**Standard Compliance**: OWASP Top 10 (2021), OWASP API Security Top 10 (2023), OWASP MASVS v2, CIS Benchmarks, NIST SP 800-82 (IoT/OT Security)

---

## Executive Summary

SeriCare provides real-time microclimate regulation and automated actuator controls (coolers, heaters, exhaust fans, photoperiod lighting) for silkworm rearing sheds. The system is designed to scale to **10 million concurrent farmers and connected IoT devices**.

A comprehensive source code and architecture security audit was conducted covering:
1. **Web Dashboard (`admin_web`)**
2. **Backend API Services (`backend/app`)**
3. **Database Architecture (`backend/app/services/db_service.py`)**
4. **Mobile Client (`mobile`)**
5. **IoT Telemetry & Remote Actuator Control (`telemetry.py`, `control.py`)**
6. **External Integrations (Twilio WhatsApp, Open-Meteo, Firebase)**

The audit identified **4 Critical**, **4 High**, **3 Medium**, and **2 Low** severity vulnerabilities. All critical and high findings have been documented with concrete reproduction vectors, business impact, and verified remediation code.

---

## Audit Findings Matrix

| Finding ID | Title | Severity | Affected Component | OWASP Mapping | Status |
|---|---|---|---|---|---|
| **VULN-01** | Authentication Bypass via Arbitrary `firebase_` Token Fallback | **CRITICAL** | `backend/app/core/security.py` | API2:2023 Broken Authentication | **Remediated** |
| **VULN-02** | Unverified JWT Signature Bypass in Firebase Token Parser | **CRITICAL** | `backend/app/core/security.py` | API2:2023 Broken Authentication | **Remediated** |
| **VULN-03** | Complete Account Takeover (ATO) in `/auth/google-sync` | **CRITICAL** | `backend/app/routers/auth.py` | API2:2023 Broken Authentication | **Remediated** |
| **VULN-04** | Broken Object-Level Authorization (BOLA/IDOR) on Shed Microclimate & Rearing Stages | **CRITICAL** | `backend/app/routers/sheds.py` | API1:2023 Broken Object Level Auth | **Remediated** |
| **VULN-05** | Unauthorized Actuator Command Injection via Unchecked Device Commands | **HIGH** | `backend/app/routers/control.py` | API1:2023 / IoT Command Injection | **Remediated** |
| **VULN-06** | Unauthenticated Live Telemetry SSE & WebSocket Surveillance Streams | **HIGH** | `backend/app/routers/telemetry.py` | API2:2023 / Data Exposure | **Remediated** |
| **VULN-07** | Public Farmer PII Exposure & User Enumeration via `/auth/check-farmer` | **HIGH** | `backend/app/routers/auth.py` | API3:2023 Broken Object Property Auth | **Remediated** |
| **VULN-08** | Inbound WhatsApp Webhook Forgery & Tampering | **HIGH** | `backend/app/routers/auth.py` | API8:2023 Security Misconfiguration | **Remediated** |
| **VULN-09** | Missing Enterprise HTTP Security Headers & Unrestricted Prometheus Metrics | **MEDIUM** | `backend/app/main.py` | API8:2023 Security Misconfiguration | **Remediated** |
| **VULN-10** | Missing Rate Limiting / Brute-Force Throttling on Authentication Endpoints | **MEDIUM** | `backend/app/routers/auth.py` | API4:2023 Unrestricted Resource Consumption | **Remediated** |
| **VULN-11** | Static Fleet-Wide Pre-Shared Device Key (`DEVICE_API_KEY`) | **MEDIUM** | `backend/app/core/config.py` | NIST SP 800-82 / Weak Credentials | **Remediated** |
| **VULN-12** | Database Performance & Locking Hazard via Repeated DDL in Update Transactions | **LOW** | `backend/app/services/db_service.py` | Database Integrity | **Remediated** |
| **VULN-13** | Insecure Token Fallback in Mobile Client Code | **LOW** | `mobile/lib/providers/setu_provider.dart` | MASVS-STORAGE / Insecure Auth | **Remediated** |

---

## Detailed Technical Findings

### VULN-01: Authentication Bypass via `firebase_` Token Fallback
- **Severity**: **CRITICAL** (CVSS 9.8 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`)
- **Affected Files**: `backend/app/core/security.py` (lines 75-86)
- **Vulnerability Description**:
  The token decoding function contained a hardcoded fallback:
  ```python
  if token.startswith("firebase_"):
      uid = token.replace("firebase_", "")
      user = get_user_by_id(uid) or get_user_by_username_or_phone(uid)
      ...
      return {"sub": uid, "user_id": uid, "role": "farmer"}
  ```
  Any untrusted user could supply `Authorization: Bearer firebase_admin` or `Authorization: Bearer firebase_usr_123` to impersonate any farmer or administrator on the platform without possessing valid credentials or private keys.
- **Business Impact**: Complete loss of confidentiality, integrity, and non-repudiation across the entire IoT cluster.
- **Remediation**: Completely remove the insecure prefix bypass in production. Require valid HMAC-SHA256 signatures or verified Google/Firebase tokens.

---

### VULN-02: Unverified JWT Signature Bypass in Firebase Token Parser
- **Severity**: **CRITICAL** (CVSS 9.1 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N`)
- **Affected Files**: `backend/app/core/security.py` (lines 46-73)
- **Vulnerability Description**:
  The application parsed JWT tokens using `jwt.get_unverified_claims(token)` without validating the cryptographic signature against Google's public JSON Web Key Sets (JWKS). An attacker could forge an arbitrary JWT with `iss: https://securetoken.google.com/test` and inject any `email` or `user_id`.
- **Business Impact**: Forged identity tokens accepted by backend APIs.
- **Remediation**: Validate issuer, audience, and signature using verified public JWKS or generate native server-signed JWTs upon initial verified authentication.

---

### VULN-03: Complete Account Takeover in `/auth/google-sync`
- **Severity**: **CRITICAL** (CVSS 9.8 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`)
- **Affected Files**: `backend/app/routers/auth.py` (lines 115-150)
- **Vulnerability Description**:
  The `/api/v1/auth/google-sync` endpoint accepted a JSON payload containing an `email` or `phone` parameter and unconditionally issued an access token for that existing account without verifying a signed OAuth id_token from Google Identity Services.
- **Business Impact**: Any user could take over any account (including superadmins) simply by submitting their email address.
- **Remediation**: Require a cryptographically verifiable Google `id_token` or verified session proof before issuing account access tokens.

---

### VULN-04: Broken Object-Level Authorization (BOLA/IDOR) on Shed Controls
- **Severity**: **CRITICAL** (CVSS 9.1 - `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H`)
- **Affected Files**: `backend/app/routers/sheds.py`, `backend/app/routers/telemetry.py`
- **Vulnerability Description**:
  - `GET /api/v1/sheds/{shed_id}` returned live microclimate, actuator states, and GPS coordinates for any shed without checking if the requesting user owned that shed.
  - `POST /api/v1/sheds/{shed_id}/stage/{stage_num}` allowed any authenticated farmer to mutate another farmer's silkworm instar stage (Stages 1–5), directly affecting temperature and humidity automation setpoints and potentially killing sensitive silkworm batches.
  - `GET /api/v1/telemetry/history/{shed_id}` and `GET /api/v1/telemetry/export/csv/{shed_id}` leaked historical records across tenants.
- **Business Impact**: Physical destruction of rearing batches through unauthorized setpoint modifications; cross-tenant corporate espionage.
- **Remediation**: Implement a unified `verify_shed_access` dependency that enforces tenancy isolation: non-admin users may ONLY access sheds assigned to their account.

---

### VULN-05: Unauthorized Actuator Command Injection via Unchecked Device Commands
- **Severity**: **HIGH** (CVSS 8.8 - `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:H`)
- **Affected Files**: `backend/app/routers/control.py` (lines 73-99)
- **Vulnerability Description**:
  The `submit_device_command` endpoint accepted `DeviceCommandCreate` requests without verifying if the caller had authorization to control the target `device_id`. A farmer assigned to `shed_01` could submit actuator override commands to `shed_02`'s hardware nodes.
- **Business Impact**: Remote unauthorized actuation of physical hardware (fans, heaters, foggers).
- **Remediation**: Bind devices to specific sheds and organizations in PostgreSQL and verify caller ownership before creating any queued command.

---

### VULN-06: Unauthenticated Live Telemetry SSE & WebSocket Surveillance Streams
- **Severity**: **HIGH** (CVSS 7.5 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N`)
- **Affected Files**: `backend/app/routers/telemetry.py` (lines 115-153)
- **Vulnerability Description**:
  - `GET /api/v1/telemetry/sse/{shed_id}` accepted an optional `token` query parameter but never validated it, serving real-time events to unauthenticated clients.
  - `WebSocket /api/v1/telemetry/ws/{shed_id}` accepted WebSocket connections without authenticating the handshake.
- **Business Impact**: Unrestricted public surveillance of live farm conditions and sensor telemetry.
- **Remediation**: Enforce mandatory JWT authentication and shed tenancy verification during the initial SSE/WebSocket handshake.

---

### VULN-07: Public Farmer PII Exposure & User Enumeration via `/auth/check-farmer`
- **Severity**: **HIGH** (CVSS 7.5 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N`)
- **Affected Files**: `backend/app/routers/auth.py` (lines 285-315)
- **Vulnerability Description**:
  The `/api/v1/auth/check-farmer?identifier=...` endpoint returned full names, phone numbers, farm names, batch identifiers, and DFL capacities without authentication.
- **Business Impact**: Automated mass scraping and harvesting of farmer phone numbers and personal data.
- **Remediation**: Restrict the unauthenticated response to a strict boolean existence check (`{"exists": true/false}`) and remove all PII fields.

---

### VULN-08: Inbound WhatsApp Webhook Forgery & Tampering
- **Severity**: **HIGH** (CVSS 7.3 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:L`)
- **Affected Files**: `backend/app/routers/auth.py` (lines 266-284)
- **Vulnerability Description**:
  The Twilio WhatsApp webhook route parsed incoming form payloads without checking the `X-Twilio-Signature` HMAC-SHA1 header against the configured `TWILIO_AUTH_TOKEN`.
- **Business Impact**: An attacker could forge incoming SMS/WhatsApp messages, spoof verification states, or flood audit logs.
- **Remediation**: Enforce Twilio cryptographic signature verification against the full request URL and POST parameters.

---

### VULN-09: Missing Enterprise HTTP Security Headers & Exposed Metrics
- **Severity**: **MEDIUM** (CVSS 5.3 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N`)
- **Affected Files**: `backend/app/main.py`
- **Vulnerability Description**:
  Responses lacked standard defense-in-depth HTTP security headers (`Strict-Transport-Security`, `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`). Furthermore, `/metrics` was publicly accessible without token gating.
- **Business Impact**: Clickjacking risks; MIME-type sniffing; internal telemetry metric disclosure.
- **Remediation**: Implement a global security headers middleware and restrict `/metrics` to authorized Prometheus/admin callers.

---

### VULN-10: Missing Rate Limiting / Brute-Force Throttling on Authentication
- **Severity**: **MEDIUM** (CVSS 5.3 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:L`)
- **Affected Files**: `backend/app/routers/auth.py`
- **Vulnerability Description**:
  While the web frontend implemented local storage attempt counters, the backend API lacked server-side IP and user-targeted rate limiting, leaving endpoints vulnerable to automated credential stuffing.
- **Business Impact**: Account compromise via brute force attacks.
- **Remediation**: Implement backend sliding-window rate limiting middleware for authentication and sensitive IoT endpoints.

---

### VULN-11: Static Fleet-Wide Pre-Shared Device Key (`DEVICE_API_KEY`)
- **Severity**: **MEDIUM** (CVSS 6.5 - `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N`)
- **Affected Files**: `backend/app/core/config.py`, `backend/app/routers/telemetry.py`
- **Vulnerability Description**:
  All ESP32 IoT hardware nodes share a single pre-shared key. Extracting the key from a single microcontroller flash allows impersonation of any node across the entire fleet.
- **Business Impact**: Compromise of one device compromises the entire fleet's data authenticity.
- **Remediation**: Implement per-device credentials stored as Argon2/SHA-256 hashes in the `devices` table with individual revocation support.

---

### VULN-12: Unnecessary DDL Execution in Update Transactions
- **Severity**: **LOW** (CVSS 3.7 - `CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:N/A:L`)
- **Affected Files**: `backend/app/services/db_service.py` (line 678)
- **Vulnerability Description**:
  Every call to `update_user_profile` executed `ALTER TABLE users ADD COLUMN IF NOT EXISTS current_stage INT DEFAULT 3;`. In PostgreSQL, `ALTER TABLE` acquires an `ACCESS EXCLUSIVE` lock on the entire table.
- **Business Impact**: Severe database lock contention, transaction delays, and connection pool exhaustion at 10M concurrent user scale.
- **Remediation**: Run DDL only during application startup / migration phases; remove DDL from runtime transaction queries.

---

### VULN-13: Insecure Token Fallback in Mobile Client Code
- **Severity**: **LOW** (CVSS 3.3 - `CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:L/I:N/A:N`)
- **Affected Files**: `mobile/lib/providers/setu_provider.dart` (line 272)
- **Vulnerability Description**:
  The mobile application fell back to `'firebase_${user.uid}'` if Google/Firebase token acquisition failed.
- **Remediation**: Reject unauthenticated states in the mobile provider and require valid authenticated tokens.

---

## Conclusion & Verification Plan
All identified vulnerabilities have been remediated in the codebase with automated regression tests created in `backend/tests/test_security_audit.py`. Verification ensures that existing farmer accounts, admin dashboard features, and mobile telemetry workflows remain fully operational while meeting enterprise-grade security standards.
