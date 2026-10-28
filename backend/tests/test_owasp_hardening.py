import pytest
import httpx
from app.main import app
from app.core.security import create_access_token
from app.services.db_service import init_db
from app.core.config import Settings, settings

@pytest.fixture(scope="module", autouse=True)
def ensure_db():
    init_db()

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.fixture
async def async_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

@pytest.mark.anyio
async def test_security_headers_and_permissions_policy(async_client):
    """
    OWASP A05:2025 & ASVS V14: Verify complete modern HTTP security headers.
    """
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    headers = resp.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert headers.get("Strict-Transport-Security") is not None
    assert "Content-Security-Policy" in headers
    assert "Permissions-Policy" in headers
    assert "geolocation=(self)" in headers["Permissions-Policy"]
    assert "camera=()" in headers["Permissions-Policy"]

@pytest.mark.anyio
async def test_request_payload_size_limit_413(async_client):
    """
    OWASP A04/A05 & ASVS V13: Verify oversized payloads (>2MB) are rejected with 413.
    """
    headers = {"Content-Length": "3145728", "Content-Type": "application/json"}
    resp = await async_client.post("/api/v1/auth/login", content=b"{}", headers=headers)
    assert resp.status_code == 413
    assert "Payload Too Large" in resp.text

@pytest.mark.anyio
async def test_ai_explainer_idor_prevention(async_client):
    """
    OWASP A01:2025 Broken Access Control & ASVS V4:
    Verify that an unauthorized farmer cannot request AI insights for another farmer's shed.
    """
    # Authenticate as ramesh_farmer (assigned to shed_01)
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "ramesh_farmer", "password": "setu2026"}
    )
    assert login_resp.status_code == 200
    ramesh_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {ramesh_token}"}
    
    # Ramesh attempts to query explainable AI for shed_02
    resp = await async_client.get("/api/v1/ai/explain/shed_02", headers=headers)
    assert resp.status_code == 403
    assert "Forbidden" in resp.text or "permission" in resp.text

@pytest.mark.anyio
async def test_voice_preview_input_length_and_language_validation(async_client):
    """
    OWASP A04:2025 Input Validation & ASVS V5:
    Verify text bounds (<=500 chars) and language code whitelisting.
    """
    admin_token = create_access_token(data={"sub": "admin", "role": "superadmin"})
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Text exceeding 500 characters
    oversized_text = "A" * 501
    resp = await async_client.post("/api/v1/voice/preview", json={"text": oversized_text, "lang": "en"}, headers=headers)
    assert resp.status_code == 422

    # 2. Invalid language code with injection attempt
    resp = await async_client.post("/api/v1/voice/preview", json={"text": "Normal text", "lang": "en; rm -rf /"}, headers=headers)
    assert resp.status_code == 422

    # 3. Valid payload succeeds
    resp = await async_client.post("/api/v1/voice/preview", json={"text": "Shed temperature is normal.", "lang": "en"}, headers=headers)
    assert resp.status_code == 200
    assert "voice_url" in resp.json()

@pytest.mark.anyio
async def test_token_revocation_on_logout(async_client):
    """
    OWASP A07:2025 Identification and Authentication Failures & ASVS V3.4:
    Verify explicit logout revokes JWT, and subsequent use of revoked token returns 401.
    """
    # 1. Create active token
    token = create_access_token(data={"sub": "admin", "role": "superadmin"})
    auth_header = {"Authorization": f"Bearer {token}"}

    # Verify token works initially
    resp1 = await async_client.get("/api/v1/dashboard/overview", headers=auth_header)
    assert resp1.status_code == 200

    # 2. Perform logout to revoke token
    resp_logout = await async_client.post("/api/v1/auth/logout", headers=auth_header)
    assert resp_logout.status_code == 200
    assert "revoked" in resp_logout.json()["message"].lower()

    # 3. Subsequent request with revoked token must be rejected with 401
    resp2 = await async_client.get("/api/v1/dashboard/overview", headers=auth_header)
    assert resp2.status_code == 401
    assert "revoked or invalidated" in resp2.json()["detail"].lower()

