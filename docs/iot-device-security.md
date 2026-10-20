# IoT Device & Gateway Security Specification
**Hardware**: ESP32 Microcontroller / Embedded Linux Gateways  
**Communication Protocol**: HTTPS / MQTTS (TLS 1.3)  
**Standard**: NIST SP 800-82 / ENISA Baseline Security for IoT  

---

## 1. Device Identity & Credential Management

Each physical sensing node or gateway possesses a unique cryptographic identity:
- **`device_id`**: Globally unique alphanumeric identifier (e.g. `node_shed_01_core`).
- **`device_key`**: A cryptographically random high-entropy pre-shared secret (minimum 32 bytes).
- **`device_key_hash`**: The backend only stores the Argon2id or SHA-256 hash of the device key in the `devices` table, never the raw key in plaintext.

```sql
CREATE TABLE IF NOT EXISTS devices (
    device_id VARCHAR(64) PRIMARY KEY,
    shed_id VARCHAR(64) NOT NULL,
    organization_id VARCHAR(64) DEFAULT 'org_default',
    device_name VARCHAR(128),
    device_key_hash VARCHAR(255),
    firmware_version VARCHAR(32) DEFAULT 'v1.0.0',
    status VARCHAR(32) DEFAULT 'ONLINE',
    last_seen_at TIMESTAMPTZ,
    last_sequence_number BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL
);
```

---

## 2. Telemetry Ingestion Verification

When an IoT node transmits sensor data to `POST /api/v1/telemetry/record`:
1. **Device Authentication**:
   The request must include `X-Device-Key: <secret>`. The server retrieves the device record and verifies the key hash.
2. **Device State Verification**:
   The device status is checked. If the status is `REVOKED` or `SUSPENDED`, the reading is rejected with `HTTP 403 Forbidden`.
3. **Replay & Sequence Protection**:
   Readings may carry an incremental `sequence_number`. If `sequence_number <= last_sequence_number`, the frame is flagged or discarded as a duplicate/replay attempt.
4. **Range & Sanity Checks**:
   - `indoor_temp`: -10.0°C to 60.0°C
   - `indoor_hum`: 0.0% to 100.0%
   - `air_quality`: 0.0% to 100.0%
   - `light_lux`: 0.0 to 100,000.0 lx

---

## 3. Instant Device Revocation Process

If a physical node in a rearing shed is stolen, tampered with, or compromised:
1. Super Admin navigates to Device Registry or issues revocation command:
   ```sql
   UPDATE devices SET status = 'REVOKED' WHERE device_id = 'target_node_id';
   ```
2. Any subsequent telemetry or command acknowledgement from that device is blocked immediately.
3. The cluster raises a high-priority security alert in `audit_logs`.
