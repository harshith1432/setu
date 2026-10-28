import pytest
import httpx
from app.main import app
from app.services.db_service import init_db
from app.services.enterprise_db import init_enterprise_tables
from app.services.org_employee_db import init_org_employee_tables

# Immediate initialization when conftest is imported
try:
    init_db()
    init_enterprise_tables()
    init_org_employee_tables()
except Exception as e:
    import logging
    logging.getLogger(__name__).warning("Conftest immediate DB initialization: %s", e)

@pytest.fixture(scope="session", autouse=True)
def initialize_test_database():
    """Ensure all core, enterprise, and RBAC tables are created and seeded before any test runs."""
    init_db()
    init_enterprise_tables()
    init_org_employee_tables()

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.fixture
async def async_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
