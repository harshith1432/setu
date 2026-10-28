# SeriCare Security Testing Guide & Verification Procedures

This operational guide provides procedures for running automated security test suites, SAST analysis, dynamic API testing, and regression verification for the SeriCare platform.

---

## 1. Automated Security Regression Suite

The platform includes a dedicated security test module (`backend/tests/test_owasp_hardening.py`) verifying all fixed OWASP Top 10:2025 and ASVS 5.0 controls.

### Prerequisites:
- Local PostgreSQL instance running on `127.0.0.1:5432` with user `setu_user`.
- Python 3.11+ environment with dependencies installed from `backend/requirements.txt`.

### Execution:
To run only the OWASP hardening security test suite:
```bash
pytest backend/tests/test_owasp_hardening.py -v
```

To run the entire platform test suite (functional, RBAC, IoT rules, and security):
```bash
pytest backend/tests/ -v
```

Expected output:
```
====================== 84 passed in 18.20s =======================
```

---

## 2. Static Application Security Testing (SAST)

### 2.1 AST Route Coverage & Authorization Audit
Run the automated AST analyzer to verify that all API endpoints enforce authentication dependencies:
```bash
python -c "
import ast
with open('backend/app/routers/ai.py', 'r', encoding='utf-8') as f:
    tree = ast.parse(f.read())
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        print(node.name, [a.arg for a in node.args.args])
"
```

### 2.2 Bandit Python Security Linter
Run Bandit to scan for common Python vulnerabilities (e.g., hardcoded passwords, unsafe deserialization, shell escapes):
```bash
bandit -r backend/app/ -ll -ii
```

### 2.3 Dependency Vulnerability Scanning (SCA)
Audit installed dependencies against the Python Packaging Advisory Database:
```bash
pip audit
```

---

## 3. Dynamic Application Security Testing (DAST)

### 3.1 HTTP Security Headers Verification
Inspect live response headers using curl:
```bash
curl -I https://<staging-url>/health
```
**Verify presence of:**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Permissions-Policy: camera=(), microphone=(), geolocation=(self)`
- `Content-Security-Policy: default-src 'self' ...`

### 3.2 Request Payload Size Enforcement (HTTP 413)
Verify that payloads >2MB are rejected:
```bash
curl -X POST https://<staging-url>/api/v1/auth/login \
  -H "Content-Length: 3145728" \
  -H "Content-Type: application/json" \
  --data "{}"
```
**Expected Response:** `HTTP/1.1 413 Payload Too Large`

### 3.3 Token Revocation & Session Termination Verification
1. Login to obtain an active JWT:
   ```bash
   TOKEN=$(curl -s -X POST https://<staging-url>/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"<password>"}' | jq -r .access_token)
   ```
2. Verify token works:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" https://<staging-url>/api/v1/dashboard/overview
   # Returns HTTP 200
   ```
3. Issue logout:
   ```bash
   curl -X POST -H "Authorization: Bearer $TOKEN" https://<staging-url>/api/v1/auth/logout
   # Returns HTTP 200 {"message": "Successfully logged out. Token has been revoked."}
   ```
4. Attempt to use revoked token:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" https://<staging-url>/api/v1/dashboard/overview
   # Returns HTTP 401 Unauthorized {"detail": "Authentication token has been revoked or invalidated..."}
   ```

---

## 4. Continuous Integration Security Gates

In `.github/workflows/`, ensure that security gates fail the build if:
1. `pytest backend/tests/test_owasp_hardening.py` exits with non-zero code.
2. `pip audit` reports high or critical unpatched CVEs.
3. Production configuration validation fails (`ENVIRONMENT=production` with default secrets).
