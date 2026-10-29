"""
Test suite for Unified Authentication & Farmer Registration in Setu
Tests:
- Unified login endpoint POST /api/v1/auth/login for multiple roles (Admin & Farmer)
- Public farmer registration POST /api/v1/auth/register
- Immediate login of newly registered farmer through unified login
- Privilege escalation defense (role injection rejected / forced to farmer)
- Input validation (passwords >= 8 chars, password confirmation, duplicate checks)
- Static HTML endpoints GET /login and GET /register
- Multi-tab session isolation integration
"""
import uuid
import pytest
import httpx
from app.main import app
from app.services.db_service import init_db
from app.core.config import settings

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
async def test_login_page_served(async_client):
    """Verify /login serves 200 OK HTML"""
    response = await async_client.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Sign In to Setu" in response.text
    assert "Register as a Farmer" in response.text
    # Ensure Super Admin console branding is removed from login
    assert "Super Admin Console" not in response.text

@pytest.mark.anyio
async def test_farmer_registration_page_served(async_client):
    """Verify /register serves 200 OK HTML"""
    response = await async_client.get("/register")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Farmer Registration" in response.text
    assert "Sign In" in response.text

@pytest.mark.anyio
async def test_unified_login_admin_success(async_client):
    """Verify admin user can log in via unified login endpoint"""
    response = await async_client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": settings.INITIAL_ADMIN_PASSWORD
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "session_id" in data
    assert data["user"]["role"] in ["admin", "superadmin"]

