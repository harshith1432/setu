# Enterprise Threat Model: SeriCare IoT Platform
**Standard**: STRIDE Methodology (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)  
**Target Scope**: 10M Concurrent Users & Fleet-Scale Connected Hardware  
**Document Revision**: 1.0 (Enterprise Production Baseline)

---

## 1. System Architecture & Trust Boundaries

The SeriCare platform consists of four distinct operational zones separated by defined trust boundaries:

```
[ UNTRUSTED PUBLIC INTERNET / FIELD ]
  │
  ├── ESP32 IoT Sensors & Gateway Nodes (Field Sensors / Relays)
  ├── Mobile Applications (Flutter Android / iOS)
  └── Browser Dashboard (Admin Web / Field Supervisors)
  │
  ▼ [ TRUST BOUNDARY 1: Edge TLS / Reverse Proxy / Rate Limiter ]
[ DMZ / INGESTION TIER ]
  │
  ├── FastAPI Web Server (HTTP REST / Server-Sent Events / WebSockets)
  └── Static Frontend Assets CDN (Vercel / Reverse Proxy)
  │
  ▼ [ TRUST BOUNDARY 2: Application Security / Object-Level Authorization ]
[ SECURE INTERNAL SERVICE TIER ]
  │
  ├── In-Memory Rules & Automation Engine (CSB Instar Stage Thresholds)
  ├── Command Lifecycle State Machine (REQUESTED -> ACKNOWLEDGED -> APPLIED)
  ├── Twilio WhatsApp Dispatcher & Voice Alert Service
  └── Real-Time WebSocket Channel Manager
  │
  ▼ [ TRUST BOUNDARY 3: Data Tier (Private Network / VPC) ]
[ PERSISTENCE & TIMESERIES STORAGE ]
  │
  └── PostgreSQL Database (Partitioned Timeseries, Users, Devices, Audit Logs)
```

---

## 2. STRIDE Threat Analysis Matrix

| Threat Category | Threat ID | Threat Description | Attack Vector | System Impact | Mitigation in SeriCare |
|---|---|---|---|---|---|
| **Spoofing** | T-S01 | IoT Hardware Impersonation | Attacker extracts hardcoded pre-shared key and sends fraudulent sensor readings. | False climate alarms, improper automated actuator triggers. | Per-device key hashing (`device_key_hash`), device registration status check (`ONLINE`/`REVOKED`), sequence number validation. |
| **Spoofing** | T-S02 | User Identity Spoofing | Attacker sends forged JWT or unverified OAuth claims. | Unauthorized access to farmer accounts. | Cryptographic HMAC-SHA256 signature enforcement, rejection of unverified `firebase_` prefixes, strict issuer/expiry checks. |
| **Spoofing** | T-S03 | Webhook Identity Spoofing | Attacker sends fake WhatsApp status updates to `/whatsapp/webhook`. | False phone verification, unauthorized alert enrollments. | `X-Twilio-Signature` HMAC-SHA1 verification against provider secret and raw request parameters. |
| **Tampering** | T-T01 | Sensor Telemetry Manipulation | Man-in-the-middle or malicious node modifies temperature/humidity in transit. | Silkworm death due to false cooling/heating automation. | TLS 1.3 encryption in transit; range and schema validation (temperatures restricted to -10°C–60°C, RH 0–100%). |
| **Tampering** | T-T02 | Device Command Tampering | Attacker intercepts or modifies actuator control parameters (e.g. PWM brightness or cooler state). | Physical damage to shed equipment or fire hazard. | Command signature / payload validation, server-enforced operating bounds, safety interlocks in rules engine. |
| **Repudiation** | T-R01 | Unaudited Manual Overrides | Operator disables heating in winter, denying responsibility when cocoon harvest fails. | Lack of legal accountability and forensic trace. | Comprehensive immutable audit logging (`audit_logs` table) with caller username, action, timestamp, and IP origin. |
| **Information Disclosure** | T-I01 | Cross-Tenant Telemetry Leakage (BOLA/IDOR) | Farmer A queries `/sheds/shed_02` to monitor Competitor B's rearing batches. | Breach of privacy and trade secrets. | Centralized object-level authorization (`verify_shed_access` dependency) verifying ownership on every request. |
| **Information Disclosure** | T-I02 | Surveillance via Unauthenticated Streams | Attacker connects to WebSocket `/ws/{shed_id}` or SSE without auth. | Live spying on farm activity. | Mandatory JWT authentication query handshake and tenancy authorization on WebSocket and SSE endpoints. |
| **Information Disclosure** | T-I03 | Farmer Directory Scraping | Scraping `/auth/check-farmer` to harvest phone numbers and locations. | Bulk spam, phishing attacks on rural farmers. | Stripped response to boolean existence (`{"exists": bool}`) without returning any PII. |
| **Denial of Service** | T-D01 | Authentication Brute-Force | Automated distributed credential stuffing on `/auth/login`. | Account lockouts, database connection exhaustion. | Server-side IP and user sliding-window rate limiting (10 req/min for auth); progressive delay. |
| **Denial of Service** | T-D02 | Telemetry Flooding | Malicious node sends 10,000 HTTP POSTs/sec to `/telemetry/record`. | Backend crash, DB storage exhaustion. | Device-level rate limiting, connection pooling with timeouts (8s statement timeout, 3s lock timeout). |
| **Denial of Service** | T-D03 | Actuator Command Flooding | Rapidly toggling cooler/heater ON and OFF. | Physical compressor burnout, relay contact welding. | Minimum command cooldowns, command state deduplication, safety interlocks preventing simultaneous heating and cooling. |
| **Elevation of Privilege** | T-E01 | Standard Farmer Accessing Superadmin Endpoints | Farmer calls `/api/v1/admin/stages` or `/api/v1/admin/farmers/{id}`. | Unauthorized modification of global thresholds or deleting other farmers. | Role-based access control (`require_superadmin`) verifying `role in ['admin', 'superadmin']` from verified JWT claims. |
| **Elevation of Privilege** | T-E02 | Mass Assignment in Profile Updates | User submits `{"role": "superadmin"}` in `PUT /auth/profile`. | Privilege escalation to cluster administrator. | Strict whitelist in `update_user_profile` that excludes privileged columns (`role`, `hashed_password`, `id`). |

---

## 3. IoT-Specific Attack Vectors & Safety Controls

### 3.1 Actuator Safety Interlocks
- **Hazard**: Heater and Cooler activated simultaneously, causing thermal stress and electrical overload.
  - **Interlock**: The rules engine and manual override enforce mutually exclusive operation. Activating the cooler automatically forces the heater OFF, and vice-versa.
- **Hazard**: Light brightness set above 100% or below 0%.
  - **Interlock**: Clamped strictly to integer range `[0, 100]` with type validation.

### 3.2 Telemetry Ingestion Safety
- **Hazard**: Malicious node sends temperature of 500°C, triggering emergency ventilation when unneeded.
  - **Interlock**: Outlier rejection and schema validation: `indoor_temp` constrained to reasonable environmental boundaries (`-10.0°C <= temp <= 65.0°C`).

---

## 4. Residual Risks & Accepted Defenses
1. **Physical Device Tampering in the Field**: Microcontrollers deployed in rural sheds without hardware secure elements (HSMs) are vulnerable to physical extraction.
   - **Mitigation**: Server-side device revocation endpoint allows immediate blocking of compromised device IDs.
2. **Third-Party Telephony Availability**: Twilio WhatsApp message delivery depends on carrier networks.
   - **Mitigation**: Circuit breakers with cooldown rollback prevent alert flooding; fallback to web/mobile push alerts.
