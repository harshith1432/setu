# OWASP Top 10:2025 Compliance & Implementation Mapping

This document provides a comprehensive mapping between the 10 risk categories of the **OWASP Top 10:2025** standard and the technical controls implemented in the SeriCare codebase.

---

### A01:2025 – Broken Access Control

**Risk Description:** Users acting outside their intended permissions, accessing unauthorized tenant data or actuator controls (BOLA/IDOR).

**SeriCare Controls Implemented:**
1. **Object-Level Authorization Enforcement:**
   - In `app/routers/sheds.py`: `verify_shed_access` verifies that regular farmers can only view and mutate their own assigned rearing shed (`user_shed == target_shed`).
   - In `app/routers/control.py`: `verify_shed_control_access` validates shed ownership before executing any hardware actuator relay commands.
   - In `app/routers/control.py`: `get_command_status` requires shed ownership validation before returning execution state.
   - In `app/routers/ai.py`: `get_ai_explanation` applies `verify_shed_access`, denying cross-tenant AI insight harvesting.
2. **Multi-Tenant SaaS Boundary Isolation:**
   - In `app/routers/enterprise_platform.py`: Non-superadmin users requesting orders, invoices, tickets, and installations are restricted to their tenant organization via `organization_id = user.get("organization_id")`.
   - In `app/services/enterprise_db.py`: `list_orders`, `list_invoices`, `list_support_tickets`, `list_installation_jobs`, and `search_platform_entities` execute SQL joins against `users u ON ... AND u.organization_id = %s`.
3. **Privilege Escalation Prevention:**
   - In `app/services/org_employee_db.py`: Circular reporting hierarchy detection prevents managerial privilege loops. Employees cannot grant permissions higher than their assigned access scope.

**Verification Test:** `test_bola_actuator_control_protection`, `test_ai_explainer_idor_prevention`, `test_bola_device_command_status`, `test_multi_tenant_cross_org_isolation`.

---

### A02:2025 – Cryptographic Failures

**Risk Description:** Sensitive data exposure in transit or rest, weak cryptographic hashing, or key exposure.

**SeriCare Controls Implemented:**
1. **Password Hashing:** Passwords hashed with `bcrypt` (work factor 12) via `passlib.context.CryptContext`. Plaintext passwords are never logged or stored.
2. **Transport Security:** HTTP Strict Transport Security (`Strict-Transport-Security: max-age=31536000; includeSubDomains`) enforced on all responses via `SecurityHeadersMiddleware`.
3. **Hardware Key Attestation:** IoT device authentication supports ATECC608A cryptographic co-processor mTLS verification (`mtls_service.py`).
4. **Token Revocation Table:** Token blacklisting uses SHA-256 digests of bearer tokens to prevent plaintext token retention in PostgreSQL.

**Verification Test:** `test_security_headers_and_permissions_policy`, `test_login_success_and_jwt`, `test_token_revocation_on_logout`.

---

### A03:2025 – Injection

**Risk Description:** SQL injection, command injection, or path traversal from untrusted inputs.

