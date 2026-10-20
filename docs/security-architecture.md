# Enterprise Security Architecture
**Platform**: SeriCare Multi-Tenant IoT Sericulture Management  
**Architecture Style**: Defense-in-Depth, Zero-Trust Micro-Segmentation  
**Target Throughput**: 10,000,000 Concurrent Users & Fleet Hardware Connectivity  

---

## 1. Architectural Layers & Security Controls

```
                        [ INTERNET CLIENTS ]
          (ESP32 Hardware Nodes, Flutter Mobile, Admin Web)
                                  │
                                  ▼
[ LAYER 1: EDGE & NETWORK SECURITY ]
  ├── Cloudflare / WAF (DDoS Mitigation, TLS 1.3 Termination)
  ├── Strict CORS Policy (Restricted to Authorized Domains & Vercel Preview RegEx)
  ├── Global HTTP Security Headers (HSTS, CSP, X-Frame-Options, X-Content-Type)
  └── Rate Limiting & Abuse Prevention Middleware (Sliding Window In-Memory / Redis)
                                  │
                                  ▼
[ LAYER 2: IDENTITY & ACCESS MANAGEMENT (IAM) ]
  ├── Stateless Cryptographic JWTs (HMAC-SHA256 with Rotatable Secret Keys)
  ├── OAuth 2.0 / OpenID Connect (OIDC) Integration Architecture (Keycloak-ready)
  ├── Role-Based Access Control (RBAC): superadmin, admin, cluster_supervisor, farmer
  └── Multi-Factor Authentication & Account Lockout Throttling
                                  │
                                  ▼
[ LAYER 3: APPLICATION & OBJECT-LEVEL TENANT ISOLATION ]
  ├── BOLA / IDOR Verification on every Resource Access (`verify_shed_access`)
  ├── Safe Actuator Command Lifecycle (REQUESTED -> QUEUED -> SENT -> APPLIED)
  ├── Input Sanitization & Strict Pydantic Request Validation
  └── Comprehensive Security Audit Trail (`audit_logs`)
                                  │
                                  ▼
[ LAYER 4: DATABASE & STORAGE SECURITY ]
  ├── PostgreSQL with Dedicated Least-Privilege Users
  ├── Parameterized SQL Execution via Psycopg2 (Zero Raw String Interpolation)
  ├── Partitioned Timeseries Tables (`shed_telemetry_partitioned`)
  └── Connection Pool Isolation with Strict Statement Timeouts (8000ms max)
```

---

## 2. Identity & Access Management (IAM) Design

### 2.1 Role Matrix & Permissions

| Role | Access Scope | Allowed Operations |
|---|---|---|
| **superadmin** | Cluster-Wide (All Sheds, Farmers, Nodes) | Full CRUD on Farmers, Global Stage Setpoint Configuration, System Metrics, Audit Logs, Emergency Actuator Overrides. |
| **admin / supervisor** | Assigned Regional Cluster | Read/Write on assigned cluster sheds, view telemetry, manage assigned farmers. |
| **farmer** | Assigned Shed (`shed_id`) Only | View assigned shed live microclimate, view 30-log history, update profile, toggle actuators within safety bounds, update silkworm growth stage. |
| **iot_device** | Specific Hardware Node ID | Ingest authenticated telemetry readings (`POST /telemetry/record`), acknowledge queued commands (`POST /control/commands/ack`). |

### 2.2 Token Lifecycle & Session Management
- **Access Tokens**: Short-to-medium lived JWTs containing `sub` (username), `user_id`, and `role`.
- **Token Verification**: Every protected API route extracts and validates signature, expiry (`exp`), and active user status (`is_active = TRUE`) before execution.
- **Session Revocation**: When an administrator deactivates an account (`is_active = FALSE`), all subsequent API calls for that user are immediately rejected with `403 Forbidden`.

---

## 3. High-Scale Concurrency & Resiliency (10M Users)

1. **Partitioned Timeseries Storage**:
   Telemetry logs are stored in PostgreSQL declarative range partitions divided by year and month (`shed_telemetry_yYYYYmMM`). Querying recent telemetry uses indexed partition pruning (`idx_shed_telemetry_yYYYYmMM_shed_time`), preventing full table scans on billions of rows.
2. **Asynchronous Non-Blocking Real-Time Synchronization**:
   Live telemetry updates are broadcast via lightweight in-memory channel mappings (`ws_manager`). Real-time push avoids expensive periodic database polling by mobile and web clients.
3. **Connection Pooling & Timeouts**:
   The PostgreSQL connection pool enforces:
   - Max 20 concurrent persistent pooled connections per container instance.
   - `statement_timeout = '8000ms'` to prevent runaway queries.
   - `lock_timeout = '3000ms'` to eliminate deadlocks.
4. **Stateless Scale-Out**:
   The FastAPI backend maintains zero disk-bound session state, allowing seamless horizontal scaling behind cloud load balancers.
