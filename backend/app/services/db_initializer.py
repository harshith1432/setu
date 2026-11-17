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
    PostgreSQL is retired. Returns pure Firebase Cloud Firestore status immediately with zero network delays.
    """
    logger.info("[DB-CHECK] Pure Firebase Cloud Firestore mode active (PostgreSQL retired).")
    return {
        "status": "disabled_migrated_to_pure_firebase",
        "reason": "PostgreSQL completely retired in favor of Firebase Cloud Firestore (setu-a767c)",
        "tables_found": 0,
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
