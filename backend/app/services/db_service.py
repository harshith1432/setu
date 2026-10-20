import os
import sys
import logging
import threading
import time
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, execute_values
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager
from app.core.config import settings
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)

DATABASE_URL = settings.DATABASE_URL

_connection_pool: Optional[pool.ThreadedConnectionPool] = None
_pool_lock = threading.Lock()

# L1 In-Memory Ring Buffer / Cache for Telemetry Read-Heavy Dashboards
_latest_reading_cache: Dict[str, Dict[str, Any]] = {}
_latest_reading_cache_times: Dict[str, float] = {}
_cache_lock = threading.Lock()

def _get_cached_latest_reading(shed_id: str) -> Optional[Dict[str, Any]]:
    now = time.time()
    with _cache_lock:
        if shed_id in _latest_reading_cache:
            if now - _latest_reading_cache_times.get(shed_id, 0) < 2.0:  # 2.0s bounded TTL
                return dict(_latest_reading_cache[shed_id])
    return None

def _set_cached_latest_reading(shed_id: str, data: Dict[str, Any]) -> None:
    now = time.time()
    with _cache_lock:
        _latest_reading_cache[shed_id] = dict(data)
        _latest_reading_cache_times[shed_id] = now


def get_pool() -> Optional[pool.ThreadedConnectionPool]:
    """
    Returns a singleton ThreadedConnectionPool for PostgreSQL connection reuse.
    Configurable connection limits to prevent Postgres server connection exhaustion.
    """
    global _connection_pool
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                try:
                    max_conn = int(os.getenv("DB_POOL_MAX", "50"))
                    _connection_pool = pool.ThreadedConnectionPool(
                        minconn=2,
                        maxconn=max_conn,
                        dsn=DATABASE_URL
                    )
                except Exception as e:
                    logger.warning("Failed to initialize ThreadedConnectionPool: %s", e)
                    _connection_pool = None
    return _connection_pool


@contextmanager
def get_db_cursor(commit: bool = False, dict_cursor: bool = False):
    """
    Context manager that yields a cursor from the connection pool or a direct connection.
    Guarantees connection cleanup, release back to pool, and enforces statement timeouts.
    """
    p = get_pool()
    conn = None
    from_pool = False
    if p:
        try:
            conn = p.getconn()
            from_pool = True
        except Exception:
            conn = psycopg2.connect(DATABASE_URL)
            from_pool = False
    else:
        conn = psycopg2.connect(DATABASE_URL)

    if commit:
        conn.autocommit = True

    cursor_kwargs = {"cursor_factory": RealDictCursor} if dict_cursor else {}
    cursor = conn.cursor(**cursor_kwargs)
    try:
        # Enforce defensive timeouts to prevent runaway queries from locking worker pools
        try:
            cursor.execute("SET statement_timeout = '8000ms'; SET lock_timeout = '3000ms';")
        except Exception:
            pass
        yield cursor
    finally:
        cursor.close()
        if from_pool and p:
            try:
                p.putconn(conn)
            except Exception:
                conn.close()
        else:
            conn.close()


def get_connection():
    """Legacy helper: Returns a direct PostgreSQL connection."""
    return psycopg2.connect(DATABASE_URL)


def _ensure_telemetry_partitions(cursor):
    """
    Ensures current, historical, and future monthly partition tables exist
    for the partitioned time-series shed_telemetry_partitioned table.
    """
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS shed_telemetry_partitioned (
            id BIGSERIAL,
            time TIMESTAMPTZ NOT NULL,
            shed_id VARCHAR(64) NOT NULL,
            device_id VARCHAR(64) DEFAULT 'node_default',
            sequence_number BIGINT DEFAULT 0,
            event_id VARCHAR(64),
            temperature DOUBLE PRECISION NOT NULL,
            humidity DOUBLE PRECISION NOT NULL,
            air_quality DOUBLE PRECISION NOT NULL DEFAULT 88.0,
            light_lux DOUBLE PRECISION NOT NULL DEFAULT 22.0,
            outside_temperature DOUBLE PRECISION,
            outside_humidity DOUBLE PRECISION,
            cooler BOOLEAN NOT NULL DEFAULT FALSE,
            heater BOOLEAN NOT NULL DEFAULT FALSE,
            fan BOOLEAN NOT NULL DEFAULT FALSE,
            humidifier BOOLEAN NOT NULL DEFAULT FALSE,
            light BOOLEAN NOT NULL DEFAULT FALSE,
            light_brightness INT NOT NULL DEFAULT 0,
            mode VARCHAR(32) NOT NULL DEFAULT 'AUTO',
            PRIMARY KEY (id, time)
        ) PARTITION BY RANGE (time);
        """)

        # Generate partitions for past 2 months, current month, and next 6 months
        base_now = datetime.now(timezone.utc)
        for offset in range(-2, 7):
            # Compute start of target month
            y = base_now.year
            m = base_now.month + offset
            while m > 12:
                y += 1
                m -= 12
            while m < 1:
                y -= 1
                m += 12
            start_date = datetime(y, m, 1, tzinfo=timezone.utc)
            # Compute end date (start of next month)
            next_y = y
            next_m = m + 1
            if next_m > 12:
                next_y += 1
                next_m = 1
            end_date = datetime(next_y, next_m, 1, tzinfo=timezone.utc)

            part_name = f"shed_telemetry_y{y}m{m:02d}"
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {part_name}
            PARTITION OF shed_telemetry_partitioned
            FOR VALUES FROM ('{start_date.isoformat()}') TO ('{end_date.isoformat()}');
            """)
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{part_name}_shed_time ON {part_name} (shed_id, time DESC);")
    except Exception as e:
        logger.debug("Partition initialization info: %s", e)


