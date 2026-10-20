# Database Security & Partitioned Architecture Specification
**Database Engine**: PostgreSQL 15+ / Supabase / Neon / Managed Cloud SQL  
**ORM / Driver**: Psycopg2 with ThreadedConnectionPool  
**Data Model**: Multi-Tenant Partitioned Timeseries + User / Device Registry  

---

## 1. Principle of Least Privilege (PoLP)

PostgreSQL security is enforced through segregated role privileges:

```sql
-- Application runtime role (Read/Write data, no DDL)
CREATE ROLE setu_app WITH LOGIN PASSWORD 'strong_random_password';
GRANT CONNECT ON DATABASE setu TO setu_app;
GRANT USAGE ON SCHEMA public TO setu_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO setu_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO setu_app;

-- Migration / Deployment role (DDL execution only during release phase)
CREATE ROLE setu_migrator WITH LOGIN PASSWORD 'strong_migration_password';
GRANT ALL PRIVILEGES ON DATABASE setu TO setu_migrator;
```

---

## 2. Partitioned Timeseries Security & Performance

Telemetry data is partitioned by month:
```sql
CREATE TABLE IF NOT EXISTS shed_telemetry_partitioned (
    id BIGSERIAL,
    time TIMESTAMPTZ NOT NULL,
    shed_id VARCHAR(64) NOT NULL,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    air_quality DOUBLE PRECISION,
    light_lux DOUBLE PRECISION,
    outside_temp DOUBLE PRECISION,
    outside_humidity DOUBLE PRECISION,
    cooler_active BOOLEAN DEFAULT FALSE,
    heater_active BOOLEAN DEFAULT FALSE,
    fan_active BOOLEAN DEFAULT FALSE,
    light_active BOOLEAN DEFAULT FALSE,
    light_brightness INT DEFAULT 0,
    PRIMARY KEY (id, time)
) PARTITION BY RANGE (time);
```

Monthly child partitions (e.g. `shed_telemetry_y2026m10`) are created automatically during initialization with dedicated compound indexes:
```sql
CREATE INDEX IF NOT EXISTS idx_shed_telemetry_y2026m10_shed_time 
ON shed_telemetry_y2026m10 (shed_id, time DESC);
```

---

## 3. SQL Injection Defense

1. **Strict Parameterization**:
   All dynamic queries in `db_service.py` pass query arguments via tuple parameters (`%s` placeholders). Raw string formatting (`f"SELECT ... WHERE id = '{user_id}'"`) is strictly prohibited.
2. **Column Name Whitelisting**:
   In dynamic update operations (`update_user_profile`), field names are validated against a strict hardcoded whitelist before insertion into the SQL statement string.

---

## 4. Connection Pool Hardening

```python
# Connection safety timeouts applied to every cursor
cursor.execute("SET statement_timeout = '8000ms'; SET lock_timeout = '3000ms';")
```
- Eliminates thread starvation from unindexed or heavy analytic queries.
- Prevents deadlocks during high-concurrency peak telemetry ingestion periods.
- Eliminates runtime DDL statements (`ALTER TABLE`) inside regular database updates.
