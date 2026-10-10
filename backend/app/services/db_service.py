import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.core.config import settings
from app.core.security import get_password_hash

DATABASE_URL = settings.DATABASE_URL

def get_connection():
    """
    Returns a PostgreSQL connection with dict-like row access.
    """
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    """
    Initializes PostgreSQL tables: 'users' and 'audit_logs', and seeds initial accounts.
    """
    conn = get_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    
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
        batch_id VARCHAR(64) NOT NULL DEFAULT 'SERI-2026-M04',
        dfl_capacity VARCHAR(64) NOT NULL DEFAULT '200 DFL',
        breed VARCHAR(128) NOT NULL DEFAULT 'Double Hybrid (FC1 x FC2)',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL
    );
    """)
    
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
    
    # Pre-seed Admin and sample farmers if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    if count == 0:
        now_dt = datetime.now(timezone.utc)
        
        # Super Admin
        cursor.execute("""
        INSERT INTO users (id, username, hashed_password, full_name, phone, preferred_language, role, farm_name, region, batch_id, dfl_capacity, breed, is_active, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            "usr_admin",
            "superadmin",
            get_password_hash("adminsecure2026"),
            "Setu Super Admin",
            "+91 98450 99999",
            "en",
            "superadmin",
            "Central Sericulture Command",
            "Central Sericulture Command HQ",
            "CENTRAL-HQ",
            "N/A",
            "N/A",
            True,
            now_dt
        ))
        
        # Farmer 1: Ramesh Gowda
        cursor.execute("""
        INSERT INTO users (id, username, hashed_password, full_name, phone, preferred_language, role, farm_name, region, batch_id, dfl_capacity, breed, is_active, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            "usr_001",
            "ramesh_farmer",
            get_password_hash("setu2026"),
            "Ramesh Gowda",
            "+91 98450 12345",
            "kn",
            "farmer",
            "Green Valley Sericulture Farm",
            "Mysuru Silk Belt, KA",
            "SERI-2026-M04",
            "200 DFL",
            "Double Hybrid (FC1 x FC2)",
            True,
            now_dt
        ))

        # Farmer 2: Venkatamma
        cursor.execute("""
        INSERT INTO users (id, username, hashed_password, full_name, phone, preferred_language, role, farm_name, region, batch_id, dfl_capacity, breed, is_active, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            "usr_002",
            "venkatamma_farmer",
            get_password_hash("setu2026"),
            "Venkatamma Reddy",
            "+91 94480 54321",
            "te",
            "farmer",
            "Sri Lakshmi Silk Farm",
            "Kolar Silk Belt, KA",
            "SERI-2026-M05",
            "150 DFL",
            "Cross Breed (PM x CSR2)",
            True,
            now_dt
        ))

        # Farmer 3: Manjunath
        cursor.execute("""
        INSERT INTO users (id, username, hashed_password, full_name, phone, preferred_language, role, farm_name, region, batch_id, dfl_capacity, breed, is_active, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            "usr_003",
            "manjunath_kolar",
            get_password_hash("setu2026"),
            "Manjunath K.",
            "+91 99001 88776",
            "kn",
            "farmer",
            "Kolar Silk Fields",
            "Ramanagara Silk Hub, KA",
            "SERI-2026-M02",
            "300 DFL",
            "Bivoltine White (FC1 x FC2)",
            True,
            now_dt
        ))

    # Always ensure default Super Admin 'admin' with password 'admin' exists
    now_dt = datetime.now(timezone.utc)
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("""
        INSERT INTO users (id, username, hashed_password, full_name, phone, preferred_language, role, farm_name, region, batch_id, dfl_capacity, breed, is_active, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            "usr_admin_default",
            "admin",
            get_password_hash("admin"),
            "Setu Super Admin",
            "+91 98450 99999",
            "en",
            "superadmin",
            "Central Sericulture Command",
            "Central Sericulture Command HQ",
            "CENTRAL-HQ",
            "N/A",
            "N/A",
            True,
            now_dt
        ))
    else:
        cursor.execute("""
        UPDATE users SET hashed_password = %s, role = 'superadmin', is_active = TRUE WHERE username = 'admin'
        """, (get_password_hash("admin"),))

    # Also update 'superadmin' to accept 'admin' as well as fallback
    cursor.execute("""
    UPDATE users SET hashed_password = %s, role = 'superadmin', is_active = TRUE WHERE username = 'superadmin'
    """, (get_password_hash("admin"),))

    cursor.close()
    conn.close()

# Initialize DB on module import
init_db()

# Database CRUD helpers
def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        d = dict(row)
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
        return d
    return None

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        d = dict(row)
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
        return d
    return None

def get_all_farmers() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT id, username, full_name, phone, preferred_language, role, 
               farm_name, region, batch_id, dfl_capacity, breed, is_active, created_at 
        FROM users 
        WHERE role != 'superadmin' 
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    result = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
        result.append(d)
    return result