**SeriCare Controls Implemented:**
1. **100% Parameterized SQL Execution:** All queries in `db_service.py`, `enterprise_db.py`, and `org_employee_db.py` use psycopg2 parameterized tuples (`%s`). String formatting and string concatenation in queries are prohibited.
2. **Audio File Token Validation:** In `app/routers/voice.py`, token decoding verifies file existence in isolated voice storage directories and rejects path traversal sequences (`..`, `/`, `\`).
3. **Language Code Whitelisting:** Regular expression validation (`^(en|kn|te|hi|ta|mr)$`) prevents shell escape injection in TTS synthesis calls.

**Verification Test:** `test_farmer_registration_persistence_and_subsequent_login`, `test_voice_preview_input_length_and_language_validation`.

---

### A04:2025 – Insecure Design & Resource Consumption

**Risk Description:** Lack of business logic controls, uncontrolled resource allocation, missing rate limits, and unbounded compute.

**SeriCare Controls Implemented:**
1. **Safety Interlock System:** In `rules_engine.py`, the environmental control system implements mutually exclusive physical interlocks. Cooling fans and heating elements cannot be commanded simultaneously under any circumstances.
2. **Actuator Cooldown & Hysteresis:** Prevents rapid hardware cycling with configurable minimum runtime and cooldown intervals.
3. **Input Length Bounds:** Voice preview text restricted to `max_length=500` characters to prevent CPU/memory exhaustion in audio rendering.
4. **Rate Limiting:** `RateLimitMiddleware` restricts authentication endpoints to 30 requests per minute per IP address.

**Verification Test:** `test_safety_interlock_mutual_exclusion`, `test_voice_preview_input_length_and_language_validation`.

---

### A05:2025 – Security Misconfiguration

**Risk Description:** Weak default settings, insecure headers, permissive CORS, or debug endpoints active in production.

**SeriCare Controls Implemented:**
1. **Production Configuration Hardening:** `Settings.validate_production_security()` halts server startup if `ENVIRONMENT="production"` is set with a default or weak secret key (<32 characters).
2. **Complete Security Headers:** In `main.py`:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: SAMEORIGIN`
   - `X-XSS-Protection: 1; mode=block`
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
   - `Content-Security-Policy: default-src 'self' ...`
   - `Permissions-Policy: camera=(), microphone=(), geolocation=(self)`
3. **CORS Hardening:** `CORSMiddleware` restricts allowed origins to explicit production domains and approved deployment regex patterns, rejecting wildcard `*` with credentials.
4. **Payload Size Limit:** `RequestSizeLimitMiddleware` rejects incoming POST/PUT/PATCH bodies exceeding 2MB with HTTP 413 Payload Too Large.

**Verification Test:** `test_production_environment_config_hardening`, `test_security_headers_and_permissions_policy`, `test_request_payload_size_limit_413`.

---

### A06:2025 – Vulnerable and Outdated Components

**Risk Description:** Running unpatched third-party dependencies with known CVEs.

**SeriCare Controls Implemented:**
1. FastAPI pinned to modern ASGI stack with Starlette, Pydantic v2, and psycopg2-binary.
2. Direct dependency locking via `requirements.txt`.
3. Automated pip dependency audit via GitHub Actions security workflow (`pip audit`).

---

### A07:2025 – Identification and Authentication Failures

**Risk Description:** Weak session management, lack of session revocation, or credential stuffing.

**SeriCare Controls Implemented:**
1. **Stateless JWT with State Revocation:** Every JWT issued includes a unique `jti` (UUID4).
2. **Explicit Session Termination:** `POST /api/v1/auth/logout` adds token `jti` and SHA-256 hash to the PostgreSQL `revoked_tokens` table.
3. **In-Memory Revocation Cache:** High-performance thread-safe set in `db_service.py` provides O(1) blacklist lookups during `decode_token()`.
4. **Brute Force Protection:** Sliding window IP rate-limiting on `/api/v1/auth/login`.

**Verification Test:** `test_token_revocation_on_logout`, `test_login_invalid_credentials`.

---

### A08:2025 – Software and Data Integrity Failures

**Risk Description:** Unsigned code execution, untrusted deserialization, or lack of CI/CD integrity controls.

**SeriCare Controls Implemented:**
1. Device commands require structured schema validation (`CommandCreate` model) before dispatch.
2. Command state machine enforces strict linear progression: `REQUESTED -> AUTHORIZED -> QUEUED -> SENT -> ACKNOWLEDGED -> APPLIED`.
3. Single-use invitation tokens (`/invitations/{token}/accept`) self-destruct upon initial activation.

**Verification Test:** `test_employee_onboarding_and_activation_workflow`.

---

### A09:2025 – Security Logging and Monitoring Failures

**Risk Description:** Undetected intrusions, unlogged authorization failures, or missing audit trails.

**SeriCare Controls Implemented:**
1. **Immutable Audit Log:** `log_audit()` records actor, action, timestamp, and metadata in PostgreSQL `audit_logs` table.
2. **SIEM Event Streaming:** `SIEMForwarder` emits structured CEF/JSON security events for:
   - `AUTH_FAILURE` (Invalid credentials, forged token signatures)
   - `AUTH_LOGOUT` (Session revocation)
   - `AUTHORIZATION_FAILURE` (Cross-tenant IDOR and BOLA access attempts)
3. Indexed querying on `audit_logs(timestamp DESC)` for high-speed SOC investigations.

**Verification Test:** `test_role_based_dashboard_view_and_audit_trail`.

---

### A10:2025 – Server-Side Request Forgery (SSRF)

**Risk Description:** Coercing backend services to make arbitrary network requests to internal services or metadata endpoints.

**SeriCare Controls Implemented:**
1. Weather service (`weather.py`) restricts external calls to authenticated Open-Meteo API endpoints with validated coordinates.
2. WhatsApp alert webhook integration (`whatsapp_alerts.py`) uses official Twilio REST client libraries with credential verification and predetermined API endpoints.
3. No user-supplied URLs are accepted for webhook redirection or server-side media retrieval.

**Verification Test:** `test_live_weather_endpoint`.
