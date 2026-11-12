"""
Database Initialization & Automated Schema Verification Service for SeriCare / Setu.

Ensures that whenever the software runs (locally or in deployment):
1. Verifies database connectivity (with resilient retry backoff for cloud cold-starts).
2. Inspects existing tables against required application schemas.
3. If tables exist -> proceeds directly with software startup.
4. If tables are missing -> automatically creates all tables, indexes, constraints, 
   and seeds baseline configurations before the application starts accepting requests.
"""

import os
import sys
import time
import logging
from typing import Dict, Any, List, Tuple, Set

logger = logging.getLogger("db_initializer")

REQUIRED_TABLES: List[str] = [
    # Core IoT & Farmer Shed Tables
    "users",
    "devices",
    "device_commands",
    "audit_logs",
    "stage_thresholds",
    "shed_settings",
    "shed_telemetry",
    "sheds",
    "revoked_tokens",
    "user_sessions",
    "password_resets",
    
    # Enterprise Platform Management Tables
    "products",
    "inventory_movements",
    "orders",
    "order_items",
    "subscriptions",
    "invoices",
    "payments",
    "support_tickets",
    "support_messages",
    "installation_jobs",
    "installation_events",
    "guidance_articles",
    "alerts",
    "sensors",
    "integration_status",
    "enquiries",
    "faqs",
    "platform_settings",
    
    # Organization, Employee & RBAC Tables
    "organizations",
    "departments",
    "roles",
    "permissions",
    "role_permissions",
    "employees",
    "employee_invitations"
]


def get_existing_postgres_tables(cursor) -> Set[str]:
    """Queries information_schema for all existing public tables."""
    try:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        rows = cursor.fetchall()
        return {r[0] if isinstance(r, (list, tuple)) else r["table_name"] for r in rows}
    except Exception as e:
        logger.warning("Could not query information_schema.tables: %s", e)
        return set()


def check_and_create_postgres_tables(max_retries: int = 5, retry_interval: float = 2.0) -> Dict[str, Any]:
    """
    Connects to PostgreSQL, checks if tables exist, and creates them if missing.
    Includes retry logic to handle cloud database container cold starts during deployment.
    """
    from app.core.config import settings
    from app.services.db_service import get_pool, init_db, _postgres_available
    from app.services.enterprise_db import init_enterprise_tables
    from app.services.org_employee_db import init_org_employee_tables

    dsn = settings.DATABASE_URL
    if not dsn or os.getenv("USE_FIREBASE_ONLY", "false").lower() in ("true", "1"):
        logger.info("[DB-CHECK] PostgreSQL disabled or USE_FIREBASE_ONLY=true. Operating in Cloud Firestore mode.")
        return {
            "status": "skipped",
            "reason": "USE_FIREBASE_ONLY or no DATABASE_URL configured",
            "tables_found": 0,
            "created": False
        }

    pool = None
    last_err = None

    # Resilient connection retry for cloud deployment cold-starts
    for attempt in range(1, max_retries + 1):
        try:
            pool = get_pool()
            if pool:
                break
        except Exception as e:
            last_err = e
            logger.warning("[DB-CHECK] Database connection attempt %d/%d failed: %s", attempt, max_retries, e)
        time.sleep(retry_interval)

    if not pool:
        logger.warning("[DB-CHECK] Could not connect to PostgreSQL after %d attempts (%s). Software will run in Firebase fallback mode.", max_retries, last_err)
        return {
            "status": "fallback",
            "reason": str(last_err),
            "tables_found": 0,
            "created": False
        }

    # Inspect database tables
    conn = pool.getconn()
    try:
        cursor = conn.cursor()
        existing_tables = get_existing_postgres_tables(cursor)
        missing_tables = [t for t in REQUIRED_TABLES if t not in existing_tables]

        if not missing_tables:
            logger.info("============================================================")
            logger.info("[DB-CHECK] SUCCESS: All required database tables exist (%d tables present).", len(existing_tables))
            logger.info("[DB-CHECK] Database schema verified. Proceeding to run software.")
            logger.info("============================================================")
            cursor.close()
            pool.putconn(conn)
            return {
                "status": "verified",
                "tables_found": len(existing_tables),
                "missing": [],
                "created": False
            }

        # Tables are missing: automatically create tables first
        logger.info("============================================================")
        logger.info("[DB-CHECK] Found %d existing tables. Missing %d required tables: %s", 
                    len(existing_tables), len(missing_tables), missing_tables)
        logger.info("[DB-CHECK] Creating missing tables and initializing database schema first...")
        logger.info("============================================================")
        cursor.close()
        pool.putconn(conn)

        # Run creation modules
        init_db()
        init_enterprise_tables()
        init_org_employee_tables()

        # Re-verify table creation
        conn2 = pool.getconn()
        try:
            cursor2 = conn2.cursor()
            updated_tables = get_existing_postgres_tables(cursor2)
            still_missing = [t for t in REQUIRED_TABLES if t not in updated_tables]
            cursor2.close()
            pool.putconn(conn2)

            if still_missing:
                logger.error("[DB-CHECK] WARNING: Some tables could not be created: %s", still_missing)
            else:
                logger.info("============================================================")
                logger.info("[DB-CHECK] SUCCESS: All tables created and verified (%d tables total).", len(updated_tables))
                logger.info("[DB-CHECK] Database is fully ready. Proceeding to run software.")
                logger.info("============================================================")

            return {
                "status": "created",
                "tables_found": len(updated_tables),
                "missing_after_init": still_missing,
                "created": True
            }
        except Exception as e:
            pool.putconn(conn2)
            raise e

    except Exception as e:
        try:
            pool.putconn(conn)
        except Exception:
            pass
        logger.error("[DB-CHECK] Error during database table verification: %s", e)
        return {
            "status": "error",
            "error": str(e),
            "created": False
        }


def verify_and_ensure_database_ready() -> Dict[str, Any]:
    """
    Master database entrypoint called on software startup and deployment.
    Checks and creates database tables, verifies Super Admin credentials,
    and validates cloud Firestore readiness.
    """
    logger.info("[DATABASE INITIALIZATION] Starting automated database and schema readiness check...")
    
    # 1. PostgreSQL Schema Verification & Creation
    pg_result = check_and_create_postgres_tables()

    # 2. Firestore Cloud Database Verification
    from app.services.firestore_service import firestore_service
    fs_ready = firestore_service.is_available
    if fs_ready:
        logger.info("[DATABASE INITIALIZATION] Cloud Firestore is active and ready.")
    else:
        logger.info("[DATABASE INITIALIZATION] Cloud Firestore running in offline/graceful mode.")

    # 3. Super Admin from .env verification
    from app.services.enterprise_db import verify_and_seed_superadmin
    try:
        admin_meta = verify_and_seed_superadmin()
        logger.info("[DATABASE INITIALIZATION] Super Admin verified from .env: username='%s', active=%s",
                    admin_meta.get("username"), admin_meta.get("is_active"))
    except Exception as se:
        logger.warning("[DATABASE INITIALIZATION] Super Admin verification notice: %s", se)
        admin_meta = {}

    logger.info("[DATABASE INITIALIZATION] Software readiness check complete. System ready to serve traffic.")
    return {
        "postgres": pg_result,
        "firestore_connected": fs_ready,
        "superadmin": admin_meta
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    # Add backend directory to sys.path if invoked directly
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    result = verify_and_ensure_database_ready()
    print("\n[DB INITIALIZER SUMMARY]")
    print(result)
