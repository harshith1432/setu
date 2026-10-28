# SeriCare / Setu Enterprise REST API Documentation

Base URL: `/api/v1`  
Interactive Swagger UI: `/docs`  
Redoc API Explorer: `/redoc`

---

## 1. Authentication, Registration & Session Isolation Endpoints

Setu enforces enterprise-grade identity and access controls aligned with OWASP ASVS 5.0 Level 2. The authentication architecture provides:
- **Unified Login**: A single public endpoint servicing all 10 platform personas with automatic role determination.
- **Farmer-Only Registration**: Public self-service onboarding for sericulture farmers with automatic shed allocation and privilege escalation defense.
- **Per-Tab Session Isolation**: Independent credentials and state management per browser tab using `X-Tab-ID` and `X-Session-ID`.
- **Token Revocation / Blacklist**: Instant session revocation recorded in `revoked_tokens` and `user_sessions`.

---

### `POST /api/v1/auth/login`
Authenticates users of all roles (Admin, CEO, HR, Operations, Technician, Sales, Support, Analyst, Farmer) using JSON credentials.
- **Rate Limit**: 30 requests/minute per client IP (DDoS/brute-force mitigation).
- **Headers**:
  - `Content-Type: application/json`
  - `X-Tab-ID: <string>` *(Optional, tab identifier for multi-tab isolation)*
- **Request**:
  ```json
  {
    "username": "admin",
    "password": "your_secure_password"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "session_id": "sess_89f7a1c0d4e5",
    "user": {
      "id": "usr_admin",
      "username": "admin",
      "role": "superadmin",
      "full_name": "Setu Super Admin",
      "preferred_language": "en",
      "shed_id": "shed_01",
      "organization_id": "default_org"
    }
  }
  ```
- **Errors**:
  - `401 Unauthorized`: Generic `"Incorrect username or password"` (prevents user enumeration).
  - `413 Payload Too Large`: If body exceeds 2MB.
  - `429 Too Many Requests`: Rate limit exceeded.

---

### `POST /api/v1/auth/register`
Public self-service registration exclusively for new sericulture farmers.
- **Access**: Public / Unauthenticated
- **Headers**:
  - `Content-Type: application/json`
  - `X-Tab-ID: <string>` *(Optional, creates isolated tab session)*
- **Request**:
  ```json
  {
    "full_name": "Ramesh Gowda",
    "username": "ramesh_gowda",
    "phone": "+919845012345",
    "email": "ramesh@sericare.in",
    "password": "FarmerPassword@123",
    "confirm_password": "FarmerPassword@123",
    "farm_name": "Gowda Sericulture Farm",
    "region": "Karnataka (Mysuru Belt)",
    "dfl_capacity": "300 DFL",
    "breed": "Bivoltine (FC1 x FC2)",
    "terms_accepted": true
  }
  ```
- **Validation Rules**:
  - Password must be at least 8 characters.
  - `password` and `confirm_password` must match.
  - `terms_accepted` must be `true`.
  - Rejects duplicate username, phone number, or email (`400 Bad Request`).
  - **Privilege Escalation Defense**: Backend strictly overrides and enforces `assigned_role = "farmer"` regardless of payload.