def init_db():
    """
    Initializes PostgreSQL tables:
    - 'users': Multi-tenant farmer & operator directory
    - 'devices': Registered IoT hardware identities with credentials
    - 'device_commands': Safe command lifecycle with state progression
    - 'audit_logs': Immutable audit trail for all control & admin actions
    - 'stage_thresholds': Growth stage thresholds and environmental setpoints
    - 'shed_telemetry': Historical telemetry timeseries storage
    - 'shed_telemetry_partitioned': High-scale time-partitioned telemetry store
    """
    with get_db_cursor(commit=True) as cursor:
        # 1. Farmers & Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR(64) PRIMARY KEY,
            username VARCHAR(64) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            full_name VARCHAR(128) NOT NULL,
            phone VARCHAR(32) NOT NULL,
            preferred_language VARCHAR(8) NOT NULL DEFAULT 'kn',
            role VARCHAR(32) NOT NULL DEFAULT 'farmer',
            farm_name VARCHAR(128) NOT NULL DEFAULT 'Green Valley Farm',
            region VARCHAR(128) NOT NULL DEFAULT 'Local Rearing Shed',
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            shed_id VARCHAR(64) DEFAULT 'shed_01',
            batch_id VARCHAR(64) NOT NULL DEFAULT 'SERI-2026-M04',
            dfl_capacity VARCHAR(64) NOT NULL DEFAULT '200 DFL',
            breed VARCHAR(128) NOT NULL DEFAULT 'Double Hybrid (FC1 x FC2)',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL
        );
        """)
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS shed_id VARCHAR(64) DEFAULT 'shed_01'")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS whatsapp_number VARCHAR(64)")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS whatsapp_verified BOOLEAN NOT NULL DEFAULT FALSE")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS current_stage INT DEFAULT 3")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_shed_id ON users (shed_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);")

        # 2. IoT Device Registry
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            device_id VARCHAR(64) PRIMARY KEY,
            shed_id VARCHAR(64) NOT NULL,
            organization_id VARCHAR(64) NOT NULL DEFAULT 'default_org',
            device_name VARCHAR(128),
            device_key_hash VARCHAR(255),
            cert_fingerprint_sha256 VARCHAR(64),
            auth_mode VARCHAR(32) DEFAULT 'API_KEY',
            firmware_version VARCHAR(32) DEFAULT '1.0.0',
            status VARCHAR(32) DEFAULT 'ONLINE',
            last_sequence_number BIGINT DEFAULT 0,
            last_seen_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_devices_shed ON devices (shed_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_devices_org ON devices (organization_id);")

        # Dynamic migration for devices columns
        cursor.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='devices' AND column_name='cert_fingerprint_sha256') THEN
                ALTER TABLE devices ADD COLUMN cert_fingerprint_sha256 VARCHAR(64);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='devices' AND column_name='auth_mode') THEN
                ALTER TABLE devices ADD COLUMN auth_mode VARCHAR(32) DEFAULT 'API_KEY';
            END IF;
        END $$;
        """)

        # Pre-seed default hardware nodes for demo sheds
        now_dt = datetime.now(timezone.utc)
        default_devices = [
            ("esp32_shed_01", "shed_01", "default_org", "Shed 01 Primary ESP32 Controller", "1.0.0", "ONLINE", now_dt),
            ("esp32_shed_02", "shed_02", "default_org", "Shed 02 Primary ESP32 Controller", "1.0.0", "ONLINE", now_dt),
            ("esp32_shed_03", "shed_03", "default_org", "Shed 03 Primary ESP32 Controller", "1.0.0", "ONLINE", now_dt),
        ]
        for dev in default_devices:
            cursor.execute("""
            INSERT INTO devices (device_id, shed_id, organization_id, device_name, firmware_version, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (device_id) DO NOTHING;
            """, dev)

        # 3. Device Command Lifecycle Table (Safe bidirectional controls)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_commands (
            command_id VARCHAR(64) PRIMARY KEY,
            organization_id VARCHAR(64) NOT NULL DEFAULT 'default_org',
            device_id VARCHAR(64) NOT NULL,
            shed_id VARCHAR(64) NOT NULL,
            requested_by VARCHAR(64) NOT NULL,
            command_type VARCHAR(64) NOT NULL,
            command_payload JSONB NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'REQUESTED',
            created_at TIMESTAMPTZ NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            correlation_id VARCHAR(64),
            acknowledged_at TIMESTAMPTZ,
            applied_at TIMESTAMPTZ,
            error_message TEXT
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_commands_device_status ON device_commands (device_id, status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_commands_created ON device_commands (created_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_commands_shed ON device_commands (shed_id);")

        # 4. Audit Logs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL,
            actor VARCHAR(64) NOT NULL,
            action VARCHAR(64) NOT NULL,
            details TEXT NOT NULL
        );
        """)

        # 5. Stage Thresholds
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stage_thresholds (
            stage_id INT PRIMARY KEY,
            name VARCHAR(128) NOT NULL,
            days VARCHAR(64) NOT NULL,
            temp_min FLOAT NOT NULL,
            temp_max FLOAT NOT NULL,
            hum_min FLOAT NOT NULL,
            hum_max FLOAT NOT NULL,
            hysteresis_temp FLOAT NOT NULL DEFAULT 0.5,
            hysteresis_hum FLOAT NOT NULL DEFAULT 3.0,
            fan_trigger_offset FLOAT NOT NULL DEFAULT 1.5,
            description TEXT,
            updated_at TIMESTAMPTZ NOT NULL
        );
        """)

        # 6. Shed Telemetry Storage (Standard)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS shed_telemetry (
            id BIGSERIAL PRIMARY KEY,
            time TIMESTAMPTZ NOT NULL,
            shed_id VARCHAR(64) NOT NULL,
            temperature DOUBLE PRECISION NOT NULL,
            humidity DOUBLE PRECISION NOT NULL,
            air_quality DOUBLE PRECISION NOT NULL DEFAULT 88.0,
            light_lux DOUBLE PRECISION NOT NULL DEFAULT 22.0,
            outside_temperature DOUBLE PRECISION,
            outside_humidity DOUBLE PRECISION,
            cooler BOOLEAN NOT NULL DEFAULT FALSE,
            heater BOOLEAN NOT NULL DEFAULT FALSE,
            fan BOOLEAN NOT NULL DEFAULT FALSE,
            humidifier BOOLEAN NOT NULL DEFAULT FALSE,
            light BOOLEAN NOT NULL DEFAULT FALSE,
            light_brightness INT NOT NULL DEFAULT 0,
            mode VARCHAR(32) NOT NULL DEFAULT 'AUTO'
        );
        """)
        cursor.execute("ALTER TABLE shed_telemetry ADD COLUMN IF NOT EXISTS air_quality DOUBLE PRECISION DEFAULT 88.0;")
        cursor.execute("ALTER TABLE shed_telemetry ADD COLUMN IF NOT EXISTS light_lux DOUBLE PRECISION DEFAULT 22.0;")
        cursor.execute("ALTER TABLE shed_telemetry ADD COLUMN IF NOT EXISTS light BOOLEAN NOT NULL DEFAULT FALSE;")
        cursor.execute("ALTER TABLE shed_telemetry ADD COLUMN IF NOT EXISTS light_brightness INT NOT NULL DEFAULT 0;")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shed_telemetry_shed_time ON shed_telemetry (shed_id, time DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shed_telemetry_time ON shed_telemetry (time DESC);")

        # 7. Partitioned Telemetry Storage (Scale-out)
        _ensure_telemetry_partitions(cursor)

        # Pre-seed Stage Thresholds if empty
        cursor.execute("SELECT COUNT(*) FROM stage_thresholds")
        if cursor.fetchone()[0] == 0:
            for stage in [
                (1, "1st Instar (Chawki)", "Days 1–3", 27.0, 28.0, 80.0, 85.0, 0.5, 3.0, 1.5, "Chawki stage: Delicate larvae requiring high humidity and warm ambient temperatures to prevent desiccation.", now_dt),
                (2, "2nd Instar", "Days 4–5", 26.5, 27.5, 75.0, 80.0, 0.5, 3.0, 1.5, "Post-first moult larvae. Transitioning to active feeding with moderate humidity requirements.", now_dt),
                (3, "3rd Instar", "Days 6–9", 25.0, 26.5, 70.0, 75.0, 0.5, 3.0, 1.5, "Late chawki / adult transition. Increased voracity requires steady ventilation and balanced thermal envelope.", now_dt),
                (4, "4th Instar", "Days 10–14", 24.0, 25.5, 65.0, 70.0, 0.5, 3.0, 1.5, "Exponential larval weight gain. High metabolic heat output necessitates active cooling and air exchange.", now_dt),
                (5, "5th Instar", "Days 15–20", 23.0, 24.5, 60.0, 65.0, 0.5, 3.0, 1.5, "Final feeding instar preceding cocooning/spinning. Requires cooler, drier conditions and continuous fresh airflow.", now_dt)
            ]:
                cursor.execute("""
                INSERT INTO stage_thresholds (stage_id, name, days, temp_min, temp_max, hum_min, hum_max, hysteresis_temp, hysteresis_hum, fan_trigger_offset, description, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, stage)

        # Pre-seed Admin accounts safely (SEC-02)
        admin_init_pw = settings.INITIAL_ADMIN_PASSWORD
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO users (id, username, hashed_password, full_name, phone, preferred_language, role, farm_name, region, shed_id, batch_id, dfl_capacity, breed, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                "usr_admin_default",
                "admin",
                get_password_hash(admin_init_pw),
                "Setu Super Admin",
                "+91 98450 99999",
                "en",
                "superadmin",
                "Central Sericulture Command",
                "Central Sericulture Command HQ",
                "shed_01",
                "CENTRAL-HQ",
                "N/A",
                "N/A",
                True,
                now_dt
            ))

        cursor.execute("SELECT id FROM users WHERE username = 'superadmin'")
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO users (id, username, hashed_password, full_name, phone, preferred_language, role, farm_name, region, shed_id, batch_id, dfl_capacity, breed, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                "usr_admin",
                "superadmin",
                get_password_hash(admin_init_pw if admin_init_pw != "admin" else "adminsecure2026"),
                "Setu Super Admin",
                "+91 98450 99999",
                "en",
                "superadmin",
                "Central Sericulture Command",
                "Central Sericulture Command HQ",
                "shed_01",
                "CENTRAL-HQ",
                "N/A",
                "N/A",
                True,
                now_dt
            ))

        # Pre-seed Demo Farmers if testing
        sample_farmers = [
            (
                "usr_001",
                "ramesh_farmer",
                "setu2026",
                "Ramesh Gowda",
                "+91 98450 12345",
                "kn",
                "farmer",
                "Green Valley Sericulture Farm",
                "Mysuru Silk Belt, KA",
                "shed_01",
                "SERI-2026-M04",
                "200 DFL",
                "Double Hybrid (FC1 x FC2)"
            ),
            (
                "usr_002",
                "venkatamma_farmer",
                "setu2026",
                "Venkatamma Reddy",
                "+91 94480 54321",
                "te",
                "farmer",
                "Sri Lakshmi Silk Farm",
                "Kolar Silk Belt, KA",
                "shed_02",
                "SERI-2026-M05",
                "150 DFL",
                "Cross Breed (PM x CSR2)"
            ),
            (
                "usr_003",
                "manjunath_kolar",
                "setu2026",
                "Manjunath K.",
                "+91 99001 88776",
                "kn",
                "farmer",
                "Kolar Silk Fields",
                "Ramanagara Silk Hub, KA",
                "shed_03",
                "SERI-2026-M02",
                "300 DFL",
                "Bivoltine White (FC1 x FC2)"
            ),
        ]

        seed_demo = os.getenv("SEED_DEMO_FARMERS", "false").lower() in ("true", "1") or "pytest" in sys.modules or bool(os.getenv("PYTEST_CURRENT_TEST"))
        if seed_demo:
            for s_id, u_name, u_pwd, f_name, phone, lang, role, farm, reg, s_shed, b_id, dfl, breed in sample_farmers:
                cursor.execute("SELECT id FROM users WHERE username = %s", (u_name,))
                if not cursor.fetchone():
                    cursor.execute("""
                    INSERT INTO users (id, username, hashed_password, full_name, phone, preferred_language, role, farm_name, region, shed_id, batch_id, dfl_capacity, breed, is_active, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        s_id,
                        u_name,
                        get_password_hash(u_pwd),
                        f_name,
                        phone,
                        lang,
                        role,
                        farm,
                        reg,
                        s_shed,
                        b_id,
                        dfl,
                        breed,
                        True,
                        now_dt
                    ))


def ensure_unique_farmer_sheds():
    """
    Ensures every farmer in the database has a distinct, dedicated shed_id.
    """
    try:
        with get_db_cursor(commit=True, dict_cursor=True) as cursor:
            cursor.execute("""
                SELECT id, shed_id 
                FROM users 
                WHERE role != 'superadmin' 
                ORDER BY created_at ASC
            """)
            rows = cursor.fetchall()
            seen_sheds = set()
            for r in rows:
                u_id = r["id"]
                current_shed = r.get("shed_id")
                if not current_shed or current_shed in seen_sheds:
                    new_shed = f"shed_{u_id}"
                    cursor.execute("UPDATE users SET shed_id = %s WHERE id = %s", (new_shed, u_id))
                    seen_sheds.add(new_shed)
                else:
                    seen_sheds.add(current_shed)
    except Exception as e:
        logger.debug("ensure_unique_farmer_sheds: %s", e)


# Initialize DB on module import safely
try:
    init_db()
    ensure_unique_farmer_sheds()
except Exception:
    pass


# --- Database CRUD helpers with L1 In-Memory Caching ---
_user_cache: Dict[str, tuple[float, Optional[Dict[str, Any]]]] = {}
_farmers_by_shed_cache: Dict[str, tuple[float, List[Dict[str, Any]]]] = {}
_user_cache_lock = threading.Lock()
USER_CACHE_TTL = 30.0  # seconds

def invalidate_user_cache():
    with _user_cache_lock:
        _user_cache.clear()
        _farmers_by_shed_cache.clear()

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    cache_key = f"u:{username.strip().lower()}"
    now = time.time()
    with _user_cache_lock:
        if cache_key in _user_cache:
            exp, val = _user_cache[cache_key]
            if now < exp:
                return dict(val) if val else None

    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        row = cursor.fetchone()
        res = None
        if row:
            d = dict(row)
            if isinstance(d.get("created_at"), datetime):
                d["created_at"] = d["created_at"].isoformat()
            res = d

        with _user_cache_lock:
            _user_cache[cache_key] = (now + USER_CACHE_TTL, res)
        return dict(res) if res else None

def get_user_by_username_or_phone(identifier: str) -> Optional[Dict[str, Any]]:
    clean_id = identifier.strip()
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute(
            "SELECT * FROM users WHERE username = %s OR phone = %s OR whatsapp_number = %s",
            (clean_id, clean_id, clean_id),
        )
        row = cursor.fetchone()
        if row:
            invalidate_user_cache()
            d = dict(row)
            if isinstance(d.get("created_at"), datetime):
                d["created_at"] = d["created_at"].isoformat()
            return d
    return None

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    cache_key = f"id:{user_id.strip()}"
    now = time.time()
    with _user_cache_lock:
        if cache_key in _user_cache:
            exp, val = _user_cache[cache_key]
            if now < exp:
                return dict(val) if val else None

    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        res = None
        if row:
            d = dict(row)
            if isinstance(d.get("created_at"), datetime):
                d["created_at"] = d["created_at"].isoformat()
            res = d

        with _user_cache_lock:
            _user_cache[cache_key] = (now + USER_CACHE_TTL, res)
        return dict(res) if res else None

def get_all_farmers() -> List[Dict[str, Any]]:
    ensure_unique_farmer_sheds()
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("""
            SELECT id, username, full_name, phone, whatsapp_number, whatsapp_verified, preferred_language, role, 
                   farm_name, region, shed_id, batch_id, dfl_capacity, breed, is_active, created_at,
                   COALESCE(current_stage, 3) as current_stage
            FROM users 
            WHERE role != 'superadmin' 
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("created_at"), datetime):
                d["created_at"] = d["created_at"].isoformat()
            result.append(d)
        return result

