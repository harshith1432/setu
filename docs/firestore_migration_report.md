# SeriCare PostgreSQL to Cloud Firestore Migration Report

**Execution Timestamp:** `2026-10-29T05:50:14.963169+00:00`  
**Target Firebase Project:** `setu-a767c`  
**Execution Mode:** `DRY-RUN (Validation & Dump)`  

---

## 1. Migration Summary

- **Total Source PostgreSQL Records:** `18,444`
- **Total Transformed Firestore Documents:** `18,444`
- **Total Reconciliation Errors:** `0`
- **Integrity Status:** `100% RECONCILED & VALIDATED`

---

## 2. Table-by-Collection Verification Matrix

| PostgreSQL Table | Firestore Collection | Source Records | Firestore Documents | Integrity Status | Artifact Dump |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `alerts` | `alerts` | 3 | 3 | ✅ VALIDATED | `docs/migration_dump\alerts.json` |
| `audit_logs` | `audit_logs` | 11,686 | 11,686 | ✅ VALIDATED | `docs/migration_dump\audit_logs.json` |
| `departments` | `departments` | 132 | 132 | ✅ VALIDATED | `docs/migration_dump\departments.json` |
| `device_commands` | `device_commands` | 427 | 427 | ✅ VALIDATED | `docs/migration_dump\device_commands.json` |
| `devices` | `devices` | 5 | 5 | ✅ VALIDATED | `docs/migration_dump\devices.json` |
| `employee_invitations` | `employee_invitations` | 58 | 58 | ✅ VALIDATED | `docs/migration_dump\employee_invitations.json` |
| `employees` | `employees` | 68 | 68 | ✅ VALIDATED | `docs/migration_dump\employees.json` |
| `enquiries` | `enquiries` | 110 | 110 | ✅ VALIDATED | `docs/migration_dump\enquiries.json` |
| `faqs` | `faqs` | 9 | 9 | ✅ VALIDATED | `docs/migration_dump\faqs.json` |
| `guidance_articles` | `guidance_articles` | 4 | 4 | ✅ VALIDATED | `docs/migration_dump\guidance_articles.json` |
| `inventory_movements` | `inventory_movements` | 38 | 38 | ✅ VALIDATED | `docs/migration_dump\inventory_movements.json` |
| `invoices` | `invoices` | 23 | 23 | ✅ VALIDATED | `docs/migration_dump\invoices.json` |
| `order_items` | `order_items` | 370 | 370 | ✅ VALIDATED | `docs/migration_dump\order_items.json` |
| `orders` | `orders` | 36 | 36 | ✅ VALIDATED | `docs/migration_dump\orders.json` |
| `organizations` | `organizations` | 0 | 0 | ✅ VALIDATED | `docs/migration_dump\organizations.json` |
| `payments` | `payments` | 23 | 23 | ✅ VALIDATED | `docs/migration_dump\payments.json` |
| `permissions` | `permissions` | 36 | 36 | ✅ VALIDATED | `docs/migration_dump\permissions.json` |
| `platform_settings` | `platform_settings` | 4 | 4 | ✅ VALIDATED | `docs/migration_dump\platform_settings.json` |
| `products` | `products` | 25 | 25 | ✅ VALIDATED | `docs/migration_dump\products.json` |
| `roles` | `roles` | 13 | 13 | ✅ VALIDATED | `docs/migration_dump\roles.json` |
| `sensors` | `sensors` | 4 | 4 | ✅ VALIDATED | `docs/migration_dump\sensors.json` |
| `shed_telemetry` | `shed_telemetry` | 2,471 | 2,471 | ✅ VALIDATED | `docs/migration_dump\shed_telemetry.json` |
| `sheds` | `sheds` | 3 | 3 | ✅ VALIDATED | `docs/migration_dump\sheds.json` |
| `stage_thresholds` | `stage_thresholds` | 5 | 5 | ✅ VALIDATED | `docs/migration_dump\stage_thresholds.json` |
| `support_messages` | `support_messages` | 42 | 42 | ✅ VALIDATED | `docs/migration_dump\support_messages.json` |
| `support_tickets` | `support_tickets` | 21 | 21 | ✅ VALIDATED | `docs/migration_dump\support_tickets.json` |
| `user_sessions` | `user_sessions` | 2,625 | 2,625 | ✅ VALIDATED | `docs/migration_dump\user_sessions.json` |
| `users` | `users` | 203 | 203 | ✅ VALIDATED | `docs/migration_dump\users.json` |

---

## 3. Data Integrity & Type Conversions

1. **Monetary Precision**: All currency values (`price_minor_units`, `total_amount_minor_units`) preserved in integer minor units (Paise), eliminating IEEE floating-point distortion.
2. **Time-series Telemetry**: Timestamps formatted in standard ISO-8601 UTC representation ready for Firestore Timestamp mapping.
3. **Composite Relationships**: `order_items` embedded inside `orders` for 1-query fetching on mobile & web.
4. **Tenant Isolation**: `organization_id` default (`default_org`) maintained across all user and shed documents.
5. **Security**: Password hashes kept in private user profile fields without exposure in migration logs.
