# Automated Security Testing & Verification Specification
**Test Suite**: Pytest with AsyncIO / AnyIO  
**Coverage**: Authentication, Authorization (IDOR), Actuator Interlocks, Command Lifecycle, SQL Safety, Rate Limiting, Security Headers  

---

## 1. Automated Security Test Matrix

The automated security regression suite is located in `backend/tests/test_security_audit.py`:

| Test Function | Target Vulnerability | Verification Criteria |
|---|---|---|
| `test_security_headers_present` | VULN-09 (Missing Security Headers) | All API responses include HSTS, CSP, X-Content-Type-Options, X-Frame-Options. |
| `test_rejection_of_insecure_token_fallbacks` | VULN-01 / VULN-02 (Token Bypass) | Rejects forged `firebase_` prefixes and unsigned tokens with HTTP 401. |
| `test_rejection_of_unauthorized_google_sync` | VULN-03 (Account Takeover) | Rejects attempts to acquire tokens via unverified `/google-sync` requests. |
| `test_cross_tenant_shed_isolation_idor` | VULN-04 (BOLA/IDOR on Sheds) | Farmer A cannot read or change the rearing stage of Farmer B's shed (HTTP 403). |
| `test_cross_tenant_telemetry_isolation` | VULN-04 (Telemetry IDOR) | Farmer A cannot view or export CSV telemetry for Farmer B's shed (HTTP 403). |
| `test_unauthorized_device_command_rejected` | VULN-05 (Actuator Command Injection) | Commands issued for unauthorized device IDs or sheds are rejected with HTTP 403. |
| `test_unauthenticated_sse_and_ws_rejected` | VULN-06 (Streaming Surveillance) | Connecting to SSE or WebSocket without valid credentials results in HTTP 401 / disconnect. |
| `test_public_farmer_enumeration_pii_redacted` | VULN-07 (PII Exposure) | `/auth/check-farmer` returns only boolean existence, without leaking phone/farm/name. |
| `test_command_lifecycle_state_machine` | Command Safety | Verifies explicit lifecycle progression: `QUEUED` -> `ACKNOWLEDGED` -> `APPLIED`. |
| `test_actuator_anti_simultaneous_interlock` | Physical Actuator Safety | Verifies cooler and heater cannot be active simultaneously in rules engine. |
| `test_rate_limiting_on_auth_endpoints` | VULN-10 (Brute-Force Flooding) | Excessive rapid requests return HTTP 429 Too Many Requests. |

---

## 2. Execution Instructions

To execute the complete security test suite:
```bash
pytest backend/tests/test_security_audit.py -v
```
All tests must pass with zero failures before committing code or deploying to production.
