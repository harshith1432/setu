# SeriCare (Setu) — Enterprise Security Threat Model & Defense-in-Depth

## 1. Threat Landscape & Security Posture

SeriCare controls physical agricultural infrastructure. A compromised actuator command can overheat a rearing shed, destroying silkworm batches worth tens of thousands of rupees. Consequently, the platform is engineered against OWASP Top 10 API Security Risks and IoT vulnerabilities.

---

## 2. STRIDE Threat Model Analysis

| STRIDE Category | Threat Vector | Vulnerability Addressed | Applied Defense & Mitigation |
| :--- | :--- | :--- | :--- |
| **Spoofing** | Attacker impersonates legitimate ESP32 gateway to inject false sensor temperatures. | Unauthenticated telemetry ingestion. | **Hardware Authentication Gate**: Every telemetry packet must supply a valid `X-Device-Key` or HMAC-SHA256 signature against pre-registered `hardware_mac` in `devices` table. |
| **Tampering** | Rogue actor intercepts and alters actuator commands in transit. | Unencrypted HTTP cleartext. | **Mandatory TLS 1.3**: All MQTT (port 8883) and HTTPS (port 443) traffic is encrypted in transit. MQTT broker requires client credentials. |
| **Repudiation** | Operator denies issuing a destructive heater override. | Missing audit trail. | **Immutable Audit Log**: Every actuator command is committed to `device_commands` with `issued_by`, client IP, timestamp, and target state before execution. |
| **Information Disclosure** | Competitor reads competitor farm environmental conditions and yields. | Broken Object-Level Authorization (BOLA / IDOR). | **BOLA Enforcement Gate (`verify_shed_access`)**: Endpoints verify that the authenticated JWT subject is explicitly assigned to the queried `shed_id`. Cross-tenant queries return `HTTP 403 Forbidden`. |
| **Denial of Service** | Botnet floods telemetry ingestion with fake readings to crash DB. | Unbounded connection pools. | **Nginx Token Bucket Rate Limiting**: 500 req/sec per device key, 100 req/sec per client IP. PgBouncer multiplexing caps DB connections at 200 max. |
| **Elevation of Privilege** | Regular farmer calls admin API to reconfigure cluster thresholds. | Missing Role-Based Access Control (RBAC). | **RBAC Dependency**: Admin endpoints require JWT claim `role in ['admin', 'superadmin']`. Regular farmer tokens are rejected with `HTTP 403`. |

---

## 3. Broken Object-Level Authorization (BOLA / IDOR) Defense

The platform enforces strict resource authorization at the FastAPI dependency level:

```python
def verify_shed_access(shed_id: str, payload: dict = Depends(get_current_user_payload)) -> dict:
    role = payload.get("role")
    if role in ["admin", "superadmin"]:
        return payload  # Superadmins oversee all rearing sheds

    username = payload.get("sub") or payload.get("user_id")
    user = get_user_by_username(username) or get_user_by_id(username)
    if user:
        user_shed = (user.get("shed_id") or "").lower()
        if user_shed == shed_id.strip().lower() or user.get("id", "").lower() == shed_id.strip().lower():
            return payload  # Authorized: User owns this shed

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Forbidden: You do not have authorization to access data for shed '{shed_id}'"
    )
```

Verified via unit tests: `test_bola_actuator_control_protection` confirms that Farmer Ramesh attempting to command Shed 02 receives `HTTP 403 Forbidden`.

---

## 4. Hardware Node Credential Lifecycle & Mutual TLS

1. **Pre-Shared Device Keys**: Gateways are provisioned with a secure random 256-bit key at manufacture time (`DEVICE_API_KEY`).
2. **MQTT 5 Topic Isolation**: EMQX access control lists (ACLs) enforce that device `esp32_01` in organization `org_01` can ONLY publish and subscribe to:
   - `organizations/org_01/devices/esp32_01/#`
   Any attempt to subscribe to wildcards (`#`) or another tenant's topics is dropped immediately at the broker level.
3. **Firmware Integrity**: OTA firmware update binaries must be cryptographically signed with an Ed25519 private key verified by the bootloader.

---

## 5. Secrets Hygiene & Zero-Trust Configuration

- **Zero Hardcoded Secrets**: Secrets (`DATABASE_URL`, `JWT_SECRET`, `TWILIO_AUTH_TOKEN`, `DEVICE_API_KEY`) are injected strictly at runtime via environment variables or secret managers (HashiCorp Vault, AWS Secrets Manager).
- **Default Secret Warning**: If the application boots with default placeholder secrets in production mode, startup hooks emit critical warnings.
- **Defensive Timeouts**: Database cursors enforce `statement_timeout = '5000'` (5 seconds) to prevent slow SQL attacks from exhausting worker pools.