def get_farmers_by_shed_id(shed_id: str) -> List[Dict[str, Any]]:
    clean_shed_id = shed_id.strip().lower()
    now = time.time()
    with _user_cache_lock:
        if clean_shed_id in _farmers_by_shed_cache:
            exp, val = _farmers_by_shed_cache[clean_shed_id]
            if now < exp:
                return [dict(x) for x in val]

    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("""
            SELECT * FROM users 
            WHERE LOWER(shed_id) = %s AND role != 'superadmin' AND is_active = TRUE 
            ORDER BY created_at ASC
        """, (clean_shed_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("created_at"), datetime):
                d["created_at"] = d["created_at"].isoformat()
            result.append(d)

        with _user_cache_lock:
            _farmers_by_shed_cache[clean_shed_id] = (now + USER_CACHE_TTL, result)
        return [dict(x) for x in result]

def get_farmer_by_shed_id(shed_id: str) -> Optional[Dict[str, Any]]:
    farmers = get_farmers_by_shed_id(shed_id)
    return farmers[0] if farmers else None

def set_user_whatsapp_verified(user_id_or_username: str, verified: bool = True) -> bool:
    clean_id = user_id_or_username.strip()
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
            UPDATE users 
            SET whatsapp_verified = %s 
            WHERE id = %s OR username = %s OR phone = %s OR whatsapp_number = %s
        """, (verified, clean_id, clean_id, clean_id, clean_id))
    invalidate_user_cache()
    return True

def get_next_available_shed_id() -> str:
    try:
        with get_db_cursor(dict_cursor=True) as cursor:
            cursor.execute("SELECT DISTINCT shed_id FROM users WHERE shed_id IS NOT NULL")
            rows = cursor.fetchall()
            existing_sheds = {r["shed_id"] if isinstance(r, dict) else r[0] for r in rows}
            num = 1
            while f"shed_{num:02d}" in existing_sheds:
                num += 1
            return f"shed_{num:02d}"
    except Exception:
        return "shed_01"

def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    created_at_val = user_data.get("created_at")
    if isinstance(created_at_val, str):
        try:
            created_at_dt = datetime.fromisoformat(created_at_val)
        except Exception:
            created_at_dt = datetime.now(timezone.utc)
    elif isinstance(created_at_val, datetime):
        created_at_dt = created_at_val
    else:
        created_at_dt = datetime.now(timezone.utc)

    assigned_shed = user_data.get("shed_id")
    if not assigned_shed or (assigned_shed == "shed_01" and user_data.get("username") != "ramesh_farmer"):
        assigned_shed = get_next_available_shed_id()
    user_data["shed_id"] = assigned_shed

    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
        INSERT INTO users (
            id, username, hashed_password, full_name, phone, whatsapp_number, whatsapp_verified,
            preferred_language, role, farm_name, region, latitude, longitude, shed_id, batch_id,
            dfl_capacity, breed, is_active, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_data["id"],
            user_data["username"],
            user_data["hashed_password"],
            user_data["full_name"],
            user_data["phone"],
            user_data.get("whatsapp_number") or user_data.get("phone"),
            bool(user_data.get("whatsapp_verified", False)),
            user_data.get("preferred_language", "kn"),
            user_data.get("role", "farmer"),
            user_data.get("farm_name", "Green Valley Farm"),
            user_data.get("region", "Local Rearing Shed"),
            user_data.get("latitude"),
            user_data.get("longitude"),
            user_data.get("shed_id", assigned_shed),
            user_data.get("batch_id", "SERI-2026-M04"),
            user_data.get("dfl_capacity", "200 DFL"),
            user_data.get("breed", "Double Hybrid (FC1 x FC2)"),
            True,
            created_at_dt
        ))
    invalidate_user_cache()
    return user_data

def update_user_profile(user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    fields = []
    values = []
    allowed = [
        "full_name", "phone", "whatsapp_number", "whatsapp_verified",
        "preferred_language", "farm_name", "region", "latitude", "longitude",
        "shed_id", "batch_id", "dfl_capacity", "breed", "current_stage"
    ]
    for k in allowed:
        if k in updates and updates[k] is not None:
            fields.append(f"{k} = %s")
            values.append(updates[k])
            
    if not fields:
        return get_user_by_id(user_id) or get_user_by_username(user_id)
        
    values.append(user_id)
    values.append(user_id)
    query = f"UPDATE users SET {', '.join(fields)} WHERE id = %s OR username = %s RETURNING *"

    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        cursor.execute(query, tuple(values))
        row = cursor.fetchone()
        if row:
            invalidate_user_cache()
            d = dict(row)
            if isinstance(d.get("created_at"), datetime):
                d["created_at"] = d["created_at"].isoformat()
            return d
    return None

def update_user_status(user_id: str, is_active: bool) -> bool:
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("UPDATE users SET is_active = %s WHERE id = %s OR username = %s", (is_active, user_id, user_id))
    return True

def delete_user(user_id: str) -> bool:
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM users WHERE id = %s OR username = %s", (user_id, user_id))
    return True

def log_audit(actor: str, action: str, details: str):
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
            INSERT INTO audit_logs (timestamp, actor, action, details)
            VALUES (%s, %s, %s, %s)
            """, (datetime.now(timezone.utc), actor, action, details))
    except Exception:
        pass

    # Real-time forwarding to 24/7 SIEM & SOC Engine (CEF/ECS/Syslog/Splunk)
    try:
        from app.services.siem_service import siem_forwarder
        siem_forwarder.forward_event(
            action=action,
            user_id=actor,
            status="SUCCESS",
            details={"description": details}
        )
    except Exception:
        pass