- **Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "session_id": "sess_47a1c0d4e5f2",
    "user": {
      "id": "usr_farmer_ramesh_gowda",
      "username": "ramesh_gowda",
      "role": "farmer",
      "full_name": "Ramesh Gowda",
      "shed_id": "shed_04",
      "farm_name": "Gowda Sericulture Farm",
      "region": "Karnataka (Mysuru Belt)"
    }
  }
  ```

---

### `GET /api/v1/auth/me`
Retrieves authoritative account details, verified permissions, and assigned rearing sheds for the active tab session.
- **Headers**: `Authorization: Bearer <access_token>`
- **Response (200 OK)**:
  ```json
  {
    "id": "usr_admin",
    "username": "admin",
    "role": "superadmin",
    "full_name": "Setu Super Admin",
    "access_scope": "GLOBAL",
    "assigned_resources": {
      "sheds": ["shed_01", "shed_02", "shed_03"],
      "devices": []
    },
    "permissions": ["VIEW_ALL_SHEDS", "MANAGE_SYSTEM", "CONTROL_ACTUATORS"]
  }
  ```

---

### `POST /api/v1/auth/logout`
Revokes **only the calling tab's active session**. Other open tabs and devices for the same user remain uninterrupted.
- **Headers**: `Authorization: Bearer <access_token>`
- **Response (200 OK)**:
  ```json
  {
    "message": "Successfully logged out of current tab session. Token has been revoked."
  }
  ```
- **Backend Action**:
  - Marks `is_revoked = TRUE` in `user_sessions` for `session_id`.
  - Adds JWT `jti` to `revoked_tokens` blacklist table.
  - Any subsequent request with this token immediately returns `401 Unauthorized`.

---

### `GET /api/v1/auth/sessions`
Returns all active, unexpired concurrent sessions for the authenticated user across all tabs and devices.
- **Headers**: `Authorization: Bearer <access_token>`
- **Response (200 OK)**:
  ```json
  [
    {
      "session_id": "sess_89f7a1c0d4e5",
      "created_at": "2026-10-28T18:00:00Z",
      "last_activity": "2026-10-28T18:04:12Z",
      "ip_address": "127.0.0.1",
      "user_agent": "Mozilla/5.0..."
    }
  ]
  ```

---

### `POST /api/v1/auth/logout-all`
Terminates all active sessions for the authenticated user across all devices and browser tabs.
- **Headers**: `Authorization: Bearer <access_token>`
- **Response (200 OK)**:
  ```json
  {
    "message": "Revoked 3 active session(s) across all devices and tabs."
  }
  ```

---

## 2. Public Web Routes

| Route | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Public marketing landing page (browser clients) / API health info (HTTP/API clients) |
| `/home` | `GET` | Public Setu landing page with interactive features and product tour |
| `/login` | `GET` | Unified official Setu login gateway (all 10 roles) |
| `/register` | `GET` | Public farmer-only self-service registration portal |
| `/admin` | `GET` | Enterprise Operations Console (21 operational modules) |

---

## 3. Dashboard & Platform Overview Endpoints

### `GET /api/v1/dashboard/overview`
**Roles**: `superadmin`, `admin`, `ceo`, `sales`, `support`  
Returns 100% authoritative database-aggregated KPIs with zero mock data.
- **Response (200 OK)**:
  ```json
  {
    "total_farmers": 103,
    "active_farmers": 103,
    "total_sheds": 107,
    "total_devices": 5,
    "online_devices": 5,
    "offline_devices": 0,
    "active_subscriptions": 1,
    "mrr_inr": 999.0,
    "total_revenue_inr": 17298.0,
    "pending_orders": 0,
    "open_tickets": 0,
    "critical_tickets": 0,
    "active_alerts": 0,
    "critical_alerts": 0,
    "pending_installations": 0,
    "last_synced_at": "2026-10-28T16:00:00Z"
  }
  ```

### `GET /api/v1/dashboard/health`
Returns database connection pool status, telemetry stream connectivity, and primary shed environmental readings.

---

## 4. Analytics & Time-Series Endpoints

### `GET /api/v1/analytics/trends?days=7`
**Query Parameters**:
- `days` (integer, default 7, range 1-90): Number of days of historical aggregation.
- **Response**: Day-by-day averages for indoor temperature, humidity, air quality, lux, daily order counts, and revenue.

---

## 5. Products & Inventory Ledger Endpoints

### `GET /api/v1/products`
Lists all commercial equipment with SKU, category, price, and stock levels.

### `POST /api/v1/products`
**Roles**: `superadmin`, `admin`, `sales`  
Creates a new SKU in the catalogue with inventory tracking.

### `POST /api/v1/products/{id}/stock-adjustment`
**Roles**: `superadmin`, `admin`, `sales`  
Adjusts warehouse stock with an immutable ledger entry.

---

## 6. Sales Orders, Subscriptions & Invoicing

### `GET /api/v1/orders`
Lists orders. Supports filtering by `status` and `user_id`. Farmers only receive their own records (BOLA defense).

### `GET /api/v1/orders/{order_id}`
Returns order details, itemized product lines, invoice, and payment transaction references.

### `PATCH /api/v1/orders/{order_id}/status`
Transitions order status (`PENDING` → `PAID` → `PROCESSING` → `FULFILLED` → `CANCELLED`).

### `GET /api/v1/subscriptions`
Lists active recurring SaaS contracts and renewal dates.

### `GET /api/v1/invoices`
Lists customer invoices with tax breakdowns (CGST + SGST 18%).

---

## 7. Helpdesk & Support Cases

### `GET /api/v1/support/tickets`
Lists tickets with priority, status, and agent assignment.

### `POST /api/v1/support/tickets`
Creates a customer support case.

### `GET /api/v1/support/tickets/{ticket_id}`
Returns the case along with complete threaded messages and internal notes.

### `POST /api/v1/support/tickets/{ticket_id}/messages`
Appends a message or internal note to the case thread.

### `PATCH /api/v1/support/tickets/{ticket_id}/status`
Updates status (`RESOLVED`, `CLOSED`, `ESCALATED`) and assignee.

---

## 8. Installations & Field Engineering

### `GET /api/v1/installations`
Lists field installation jobs with workflow states.

### `POST /api/v1/installations`
Schedules an on-site installation job for a farmer's rearing shed.

### `PATCH /api/v1/installations/{job_id}`
Advances job workflow (`REQUESTED` → `SCHEDULED` → `IN_PROGRESS` → `VERIFICATION` → `COMPLETED`) with mandatory checklist verification.

### `GET /api/v1/installations/team`
Returns roster of certified technicians and current workload.

---

## 9. Guidance & Multilingual Advisory

### `GET /api/v1/guidance?language=kn`
Returns localized rearing guides and CSRTI research recommendations across English, Kannada, Telugu, Hindi, Tamil, and Malayalam.

---

## 10. IoT Telemetry, Sensors & Live Streaming

### `POST /api/v1/telemetry/record`
Ingestion gate for edge IoT gateways. Authenticated via `X-Device-Key` or mTLS client certificate.

### `GET /api/v1/telemetry/live-stream/{shed_id}`
Server-Sent Events (SSE) live stream providing real-time sub-second updates to connected dashboards.

### `GET /api/v1/sensors?shed_id=shed_01`
Returns hardware sensors metadata, pin assignments, and calibration offsets.

### `POST /api/v1/sensors/{sensor_id}/calibrate`
Applies hardware calibration offset (± delta) to sensor probe.

---

## 11. Platform Governance & Integrations

### `GET /api/v1/platform/integrations`
Returns verified operational status of third-party services (Razorpay, Twilio, Open-Meteo, MQTT, Cloud Storage).

### `GET /api/v1/platform/audit-logs`
Returns immutable security audit records of all administrative actions.