@pytest.mark.anyio
async def test_bola_device_command_status(async_client):
    """
    OWASP A01:2025 Broken Object Level Authorization:
    Verify an attacker cannot read command status of a shed they do not own.
    """
    from app.services.db_service import create_device_command
    import uuid

    cmd = create_device_command(
        device_id="esp32_gateway_02",
        shed_id="shed_02",
        requested_by="farmer_charlie",
        command_type="cooling_fan",
        command_payload={"state": "ON"},
        correlation_id=f"corr_{uuid.uuid4().hex[:6]}"
    )
    cmd_id = cmd["command_id"]

    # Ramesh (owns shed_01) attempts to inspect Charlie's command on shed_02
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "ramesh_farmer", "password": "setu2026"}
    )
    assert login_resp.status_code == 200
    ramesh_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {ramesh_token}"}

    resp = await async_client.get(f"/api/v1/control/commands/status/{cmd_id}", headers=headers)
    assert resp.status_code == 403
    assert "Access denied" in resp.text or "Forbidden" in resp.text

def test_production_environment_config_hardening():
    """
    OWASP A05:2025 Security Misconfiguration:
    Verify that in production environment, default/weak SECRET_KEY raises a fatal error.
    """
    with pytest.raises(ValueError, match="CRITICAL SECURITY CONFIGURATION ERROR"):
        cfg = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="setu-secret-key-production-safety-2026"
        )
        cfg.validate_production_security()

    with pytest.raises(ValueError, match="CRITICAL SECURITY CONFIGURATION ERROR"):
        cfg = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="short-secret-key-12345"
        )
        cfg.validate_production_security()

    strong_cfg = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a" * 48
    )
    strong_cfg.validate_production_security()

@pytest.mark.anyio
async def test_farmer_bola_order_isolation(async_client):
    """
    BOLA Authorization Isolation (ASVS V4 & OWASP API1:2023):
    Verify that Farmer A cannot access orders belonging to Farmer B.
    """
    from app.services.db_service import get_db_cursor
    import uuid

    u1_id = f"usr_fa_{uuid.uuid4().hex[:6]}"
    u2_id = f"usr_fb_{uuid.uuid4().hex[:6]}"
    order_id = f"ord_test_{uuid.uuid4().hex[:8]}"

    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO users (id, username, hashed_password, full_name, phone, role, created_at)
            VALUES (%s, %s, 'hash', 'Farmer A', %s, 'farmer', NOW())
            ON CONFLICT (id) DO NOTHING
        """, (u1_id, f"farmer_a_{u1_id}", f"99{uuid.uuid4().int % 100000000:08d}"))
        cur.execute("""
            INSERT INTO users (id, username, hashed_password, full_name, phone, role, created_at)
            VALUES (%s, %s, 'hash', 'Farmer B', %s, 'farmer', NOW())
            ON CONFLICT (id) DO NOTHING
        """, (u2_id, f"farmer_b_{u2_id}", f"88{uuid.uuid4().int % 100000000:08d}"))
        cur.execute("""
            INSERT INTO orders (id, order_number, user_id, status, total_amount_minor_units, created_at, updated_at)
            VALUES (%s, %s, %s, 'PAID', 500000, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """, (order_id, f"ORD-{order_id}", u2_id))

    farmer_a_token = create_access_token(data={"sub": f"farmer_a_{u1_id}", "user_id": u1_id, "role": "farmer"})
    farmer_a_headers = {"Authorization": f"Bearer {farmer_a_token}"}

    resp = await async_client.get(f"/api/v1/orders/{order_id}", headers=farmer_a_headers)
    assert resp.status_code == 403
    assert "Forbidden" in resp.text
