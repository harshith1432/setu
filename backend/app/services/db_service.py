import os
import logging
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from contextlib import contextmanager
from app.core.config import settings
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)

DATABASE_URL = settings.DATABASE_URL

_connection_pool: Optional[pool.ThreadedConnectionPool] = None

def get_pool() -> Optional[pool.ThreadedConnectionPool]:
    """
    Returns a singleton ThreadedConnectionPool for PostgreSQL connection reuse.
    """
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                dsn=DATABASE_URL
            )
        except Exception as e:
            _connection_pool = None
    return _connection_pool

@contextmanager
def get_db_cursor(commit: bool = False, dict_cursor: bool = False):
    """
    Context manager that yields a cursor from the connection pool or a direct connection.
    Guarantees connection cleanup and release back to the pool.
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
    """
    Legacy helper: Returns a direct PostgreSQL connection.
    """
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """
    Initializes PostgreSQL tables: 'users', 'audit_logs', 'stage_thresholds', 'shed_telemetry',
    and seeds initial accounts safely without overwriting user passwords on restart (SEC-02).
    """
    with get_db_cursor(commit=True) as cursor:
        # Farmers & Users Table
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

        # Audit Logs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL,
            actor VARCHAR(64) NOT NULL,
            action VARCHAR(64) NOT NULL,
            details TEXT NOT NULL
        );
        """)

        # Stage Thresholds (Admin software levels for auto-mode)
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

        # Shed Telemetry Timeseries Table (Persisting historical sensor readings)
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

        # Pre-seed Stage Thresholds if empty
        cursor.execute("SELECT COUNT(*) FROM stage_thresholds")
        if cursor.fetchone()[0] == 0:
            now_dt = datetime.now(timezone.utc)
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

        now_dt = datetime.now(timezone.utc)

        # Pre-seed Admin safely (SEC-02: only create if missing, NEVER overwrite on reboot)
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

        # Pre-seed Demo Farmers individually if not present
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
    Purely data-driven from the database records with zero hardcoded usernames.
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

                # If shed_id is empty or already claimed by another farmer, assign unique shed_{u_id}
                if not current_shed or current_shed in seen_sheds:
                    new_shed = f"shed_{u_id}"
                    cursor.execute("UPDATE users SET shed_id = %s WHERE id = %s", (new_shed, u_id))
                    seen_sheds.add(new_shed)
                else:
                    seen_sheds.add(current_shed)
    except Exception as e:
        logger.debug(f"ensure_unique_farmer_sheds: {e}")

# Initialize DB on module import safely
try:
    init_db()
    ensure_unique_farmer_sheds()
except Exception as e:
    # Gracefully handle DB unavailability during builds / imports
    pass

# Database CRUD helpers
def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            if isinstance(d.get("created_at"), datetime):
                d["created_at"] = d["created_at"].isoformat()
            return d
    return None

def get_user_by_username_or_phone(identifier: str) -> Optional[Dict[str, Any]]:
    clean_id = identifier.strip()
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute(
            "SELECT * FROM users WHERE username = %s OR phone = %s OR whatsapp_number = %s",
            (clean_id, clean_id, clean_id),
        )
        row = cursor.fetchone()
        if row:
            d = dict(row)
            if isinstance(d.get("created_at"), datetime):
                d["created_at"] = d["created_at"].isoformat()
            return d
    return None

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            if isinstance(d.get("created_at"), datetime):
                d["created_at"] = d["created_at"].isoformat()
            return d
    return None

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
    clean_shed_id = shed_id.strip()
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("""
            SELECT * FROM users 
            WHERE LOWER(shed_id) = LOWER(%s) AND role != 'superadmin' AND is_active = TRUE 
            ORDER BY created_at ASC
        """, (clean_shed_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("created_at"), datetime):
                d["created_at"] = d["created_at"].isoformat()
            result.append(d)
        return result

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

    # Assign distinct shed_id for new farmers if not specified or defaulting
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
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS current_stage INT DEFAULT 3")
        cursor.execute(query, tuple(values))
        row = cursor.fetchone()
        if row:
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

# Telemetry Persistence Operations
def save_telemetry_reading(reading: Dict[str, Any]) -> None:
    """
    Persists a telemetry reading into PostgreSQL table 'shed_telemetry'.
    """
    try:
        with get_db_cursor(commit=True) as cursor:
            t = reading.get("timestamp") or datetime.now(timezone.utc)
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
                float(reading.get("indoor_temp", 25.0)),
                float(reading.get("indoor_hum", 75.0)),
                float(reading.get("air_quality", 88.0)),
                float(reading.get("light_lux", 22.0)),
                float(reading.get("outside_temp")) if reading.get("outside_temp") is not None else None,
                float(reading.get("outside_hum")) if reading.get("outside_hum") is not None else None,
                bool(reading.get("cooler", False)),
                bool(reading.get("heater", False)),
                bool(reading.get("fan", False)),
                bool(reading.get("humidifier", False)),
                bool(reading.get("light", False)),
                int(reading.get("light_brightness", 0)),
                reading.get("mode", "AUTO")
            ))
    except Exception:
        pass

def get_latest_telemetry_reading_from_db(shed_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the single most recent real-time telemetry reading for a shed from PostgreSQL table 'shed_telemetry'.
    Queries purely from real recorded IoT data.
    """
    try:
        with get_db_cursor(dict_cursor=True) as cursor:
            cursor.execute("""
            SELECT st.time as timestamp, st.shed_id,
                   st.temperature as indoor_temp, st.humidity as indoor_hum,
                   COALESCE(st.air_quality, 88.0) as air_quality,
                   COALESCE(st.light_lux, 22.0) as light_lux,
                   st.outside_temperature as outside_temp, st.outside_humidity as outside_hum,
                   st.cooler, st.heater, st.fan, st.humidifier,
                   COALESCE(st.light, FALSE) as light,
                   COALESCE(st.light_brightness, 0) as light_brightness,
                   st.mode
            FROM shed_telemetry st
            LEFT JOIN users u ON u.shed_id = st.shed_id
            WHERE st.shed_id = %s 
               OR u.id = %s 
               OR u.username = %s 
               OR ('shed_' || u.id) = %s
            ORDER BY st.time DESC
            LIMIT 1
            """, (shed_id, shed_id, shed_id, shed_id))
            row = cursor.fetchone()
            if row:
                return dict(row)
    except Exception:
        pass
    return None

def get_telemetry_history_from_db(shed_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Queries historical telemetry timeseries from PostgreSQL table 'shed_telemetry'.
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