@pytest.mark.anyio
async def test_unified_login_farmer_success(async_client):
    """Verify existing farmer can log in via the SAME unified login endpoint"""
    response = await async_client.post("/api/v1/auth/login", json={
        "username": "ramesh_farmer",
        "password": "setu2026"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "session_id" in data
    assert data["user"]["role"] == "farmer"

@pytest.mark.anyio
async def test_unified_login_invalid_credentials(async_client):
    """Verify generic error on invalid credentials without user enumeration"""
    response = await async_client.post("/api/v1/auth/login", json={
        "username": "nonexistent_user_9999",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    err_msg = data["detail"].lower()
    assert "incorrect" in err_msg or "invalid" in err_msg

@pytest.mark.anyio
async def test_farmer_registration_success(async_client):
    """Verify farmer registration flow works end-to-end and can immediately log in"""
    rand_suffix = uuid.uuid4().hex[:6]
    test_username = f"farmer_{rand_suffix}"
    test_phone = f"+9198{uuid.uuid4().int % 100000000:08d}"
    test_email = f"farmer_{rand_suffix}@example.com"
    test_password = "FarmerPassword@123"
    
    payload = {
        "full_name": "Ramesh Gowda",
        "username": test_username,
        "phone": test_phone,
        "email": test_email,
        "password": test_password,
        "confirm_password": test_password,
        "farm_name": "Gowda Sericulture Farm",
        "region": "Karnataka",
        "dfl_capacity": "300 DFL",
        "breed": "Bivoltine (FC1 x FC2)",
        "terms_accepted": True
    }
    
    response = await async_client.post(
        "/api/v1/auth/register",
        json=payload,
        headers={"X-Tab-ID": "tab_test_farmer_01"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "session_id" in data
    assert data["user"]["role"] == "farmer"
    assert data["user"]["username"] == test_username
    assert data["user"]["shed_id"] is not None

    # Verify newly registered farmer can log in via unified /api/v1/auth/login
    login_res = await async_client.post("/api/v1/auth/login", json={
        "username": test_username,
        "password": test_password
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["user"]["role"] == "farmer"
    assert login_data["user"]["username"] == test_username

@pytest.mark.anyio
async def test_farmer_registration_privilege_escalation_defense(async_client):
    """Verify malicious client attempting to register as admin or superadmin is strictly forced to farmer"""
    rand_suffix = uuid.uuid4().hex[:6]
    test_username = f"hacker_{rand_suffix}"
    test_phone = f"+9197{uuid.uuid4().int % 100000000:08d}"
    
    payload = {
        "full_name": "Attacker Trying Admin",
        "username": test_username,
        "phone": test_phone,
        "password": "SuperSecretPassword123",
        "confirm_password": "SuperSecretPassword123",
        "role": "superadmin",
        "terms_accepted": True
    }
    
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    # The assigned role MUST BE farmer, strictly ignoring the client-supplied role
    assert data["user"]["role"] == "farmer"
    assert data["user"]["role"] != "superadmin"
    assert data["user"]["role"] != "admin"

@pytest.mark.anyio
async def test_farmer_registration_password_mismatch(async_client):
    """Verify registration fails when passwords don't match"""
    rand_suffix = uuid.uuid4().hex[:6]
    payload = {
        "full_name": "Mismatch User",
        "username": f"mismatch_{rand_suffix}",
        "phone": f"+9196{uuid.uuid4().int % 100000000:08d}",
        "password": "Password12345",
        "confirm_password": "PasswordDifferent99",
        "terms_accepted": True
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "match" in response.json()["detail"].lower()

@pytest.mark.anyio
async def test_farmer_registration_password_too_short(async_client):
    """Verify registration fails when password is under 8 characters"""
    rand_suffix = uuid.uuid4().hex[:6]
    payload = {
        "full_name": "Short Pass User",
        "username": f"short_{rand_suffix}",
        "phone": f"+9195{uuid.uuid4().int % 100000000:08d}",
        "password": "pass",
        "confirm_password": "pass",
        "terms_accepted": True
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "8 characters" in response.json()["detail"]

@pytest.mark.anyio
async def test_farmer_registration_duplicate_username(async_client):
    """Verify duplicate username returns HTTP 400"""
    rand_suffix = uuid.uuid4().hex[:6]
    test_username = f"dupuser_{rand_suffix}"
    test_phone_1 = f"+9194{uuid.uuid4().int % 100000000:08d}"
    test_phone_2 = f"+9193{uuid.uuid4().int % 100000000:08d}"
    
    payload1 = {
        "full_name": "First User",
        "username": test_username,
        "phone": test_phone_1,
        "password": "Password12345",
        "confirm_password": "Password12345",
        "terms_accepted": True
    }
    res1 = await async_client.post("/api/v1/auth/register", json=payload1)
    assert res1.status_code == 200
    
    payload2 = {
        "full_name": "Second User",
        "username": test_username,
        "phone": test_phone_2,
        "password": "Password12345",
        "confirm_password": "Password12345",
        "terms_accepted": True
    }
    res2 = await async_client.post("/api/v1/auth/register", json=payload2)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"].lower()


@pytest.mark.anyio
async def test_forgot_and_reset_password_flow(async_client):
    """
    Verifies end-to-end 2-step password recovery:
    1. Requests recovery code for valid registered identifier
    2. Enforces 404 on nonexistent identifiers
    3. Rejects invalid OTP reset codes
    4. Resets password successfully with valid OTP code
    5. Confirms old credentials revoked and new credentials work
    """
    import uuid
    suffix = uuid.uuid4().hex[:6]
    test_user = f"resetuser_{suffix}"
    test_phone = f"+9198{uuid.uuid4().int % 100000000:08d}"
    initial_pass = "InitialPass123"
    new_pass = "UpdatedPass999!"

    # 1. Register test farmer account
    reg_res = await async_client.post("/api/v1/auth/register", json={
        "full_name": "Password Reset Tester",
        "username": test_user,
        "phone": test_phone,
        "password": initial_pass,
        "confirm_password": initial_pass,
        "terms_accepted": True
    })
    assert reg_res.status_code == 200

    # 2. Unknown identifier returns 404
    bad_req = await async_client.post("/api/v1/auth/forgot-password", json={
        "identifier": "non_existent_account_99999"
    })
    assert bad_req.status_code == 404

    # 3. Valid identifier returns 200 and recovery OTP
    fp_res = await async_client.post("/api/v1/auth/forgot-password", json={
        "identifier": test_user
    })
    assert fp_res.status_code == 200
    fp_data = fp_res.json()
    assert fp_data["success"] is True
    assert "reset_code" in fp_data
    reset_code = fp_data["reset_code"]

    # 4. Invalid reset code returns 400
    bad_reset = await async_client.post("/api/v1/auth/reset-password", json={
        "reset_code": "000000",
        "new_password": new_pass,
        "confirm_password": new_pass
    })
    assert bad_reset.status_code == 400

    # 5. Valid code updates password
    good_reset = await async_client.post("/api/v1/auth/reset-password", json={
        "reset_code": reset_code,
        "new_password": new_pass,
        "confirm_password": new_pass
    })
    assert good_reset.status_code == 200
    assert good_reset.json()["success"] is True

    # 6. Old password no longer works
    old_login = await async_client.post("/api/v1/auth/login", json={
        "username": test_user,
        "password": initial_pass
    })
    assert old_login.status_code == 401

    # 7. New password authenticates and issues token
    new_login = await async_client.post("/api/v1/auth/login", json={
        "username": test_user,
        "password": new_pass
    })
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()

