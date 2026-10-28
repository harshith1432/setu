# SeriCare / Setu Enterprise REST API Documentation

Base URL: `/api/v1`  
Interactive Swagger UI: `/docs`  
Redoc API Explorer: `/redoc`

---

## 1. Authentication & Security Endpoints

### `POST /api/v1/auth/login`
Authenticates administrative operators and farmers using JSON credentials. Returns short-lived JWT access token and user role profile.
- **Rate Limit**: 30 requests/minute per client IP.
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
    "user": {
      "id": "usr_admin",
      "username": "admin",
      "role": "superadmin",
      "full_name": "Setu Super Admin",
      "preferred_language": "en"
    }
  }
  ```

### `GET /api/v1/auth/me`
Retrieves authenticated user session profile. Requires `Authorization: Bearer <token>`.

---

## 2. Dashboard & Platform Overview Endpoints

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

## 3. Analytics & Time-Series Endpoints

### `GET /api/v1/analytics/trends?days=7`
**Query Parameters**:
- `days` (integer, default 7, range 1-90): Number of days of historical aggregation.
- **Response**: Day-by-day averages for indoor temperature, humidity, air quality, lux, daily order counts, and revenue.

---

## 4. Products & Inventory Ledger Endpoints

### `GET /api/v1/products`
Lists all commercial equipment with SKU, category, price, and stock levels.

### `POST /api/v1/products`
**Roles**: `superadmin`, `admin`, `sales`  
Creates a new SKU in the catalogue with inventory tracking.

### `POST /api/v1/products/{id}/stock-adjustment`
**Roles**: `superadmin`, `admin`, `sales`  
Adjusts warehouse stock with an immutable ledger entry.

---

## 5. Sales Orders, Subscriptions & Invoicing

### `GET /api/v1/orders`
Lists orders. Supports filtering by `status` and `user_id`. Farmers only receive their own records.

### `GET /api/v1/orders/{order_id}`
Returns order details, itemized product lines, invoice, and payment transaction references.

### `PATCH /api/v1/orders/{order_id}/status`
Transitions order status (`PENDING` → `PAID` → `PROCESSING` → `FULFILLED` → `CANCELLED`).

### `GET /api/v1/subscriptions`
Lists active recurring SaaS contracts and renewal dates.

### `GET /api/v1/invoices`
Lists customer invoices with tax breakdowns (CGST + SGST 18%).

---

## 6. Helpdesk & Support Cases

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

## 7. Installations & Field Engineering

### `GET /api/v1/installations`
Lists field installation jobs with workflow states.

### `POST /api/v1/installations`
Schedules an on-site installation job for a farmer's rearing shed.

### `PATCH /api/v1/installations/{job_id}`
Advances job workflow (`REQUESTED` → `SCHEDULED` → `IN_PROGRESS` → `VERIFICATION` → `COMPLETED`) with mandatory checklist verification.

### `GET /api/v1/installations/team`
Returns roster of certified technicians and current workload.

---

## 8. Guidance & Multilingual Advisory

### `GET /api/v1/guidance?language=kn`
Returns localized rearing guides and CSRTI research recommendations across English, Kannada, Telugu, Hindi, Tamil, and Malayalam.

---

## 9. IoT Telemetry, Sensors & Live Streaming

### `POST /api/v1/telemetry/record`
Ingestion gate for edge IoT gateways. Authenticated via `X-Device-Key` or mTLS client certificate.

### `GET /api/v1/telemetry/live-stream/{shed_id}`
Server-Sent Events (SSE) live stream providing real-time sub-second updates to connected dashboards.

### `GET /api/v1/sensors?shed_id=shed_01`
Returns hardware sensors metadata, pin assignments, and calibration offsets.

### `POST /api/v1/sensors/{sensor_id}/calibrate`
Applies hardware calibration offset (± delta) to sensor probe.

---

## 10. Platform Governance & Integrations

### `GET /api/v1/platform/integrations`
Returns verified operational status of third-party services (Razorpay, Twilio, Open-Meteo, MQTT, Cloud Storage).

### `GET /api/v1/platform/audit-logs`
Returns immutable security audit records of all administrative actions.