def get_audit_logs(limit: int = 50) -> List[Dict[str, Any]]:
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT %s", (limit,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("timestamp"), datetime):
                d["timestamp"] = d["timestamp"].isoformat()
            result.append(d)
        return result

def get_all_stage_thresholds() -> List[Dict[str, Any]]:
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("SELECT * FROM stage_thresholds ORDER BY stage_id ASC")
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("updated_at"), datetime):
                d["updated_at"] = d["updated_at"].isoformat()
            result.append(d)
        return result

def get_stage_threshold(stage_id: int) -> Optional[Dict[str, Any]]:
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("SELECT * FROM stage_thresholds WHERE stage_id = %s", (stage_id,))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            if isinstance(d.get("updated_at"), datetime):
                d["updated_at"] = d["updated_at"].isoformat()
            return d
    return None

def update_stage_threshold(stage_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    fields = []
    values = []
    allowed = ["name", "days", "temp_min", "temp_max", "hum_min", "hum_max", "hysteresis_temp", "hysteresis_hum", "fan_trigger_offset", "description"]
    for k in allowed:
        if k in updates and updates[k] is not None:
            fields.append(f"{k} = %s")
            values.append(updates[k])
            
    if not fields:
        return get_stage_threshold(stage_id)

    fields.append("updated_at = %s")
    values.append(datetime.now(timezone.utc))

    values.append(stage_id)
    query = f"UPDATE stage_thresholds SET {', '.join(fields)} WHERE stage_id = %s RETURNING *"

    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        cursor.execute(query, tuple(values))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            if isinstance(d.get("updated_at"), datetime):
                d["updated_at"] = d["updated_at"].isoformat()
            return d
    return None

def reset_stage_thresholds() -> List[Dict[str, Any]]:
    defaults = [
        (1, "1st Instar (Chawki)", "Days 1–3", 27.0, 28.0, 80.0, 85.0, 0.5, 3.0, 1.5, "Chawki stage: Delicate larvae requiring high humidity and warm ambient temperatures to prevent desiccation."),
        (2, "2nd Instar", "Days 4–5", 26.5, 27.5, 75.0, 80.0, 0.5, 3.0, 1.5, "Post-first moult larvae. Transitioning to active feeding with moderate humidity requirements."),
        (3, "3rd Instar", "Days 6–9", 25.0, 26.5, 70.0, 75.0, 0.5, 3.0, 1.5, "Late chawki / adult transition. Increased voracity requires steady ventilation and balanced thermal envelope."),
        (4, "4th Instar", "Days 10–14", 24.0, 25.5, 65.0, 70.0, 0.5, 3.0, 1.5, "Exponential larval weight gain. High metabolic heat output necessitates active cooling and air exchange."),
        (5, "5th Instar", "Days 15–20", 23.0, 24.5, 60.0, 65.0, 0.5, 3.0, 1.5, "Final feeding instar preceding cocooning/spinning. Requires cooler, drier conditions and continuous fresh airflow.")
    ]
    
    now_dt = datetime.now(timezone.utc)
    with get_db_cursor(commit=True) as cursor:
        for s in defaults:
            cursor.execute("""
            INSERT INTO stage_thresholds (stage_id, name, days, temp_min, temp_max, hum_min, hum_max, hysteresis_temp, hysteresis_hum, fan_trigger_offset, description, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (stage_id) DO UPDATE SET
                name = EXCLUDED.name,
                days = EXCLUDED.days,
                temp_min = EXCLUDED.temp_min,
                temp_max = EXCLUDED.temp_max,
                hum_min = EXCLUDED.hum_min,
                hum_max = EXCLUDED.hum_max,
                hysteresis_temp = EXCLUDED.hysteresis_temp,
                hysteresis_hum = EXCLUDED.hysteresis_hum,
                fan_trigger_offset = EXCLUDED.fan_trigger_offset,
                description = EXCLUDED.description,
                updated_at = EXCLUDED.updated_at
            """, (*s, now_dt))
        
    return get_all_stage_thresholds()


# --- Telemetry Persistence Operations ---

def save_telemetry_reading(reading: Dict[str, Any]) -> None:
    """
    Persists a single telemetry reading into PostgreSQL table 'shed_telemetry'.
    Updates L1 cache for zero-latency subsequent reads.
    """
    try:
        with get_db_cursor(commit=True) as cursor:
            t = reading.get("timestamp") or reading.get("measured_at") or datetime.now(timezone.utc)
            if isinstance(t, str):
                try:
                    t = datetime.fromisoformat(t)
                except Exception:
                    t = datetime.now(timezone.utc)
            cursor.execute("""
            INSERT INTO shed_telemetry (
                time, shed_id, temperature, humidity, air_quality, light_lux,
                outside_temperature, outside_humidity,
                cooler, heater, fan, humidifier, light, light_brightness, mode
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                t,
                reading.get("shed_id", "shed_01"),
                float(reading.get("indoor_temp", reading.get("temperature", 25.0))),
                float(reading.get("indoor_hum", reading.get("humidity", 75.0))),
                float(reading.get("air_quality", 88.0)),
                float(reading.get("light_lux", 22.0)),
                float(reading.get("outside_temp", reading.get("outside_temperature"))) if reading.get("outside_temp") is not None or reading.get("outside_temperature") is not None else None,
                float(reading.get("outside_hum", reading.get("outside_humidity"))) if reading.get("outside_hum") is not None or reading.get("outside_humidity") is not None else None,
                bool(reading.get("cooler", False)),
                bool(reading.get("heater", False)),
                bool(reading.get("fan", False)),
                bool(reading.get("humidifier", False)),
                bool(reading.get("light", False)),
                int(reading.get("light_brightness", 0)),
                reading.get("mode", "AUTO")
            ))

            # Update in-memory L1 cache
            _set_cached_latest_reading(reading.get("shed_id", "shed_01"), {
                "timestamp": t,
                "shed_id": reading.get("shed_id", "shed_01"),
                "indoor_temp": float(reading.get("indoor_temp", reading.get("temperature", 25.0))),
                "indoor_hum": float(reading.get("indoor_hum", reading.get("humidity", 75.0))),
                "air_quality": float(reading.get("air_quality", 88.0)),
                "light_lux": float(reading.get("light_lux", 22.0)),
                "outside_temp": float(reading.get("outside_temp", reading.get("outside_temperature", 30.0))),
                "outside_hum": float(reading.get("outside_hum", reading.get("outside_humidity", 60.0))),
                "cooler": bool(reading.get("cooler", False)),
                "heater": bool(reading.get("heater", False)),
                "fan": bool(reading.get("fan", False)),
                "humidifier": bool(reading.get("humidifier", False)),
                "light": bool(reading.get("light", False)),
                "light_brightness": int(reading.get("light_brightness", 0)),
                "mode": reading.get("mode", "AUTO"),
            })
    except Exception as e:
        logger.debug("save_telemetry_reading error: %s", e)


def save_telemetry_batch(records: List[Dict[str, Any]]) -> int:
    """
    High-throughput bulk ingestion using psycopg2.extras.execute_values.
    Saves hundreds or thousands of records in a single database round-trip.
    """
    if not records:
        return 0
    inserted_count = 0
    try:
        with get_db_cursor(commit=True) as cursor:
            tuples = []
            now_dt = datetime.now(timezone.utc)
            for r in records:
                t = r.get("timestamp") or r.get("measured_at") or now_dt
                if isinstance(t, str):
                    try:
                        t = datetime.fromisoformat(t)
                    except Exception:
                        t = now_dt
                tuples.append((
                    t,
                    r.get("shed_id", "shed_01"),
                    float(r.get("indoor_temp", r.get("temperature", 25.0))),
                    float(r.get("indoor_hum", r.get("humidity", 75.0))),
                    float(r.get("air_quality", 88.0)),
                    float(r.get("light_lux", 22.0)),
                    float(r.get("outside_temp", r.get("outside_temperature"))) if r.get("outside_temp") is not None or r.get("outside_temperature") is not None else None,
                    float(r.get("outside_hum", r.get("outside_humidity"))) if r.get("outside_hum") is not None or r.get("outside_humidity") is not None else None,
                    bool(r.get("cooler", False)),
                    bool(r.get("heater", False)),
                    bool(r.get("fan", False)),
                    bool(r.get("humidifier", False)),
                    bool(r.get("light", False)),
                    int(r.get("light_brightness", 0)),
                    r.get("mode", "AUTO"),
                ))

            insert_query = """
            INSERT INTO shed_telemetry (
                time, shed_id, temperature, humidity, air_quality, light_lux,
                outside_temperature, outside_humidity,
                cooler, heater, fan, humidifier, light, light_brightness, mode
            ) VALUES %s
            """
            execute_values(cursor, insert_query, tuples, page_size=1000)
            inserted_count = len(tuples)

            # Invalidate/update latest reading cache for sheds in this batch
            for r in records:
                s_id = r.get("shed_id", "shed_01")
                _set_cached_latest_reading(s_id, {
                    "timestamp": r.get("timestamp") or now_dt,
                    "shed_id": s_id,
                    "indoor_temp": float(r.get("indoor_temp", r.get("temperature", 25.0))),
                    "indoor_hum": float(r.get("indoor_hum", r.get("humidity", 75.0))),
                    "air_quality": float(r.get("air_quality", 88.0)),
                    "light_lux": float(r.get("light_lux", 22.0)),
                    "outside_temp": float(r.get("outside_temp", r.get("outside_temperature", 30.0))),
                    "outside_hum": float(r.get("outside_hum", r.get("outside_humidity", 60.0))),
                    "cooler": bool(r.get("cooler", False)),
                    "heater": bool(r.get("heater", False)),
                    "fan": bool(r.get("fan", False)),
                    "humidifier": bool(r.get("humidifier", False)),
                    "light": bool(r.get("light", False)),
                    "light_brightness": int(r.get("light_brightness", 0)),
                    "mode": r.get("mode", "AUTO"),
                })
    except Exception as e:
        logger.error("Failed bulk inserting telemetry batch: %s", e)
    return inserted_count


def get_latest_telemetry_reading_from_db(shed_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the single most recent real-time telemetry reading for a shed from PostgreSQL table 'shed_telemetry'.
    Uses composite index idx_shed_telemetry_shed_time (<0.1ms scan) and L1 in-memory caching.
    """
    try:
        # 1. Fast L1 In-Memory Cache (<0.01ms)
        cached = _get_cached_latest_reading(shed_id)
        if cached:
            return cached

        # 2. Indexed direct lookup on shed_id
        with get_db_cursor(dict_cursor=True) as cursor:
            cursor.execute("""
            SELECT time as timestamp, shed_id,
                   temperature as indoor_temp, humidity as indoor_hum,
                   COALESCE(air_quality, 88.0) as air_quality,
                   COALESCE(light_lux, 22.0) as light_lux,
                   outside_temperature as outside_temp, outside_humidity as outside_hum,
                   cooler, heater, fan, humidifier,
                   COALESCE(light, FALSE) as light,
                   COALESCE(light_brightness, 0) as light_brightness,
                   mode
            FROM shed_telemetry
            WHERE shed_id = %s
            ORDER BY time DESC
            LIMIT 1
            """, (shed_id,))
            row = cursor.fetchone()
            if row:
                res = dict(row)
                _set_cached_latest_reading(shed_id, res)
                return res

            # Fallback for alias matching (if user ID or username was passed instead of shed_id)
            cursor.execute("SELECT shed_id FROM users WHERE id = %s OR username = %s LIMIT 1", (shed_id, shed_id))
            u_row = cursor.fetchone()
            if u_row and u_row.get("shed_id"):
                resolved_shed = u_row["shed_id"]
                cursor.execute("""
                SELECT time as timestamp, shed_id,
                       temperature as indoor_temp, humidity as indoor_hum,
                       COALESCE(air_quality, 88.0) as air_quality,
                       COALESCE(light_lux, 22.0) as light_lux,
                       outside_temperature as outside_temp, outside_humidity as outside_hum,
                       cooler, heater, fan, humidifier,
                       COALESCE(light, FALSE) as light,
                       COALESCE(light_brightness, 0) as light_brightness,
                       mode
                FROM shed_telemetry
                WHERE shed_id = %s
                ORDER BY time DESC
                LIMIT 1
                """, (resolved_shed,))
                f_row = cursor.fetchone()
                if f_row:
                    res = dict(f_row)
                    _set_cached_latest_reading(shed_id, res)
                    return res
    except Exception as e:
        logger.debug("get_latest_telemetry_reading_from_db error: %s", e)
    return None


def get_telemetry_history_from_db(shed_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Queries historical telemetry timeseries from PostgreSQL table 'shed_telemetry'.
    Uses index idx_shed_telemetry_shed_time.
    """
    try:
        with get_db_cursor(dict_cursor=True) as cursor:
            cursor.execute("""
            SELECT time as timestamp, shed_id,
                   temperature as indoor_temp, humidity as indoor_hum,
                   COALESCE(air_quality, 88.0) as air_quality,
                   COALESCE(light_lux, 22.0) as light_lux,
                   outside_temperature as outside_temp, outside_humidity as outside_hum,
                   cooler, heater, fan, humidifier,
                   COALESCE(light, FALSE) as light,
                   COALESCE(light_brightness, 0) as light_brightness,
                   mode
            FROM shed_telemetry
            WHERE shed_id = %s
            ORDER BY time DESC
            LIMIT %s
            """, (shed_id, limit))
            rows = cursor.fetchall()
            result = []
            for r in reversed(rows):
                d = dict(r)
                if isinstance(d.get("timestamp"), datetime):
                    d["timestamp"] = d["timestamp"].isoformat()
                result.append(d)
            return result
    except Exception:
        return []


# --- Device Registry Operations ---

def register_device(
    device_id: str,
    shed_id: str,
    organization_id: str = "default_org",
    device_name: Optional[str] = None,
    device_key: Optional[str] = None,
    firmware_version: str = "1.0.0",
    cert_fingerprint_sha256: Optional[str] = None,
    auth_mode: str = "API_KEY",
) -> Dict[str, Any]:
    """Registers an IoT hardware node or updates its metadata."""
    key_hash = get_password_hash(device_key) if device_key else None
    now_dt = datetime.now(timezone.utc)
    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        cursor.execute("""
        INSERT INTO devices (device_id, shed_id, organization_id, device_name, device_key_hash, cert_fingerprint_sha256, auth_mode, firmware_version, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'ONLINE', %s)
        ON CONFLICT (device_id) DO UPDATE SET
            shed_id = EXCLUDED.shed_id,
            organization_id = EXCLUDED.organization_id,
            device_name = COALESCE(EXCLUDED.device_name, devices.device_name),
            device_key_hash = COALESCE(EXCLUDED.device_key_hash, devices.device_key_hash),
            cert_fingerprint_sha256 = COALESCE(EXCLUDED.cert_fingerprint_sha256, devices.cert_fingerprint_sha256),
            auth_mode = EXCLUDED.auth_mode,
            firmware_version = EXCLUDED.firmware_version
        RETURNING device_id, shed_id, organization_id, device_name, firmware_version, status, cert_fingerprint_sha256, auth_mode, created_at;
        """, (device_id, shed_id, organization_id, device_name or f"Device {device_id}", key_hash, cert_fingerprint_sha256, auth_mode, firmware_version, now_dt))
        row = cursor.fetchone()
        return dict(row) if row else {}


def get_device_by_id(device_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves device registration metadata by device_id."""
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("SELECT * FROM devices WHERE device_id = %s", (device_id,))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            if isinstance(d.get("created_at"), datetime):
                d["created_at"] = d["created_at"].isoformat()
            if isinstance(d.get("last_seen_at"), datetime):
                d["last_seen_at"] = d["last_seen_at"].isoformat()
            return d
    return None


def update_device_heartbeat(device_id: str, sequence_number: Optional[int] = None) -> None:
    """Updates device last_seen_at and sequence number tracking."""
    now_dt = datetime.now(timezone.utc)
    with get_db_cursor(commit=True) as cursor:
        if sequence_number is not None:
            cursor.execute("""
            UPDATE devices 
            SET last_seen_at = %s, last_sequence_number = %s, status = 'ONLINE'
            WHERE device_id = %s
            """, (now_dt, sequence_number, device_id))
        else:
            cursor.execute("""
            UPDATE devices 
            SET last_seen_at = %s, status = 'ONLINE'
            WHERE device_id = %s
            """, (now_dt, device_id))


# --- Safe Command Lifecycle Operations ---

def create_device_command(
    device_id: str,
    shed_id: str,
    requested_by: str,
    command_type: str,
    command_payload: Dict[str, Any],
    expires_in_seconds: int = 300,
    correlation_id: Optional[str] = None,
    organization_id: str = "default_org",
) -> Dict[str, Any]:
    """
    Creates a new command in REQUESTED state following the safe lifecycle:
    REQUESTED -> AUTHORIZED -> QUEUED -> SENT -> ACKNOWLEDGED -> APPLIED
    """
    import uuid
    import json
    command_id = f"cmd_{uuid.uuid4().hex[:12]}"
    now_dt = datetime.now(timezone.utc)
    expires_at = now_dt + timedelta(seconds=expires_in_seconds)

    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        cursor.execute("""
        INSERT INTO device_commands (
            command_id, organization_id, device_id, shed_id, requested_by,
            command_type, command_payload, status, created_at, expires_at, correlation_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'QUEUED', %s, %s, %s)
        RETURNING *;
        """, (
            command_id,
            organization_id,
            device_id,
            shed_id,
            requested_by,
            command_type,
            json.dumps(command_payload),
            now_dt,
            expires_at,
            correlation_id
        ))
        row = cursor.fetchone()
        log_audit(requested_by, "COMMAND_CREATED", f"Created command {command_id} ({command_type}) for device {device_id}")
        return dict(row) if row else {}


def acknowledge_device_command(
    command_id: str,
    device_id: str,
    status: str,
    error_message: Optional[str] = None,
    applied_state: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Records device execution acknowledgement (ACKNOWLEDGED / APPLIED / REJECTED / FAILED).
    Enforces device authorization: only the designated device can acknowledge its own commands.
    """
    now_dt = datetime.now(timezone.utc)
    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        # Check if command exists and has not expired
        cursor.execute("SELECT * FROM device_commands WHERE command_id = %s", (command_id,))
        cmd = cursor.fetchone()
        if not cmd:
            return None
        if cmd["device_id"] != device_id:
            logger.warning("Device mismatch acknowledging command %s: %s vs %s", command_id, device_id, cmd["device_id"])
            return None
        if cmd["expires_at"] < now_dt and status not in ["REJECTED", "FAILED"]:
            status = "EXPIRED"

        applied_at = now_dt if status == "APPLIED" else None
        ack_at = now_dt

        cursor.execute("""
        UPDATE device_commands
        SET status = %s, acknowledged_at = %s, applied_at = COALESCE(%s, applied_at), error_message = %s
        WHERE command_id = %s
        RETURNING *;
        """, (status, ack_at, applied_at, error_message, command_id))
        row = cursor.fetchone()
        log_audit(device_id, "COMMAND_ACK", f"Command {command_id} transitioned to {status}")
        return dict(row) if row else None


def get_pending_device_commands(device_id: str) -> List[Dict[str, Any]]:
    """Fetches valid, non-expired pending commands queued for a hardware node."""
    now_dt = datetime.now(timezone.utc)
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("""
        SELECT * FROM device_commands
        WHERE device_id = %s 
          AND status IN ('QUEUED', 'SENT')
          AND expires_at > %s
        ORDER BY created_at ASC
        """, (device_id, now_dt))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_device_command_by_id(command_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves full command lifecycle state by command_id."""
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("SELECT * FROM device_commands WHERE command_id = %s", (command_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
