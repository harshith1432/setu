# Disaster Recovery & Automated Backup Specification
**Recovery Point Objective (RPO)**: <= 1 Hour (Continuous WAL Archiving)  
**Recovery Time Objective (RTO)**: <= 30 Minutes  

---

## 1. Backup Strategy

1. **Automated Continuous WAL Archiving**:
   PostgreSQL Write-Ahead Logging (WAL) enabled with streaming replication to secondary standby.
2. **Daily Logical Backups**:
   Automated daily `pg_dump` of schema, farmer profiles, device registries, and audit logs:
   ```bash
   pg_dump --format=custom --no-owner --no-privileges -f "setu_backup_$(date +%Y%m%d_%H%M%S).dump" "$DATABASE_URL"
   ```
3. **Partition Retention & Archival**:
   Telemetry partitions older than 12 months are exported to encrypted cold object storage (S3 / GCS) and detached from the active database catalog to conserve SSD capacity and query speed.

---

## 2. Restoration & Disaster Recovery Verification

1. **Restoration Drill**:
   ```bash
   # Test restoration to isolated validation instance
   pg_restore --clean --if-exists -d "$TEST_DB_URL" "setu_backup_20261021.dump"
   ```
2. **Data Consistency Audit**:
   Verify record count equality across `users`, `devices`, and `stage_thresholds` after restoration.
3. **Automated Failover**:
   In managed cloud environments (Neon / Render PostgreSQL), multi-AZ failover automatically reroutes application traffic without manual DNS intervention.
