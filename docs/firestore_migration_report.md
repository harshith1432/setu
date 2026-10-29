# SeriCare PostgreSQL to Cloud Firestore Migration Report

**Execution Timestamp:** `2026-10-29T06:33:45.183716+00:00`  
**Target Firebase Project:** `setu-a767c`  
**Execution Mode:** `LIVE COMMITS`  

---

## 1. Migration Summary

- **Total Source PostgreSQL Records:** `17,742`
- **Total Transformed Firestore Documents:** `17,742`
- **Total Reconciliation Errors:** `0`
- **Integrity Status:** `100% RECONCILED & VALIDATED`

---

## 2. Table-by-Collection Verification Matrix

| PostgreSQL Table | Firestore Collection | Source Records | Firestore Documents | Integrity Status | Artifact Dump |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `alerts` | `alerts` | 3 | 3 | ✅ VALIDATED | `docs/migration_dump\alerts.json` |
| `audit_logs` | `audit_logs` | 11,997 | 11,997 | ✅ VALIDATED | `docs/migration_dump\audit_logs.json` |
| `departments` | `departments` | 134 | 134 | ✅ VALIDATED | `docs/migration_dump\departments.json` |
| `device_commands` | `device_commands` | 437 | 437 | ✅ VALIDATED | `docs/migration_dump\device_commands.json` |
| `devices` | `devices` | 5 | 5 | ✅ VALIDATED | `docs/migration_dump\devices.json` |
| `employee_invitations` | `employee_invitations` | 6 | 6 | ✅ VALIDATED | `docs/migration_dump\employee_invitations.json` |
| `employees` | `employees` | 16 | 16 | ✅ VALIDATED | `docs/migration_dump\employees.json` |
| `enquiries` | `enquiries` | 112 | 112 | ✅ VALIDATED | `docs/migration_dump\enquiries.json` |
| `faqs` | `faqs` | 9 | 9 | ✅ VALIDATED | `docs/migration_dump\faqs.json` |
| `guidance_articles` | `guidance_articles` | 4 | 4 | ✅ VALIDATED | `docs/migration_dump\guidance_articles.json` |
| `inventory_movements` | `inventory_movements` | 42 | 42 | ✅ VALIDATED | `docs/migration_dump\inventory_movements.json` |
| `invoices` | `invoices` | 3 | 3 | ✅ VALIDATED | `docs/migration_dump\invoices.json` |
| `order_items` | `order_items` | 89 | 89 | ✅ VALIDATED | `docs/migration_dump\order_items.json` |
| `orders` | `orders` | 18 | 18 | ✅ VALIDATED | `docs/migration_dump\orders.json` |
| `organizations` | `organizations` | 0 | 0 | ✅ VALIDATED | `docs/migration_dump\organizations.json` |
| `payments` | `payments` | 3 | 3 | ✅ VALIDATED | `docs/migration_dump\payments.json` |
| `permissions` | `permissions` | 36 | 36 | ✅ VALIDATED | `docs/migration_dump\permissions.json` |
| `platform_settings` | `platform_settings` | 2 | 2 | ✅ VALIDATED | `docs/migration_dump\platform_settings.json` |
| `products` | `products` | 27 | 27 | ✅ VALIDATED | `docs/migration_dump\products.json` |
| `roles` | `roles` | 15 | 15 | ✅ VALIDATED | `docs/migration_dump\roles.json` |
| `sensors` | `sensors` | 4 | 4 | ✅ VALIDATED | `docs/migration_dump\sensors.json` |
| `shed_telemetry` | `shed_telemetry` | 2,477 | 2,477 | ✅ VALIDATED | `docs/migration_dump\shed_telemetry.json` |
| `sheds` | `sheds` | 3 | 3 | ✅ VALIDATED | `docs/migration_dump\sheds.json` |
| `stage_thresholds` | `stage_thresholds` | 5 | 5 | ✅ VALIDATED | `docs/migration_dump\stage_thresholds.json` |
| `support_messages` | `support_messages` | 4 | 4 | ✅ VALIDATED | `docs/migration_dump\support_messages.json` |
| `support_tickets` | `support_tickets` | 5 | 5 | ✅ VALIDATED | `docs/migration_dump\support_tickets.json` |
| `user_sessions` | `user_sessions` | 2,117 | 2,117 | ✅ VALIDATED | `docs/migration_dump\user_sessions.json` |
| `users` | `users` | 169 | 169 | ✅ VALIDATED | `docs/migration_dump\users.json` |

---

## 3. Data Integrity & Type Conversions

1. **Monetary Precision**: All currency values (`price_minor_units`, `total_amount_minor_units`) preserved in integer minor units (Paise), eliminating IEEE floating-point distortion.
2. **Time-series Telemetry**: Timestamps formatted in standard ISO-8601 UTC representation ready for Firestore Timestamp mapping.
3. **Composite Relationships**: `order_items` embedded inside `orders` for 1-query fetching on mobile & web.
4. **Tenant Isolation**: `organization_id` default (`default_org`) maintained across all user and shed documents.
5. **Security**: Password hashes kept in private user profile fields without exposure in migration logs.