def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    conn.autocommit = True
    cursor = conn.cursor()
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

    cursor.execute("""
    INSERT INTO users (id, username, hashed_password, full_name, phone, preferred_language, role, farm_name, region, latitude, longitude, batch_id, dfl_capacity, breed, is_active, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        user_data["id"],
        user_data["username"],
        user_data["hashed_password"],
        user_data["full_name"],
        user_data["phone"],
        user_data.get("preferred_language", "kn"),
        user_data.get("role", "farmer"),
        user_data.get("farm_name", "Green Valley Farm"),
        user_data.get("region", "Local Rearing Shed"),
        user_data.get("latitude"),
        user_data.get("longitude"),
        user_data.get("batch_id", "SERI-2026-M04"),
        user_data.get("dfl_capacity", "200 DFL"),
        user_data.get("breed", "Double Hybrid (FC1 x FC2)"),
        True,
        created_at_dt
    ))
    cursor.close()
    conn.close()
    return user_data

def update_user_profile(user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    conn.autocommit = True
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    fields = []
    values = []
    allowed = ["full_name", "phone", "preferred_language", "farm_name", "region", "latitude", "longitude", "batch_id", "dfl_capacity", "breed"]
    for k in allowed:
        if k in updates and updates[k] is not None:
            fields.append(f"{k} = %s")
            values.append(updates[k])
            
    if not fields:
        cursor.close()
        conn.close()
        return get_user_by_id(user_id) or get_user_by_username(user_id)
        
    values.append(user_id)
    values.append(user_id)
    query = f"UPDATE users SET {', '.join(fields)} WHERE id = %s OR username = %s RETURNING *"
    cursor.execute(query, tuple(values))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        d = dict(row)
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
        return d
    return None

def update_user_status(user_id: str, is_active: bool) -> bool:
    conn = get_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    # Support both username or id match
    cursor.execute("UPDATE users SET is_active = %s WHERE id = %s OR username = %s", (is_active, user_id, user_id))
    cursor.close()
    conn.close()
    return True

def delete_user(user_id: str) -> bool:
    conn = get_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s OR username = %s", (user_id, user_id))
    cursor.close()
    conn.close()
    return True

def log_audit(actor: str, action: str, details: str):
    conn = get_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO audit_logs (timestamp, actor, action, details)
    VALUES (%s, %s, %s, %s)
    """, (datetime.now(timezone.utc), actor, action, details))
    cursor.close()
    conn.close()

def get_audit_logs(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT %s", (limit,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    result = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get("timestamp"), datetime):
            d["timestamp"] = d["timestamp"].isoformat()
        result.append(d)
    return result

def get_all_stage_thresholds() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM stage_thresholds ORDER BY stage_id ASC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    result = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get("updated_at"), datetime):
            d["updated_at"] = d["updated_at"].isoformat()
        result.append(d)
    return result

def get_stage_threshold(stage_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM stage_thresholds WHERE stage_id = %s", (stage_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        d = dict(row)
        if isinstance(d.get("updated_at"), datetime):
            d["updated_at"] = d["updated_at"].isoformat()
        return d
    return None

def update_stage_threshold(stage_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    conn.autocommit = True
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    fields = []
    values = []
    allowed = ["name", "days", "temp_min", "temp_max", "hum_min", "hum_max", "hysteresis_temp", "hysteresis_hum", "fan_trigger_offset", "description"]
    for k in allowed:
        if k in updates and updates[k] is not None:
            fields.append(f"{k} = %s")
            values.append(updates[k])
            
    if not fields:
        cursor.close()
        conn.close()
        return get_stage_threshold(stage_id)

    fields.append("updated_at = %s")
    values.append(datetime.now(timezone.utc))

    values.append(stage_id)
    query = f"UPDATE stage_thresholds SET {', '.join(fields)} WHERE stage_id = %s RETURNING *"
    cursor.execute(query, tuple(values))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        d = dict(row)
        if isinstance(d.get("updated_at"), datetime):
            d["updated_at"] = d["updated_at"].isoformat()
        return d
    return None

def reset_stage_thresholds() -> List[Dict[str, Any]]:
    conn = get_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    
    defaults = [
        (1, "1st Instar (Chawki)", "Days 1–3", 27.0, 28.0, 80.0, 85.0, 0.5, 3.0, 1.5, "Chawki stage: Delicate larvae requiring high humidity and warm ambient temperatures to prevent desiccation."),
        (2, "2nd Instar", "Days 4–5", 26.5, 27.5, 75.0, 80.0, 0.5, 3.0, 1.5, "Post-first moult larvae. Transitioning to active feeding with moderate humidity requirements."),
        (3, "3rd Instar", "Days 6–9", 25.0, 26.5, 70.0, 75.0, 0.5, 3.0, 1.5, "Late chawki / adult transition. Increased voracity requires steady ventilation and balanced thermal envelope."),
        (4, "4th Instar", "Days 10–14", 24.0, 25.5, 65.0, 70.0, 0.5, 3.0, 1.5, "Exponential larval weight gain. High metabolic heat output necessitates active cooling and air exchange."),
        (5, "5th Instar", "Days 15–20", 23.0, 24.5, 60.0, 65.0, 0.5, 3.0, 1.5, "Final feeding instar preceding cocooning/spinning. Requires cooler, drier conditions and continuous fresh airflow.")
    ]
    
    now_dt = datetime.now(timezone.utc)
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
        
    cursor.close()
    conn.close()
    return get_all_stage_thresholds()

