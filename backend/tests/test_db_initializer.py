import pytest
from app.services.db_initializer import (
    REQUIRED_TABLES,
    get_existing_postgres_tables,
    check_and_create_postgres_tables,
    verify_and_ensure_database_ready
)


def test_required_tables_list_defined():
    assert len(REQUIRED_TABLES) >= 30
    assert "users" in REQUIRED_TABLES
    assert "sheds" in REQUIRED_TABLES
    assert "products" in REQUIRED_TABLES
    assert "orders" in REQUIRED_TABLES
    assert "platform_settings" in REQUIRED_TABLES
    assert "employees" in REQUIRED_TABLES
    assert "roles" in REQUIRED_TABLES


def test_verify_and_ensure_database_ready():
    result = verify_and_ensure_database_ready()
    assert "postgres" in result
    assert "firestore_connected" in result
    assert "superadmin" in result
    assert result["superadmin"].get("username") is not None


def test_existing_tables_verification():
    from app.services.db_service import get_pool
    p = get_pool()
    if not p:
        pytest.skip("PostgreSQL pool offline in test environment")

    conn = p.getconn()
    try:
        cur = conn.cursor()
        tables = get_existing_postgres_tables(cur)
        assert len(tables) > 0
        assert "users" in tables
        assert "sheds" in tables
        cur.close()
    finally:
        p.putconn(conn)
