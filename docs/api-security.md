# API Security Specification
**Framework**: FastAPI / Python 3.11+  
**API Baseline**: RESTful JSON over HTTPS / WSS / SSE  
**Standard**: OWASP API Security Top 10 (2023)  

---

## 1. Authentication & Authorization Enforcement

All API endpoints are protected under the principle of **Deny by Default**.

### Public (Unauthenticated) Endpoints
Only the following endpoints may be invoked without credentials:
- `POST /api/v1/auth/login`: User and administrator login (protected by rate limiting).
- `POST /api/v1/auth/register`: Farmer self-registration (protected by rate limiting).
- `GET /health` & `GET /ready`: Orchestrator health check probes (minimal response, no internal telemetry).
- `GET /`: Platform root service status banner.

### Protected Endpoints
All other endpoints require:
1. `Authorization: Bearer <valid_jwt_token>` (for user/mobile/dashboard clients).
2. `X-Device-Key: <per_device_secret>` (for authorized hardware nodes).

---

## 2. Broken Object-Level Authorization (BOLA/IDOR) Defense

To prevent cross-tenant data leakage between farmers and rearing sheds:

```python
def verify_shed_access(
    shed_id: str,
    user_payload: dict = Depends(get_current_user_payload)
) -> dict:
    """Enforces tenant isolation: callers can only access their assigned shed unless superadmin."""
    role = user_payload.get("role")
    if role in ["admin", "superadmin"]:
        return user_payload

    username = user_payload.get("sub")
    if username:
        user = get_user_by_username(username) or get_user_by_id(username)
        if user:
            user_shed = user.get("shed_id") or "shed_01"
            if user_shed.lower() == shed_id.lower():
                return user_payload

    raise HTTPException(
        status_code=403,
        detail=f"Forbidden: You do not have authorization to access data for shed '{shed_id}'"
    )
```

This dependency is applied to:
- `GET /api/v1/sheds/{shed_id}`
- `POST /api/v1/sheds/{shed_id}/stage/{stage_num}`
- `GET /api/v1/telemetry/history/{shed_id}`
- `GET /api/v1/telemetry/export/csv/{shed_id}`
- `GET /api/v1/telemetry/sse/{shed_id}`
- `WebSocket /api/v1/telemetry/ws/{shed_id}`
- `POST /api/v1/control/{shed_id}/setpoints`
- `POST /api/v1/control/{shed_id}/override`

---

## 3. Rate Limiting Specification

Rate limits are enforced at the API gateway / application middleware layer:

| Route Group | Limit | Window | Action on Limit |
|---|---|---|---|
| `/auth/login`, `/auth/register` | 10 requests | 60 seconds per IP | HTTP 429 Too Many Requests |
| `/control/**` (Actuator commands) | 30 requests | 60 seconds per user | HTTP 429 Too Many Requests |
| `/telemetry/record` (IoT Ingestion) | 120 requests | 60 seconds per node | HTTP 429 Too Many Requests |
| General API Read Queries | 300 requests | 60 seconds per IP | HTTP 429 Too Many Requests |

---

## 4. HTTP Security Headers Specification

Every response issued by the FastAPI service includes:

```http
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; img-src 'self' data: https:; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https: wss:;
Permissions-Policy: geolocation=(self), camera=(), microphone=(), payment=()
```
