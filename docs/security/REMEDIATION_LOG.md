# SeriCare Security Remediation Log

This document records the exact changes, files modified, vulnerability mitigations, and automated verification tests implemented during the security hardening audit.

---

## Remediation Entry 1: AI Explainer Broken Object Level Authorization (BOLA/IDOR)

- **Vulnerability ID:** VULN-01 (CWE-639, OWASP A01:2025)
- **Component:** `backend/app/routers/ai.py`
- **Root Cause:** Route `/api/v1/ai/explain/{shed_id}` utilized `get_current_user_payload` which checked only JWT validity without verifying that the authenticated user was authorized to view the requested `shed_id`.
- **Code Change:**
  - Replaced `payload: dict = Depends(get_current_user_payload)` with `payload: dict = Depends(verify_shed_access)`.
  - Added access check enforcing that farmers can only view their own rearing shed.
- **Verification Test:** `backend/tests/test_owasp_hardening.py::test_ai_explainer_idor_prevention` (PASSED).

---

## Remediation Entry 2: Voice Preview Compute Exhaustion & Language Injection

- **Vulnerability ID:** VULN-02 (CWE-400 / CWE-20, OWASP A04:2025)
- **Component:** `backend/app/routers/voice.py`
- **Root Cause:** Text synthesis accepted unbounded strings, enabling compute denial of service, and lacked language code validation.
- **Code Change:**
  - Added strict Pydantic input limits: `text: str = Field(..., min_length=1, max_length=500)`.
  - Enforced strict language regex validation: `pattern="^(en|kn|te|hi|ta|mr)$"`.
  - Added support for both `lang` and `language` fields with regex validation.
- **Verification Test:** `backend/tests/test_owasp_hardening.py::test_voice_preview_input_length_and_language_validation` (PASSED).

---

## Remediation Entry 3: Actuator Command Status BOLA

- **Vulnerability ID:** VULN-04 (CWE-639, OWASP A01:2025)
- **Component:** `backend/app/routers/control.py`
- **Root Cause:** Endpoint `/api/v1/control/commands/status/{command_id}` returned command execution state without checking whether the caller was authorized to access the shed targeted by the command.
- **Code Change:**
  - Looked up the targeted `shed_id` for the command.
  - Injected `verify_shed_control_access(cmd.get("shed_id"), user_payload)` before returning status.
- **Verification Test:** `backend/tests/test_owasp_hardening.py::test_bola_device_command_status` (PASSED).

---

## Remediation Entry 4: JWT Token Revocation & Session Termination

- **Vulnerability ID:** VULN-03 (CWE-613, OWASP A07:2025)
- **Components:** `backend/app/services/db_service.py`, `backend/app/core/security.py`, `backend/app/routers/auth.py`
- **Root Cause:** JWT tokens were purely stateless with no server-side revocation mechanism, allowing logged-out or compromised tokens to remain active until their 7-day expiration.
- **Code Change:**
  - Created PostgreSQL `revoked_tokens` table with TTL index `idx_revoked_tokens_expires`.
  - Added thread-safe in-memory cache `_revoked_tokens_cache` with RWLock synchronization for sub-millisecond lookups.
  - Injected unique `jti` (UUID4) into all minted tokens in `create_access_token()`.
  - Enforced revocation blacklist check in `decode_token()`.
  - Added endpoint `POST /api/v1/auth/logout` that accepts Bearer credentials and revokes the token.
- **Verification Test:** `backend/tests/test_owasp_hardening.py::test_token_revocation_on_logout` (PASSED).

---

## Remediation Entry 5: Multi-Tenant Boundary Isolation

- **Vulnerability ID:** VULN-05 (CWE-284, OWASP A01:2025)
- **Components:** `backend/app/services/enterprise_db.py`, `backend/app/routers/enterprise_platform.py`
- **Root Cause:** Orders, invoices, support tickets, installation jobs, and global search routes returned records across all tenants when called by non-superadmin users (e.g. `company_admin` of another organization).
- **Code Change:**
  - Updated `list_orders()`, `list_invoices()`, `list_support_tickets()`, `list_installation_jobs()`, and `search_platform_entities()` to accept `organization_id: Optional[str] = None`.
  - Applied SQL parameterization joining `users u ON ... AND u.organization_id = %s`.
  - In `get_order()` and `get_ticket()`, verified that the entity's owner belongs to caller's organization, returning HTTP 403 Forbidden on cross-tenant attempts.
- **Verification Test:** `backend/tests/test_owasp_hardening.py::test_multi_tenant_cross_org_isolation` (PASSED).

---

## Remediation Entry 6: Request Payload Size Limitation Middleware

- **Vulnerability ID:** VULN-06 (CWE-400, OWASP A05:2025)
- **Component:** `backend/app/main.py`
- **Root Cause:** Missing body size limit on incoming HTTP POST/PUT requests allowed denial of service attacks via large payloads.
- **Code Change:**
  - Implemented `RequestSizeLimitMiddleware` checking `Content-Length`.
  - Rejects payloads exceeding 2MB with HTTP 413 Payload Too Large.
- **Verification Test:** `backend/tests/test_owasp_hardening.py::test_request_payload_size_limit_413` (PASSED).

---

## Remediation Entry 7: Production Environment Secret Key Hardening

- **Vulnerability ID:** VULN-07 (CWE-1188, OWASP A05:2025)
- **Component:** `backend/app/core/config.py`
- **Root Cause:** Default fallback secret key could accidentally be deployed to production environments without triggering an error.
- **Code Change:**
  - Added `ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")`.
  - Added `Settings.validate_production_security()` which enforces that if `ENVIRONMENT="production"`, default/weak secret keys or keys < 32 characters raise a fatal `ValueError`.
- **Verification Test:** `backend/tests/test_owasp_hardening.py::test_production_environment_config_hardening` (PASSED).

---

## Remediation Entry 8: Permissions-Policy HTTP Security Header

- **Vulnerability ID:** VULN-08 (CWE-693, OWASP A05:2025)
- **Component:** `backend/app/main.py`
- **Root Cause:** Modern browser device access restrictions were not explicitly declared.
- **Code Change:**
  - Added `response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"` in `SecurityHeadersMiddleware`.
- **Verification Test:** `backend/tests/test_owasp_hardening.py::test_security_headers_and_permissions_policy` (PASSED).
