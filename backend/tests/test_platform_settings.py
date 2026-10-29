import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.security import create_access_token


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def admin_token():
    return create_access_token(data={"sub": "admin", "role": "superadmin", "shed_id": "shed_01"})


@pytest.fixture
def farmer_token():
    return create_access_token(data={"sub": "farmer_01", "role": "farmer", "shed_id": "shed_01"})


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_get_platform_settings_and_categories(async_client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = await async_client.get("/api/v1/platform/settings", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "general" in data
    assert "security" in data
    # branding and cms are completely removed
    assert "branding" not in data
    assert "cms" not in data

    # Verify General default parameters match Image 2
    general = data["general"]
    assert "self_service_signup" in general
    assert "email_otp_verification" in general
    assert "phone_otp_verification" in general
    assert "maintenance_mode" in general


@pytest.mark.anyio
async def test_update_platform_settings_general(async_client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    update_payload = {
        "settings": {
            "self_service_signup": False,
            "email_otp_verification": True,
            "phone_otp_verification": True,
            "maintenance_mode": False
        }
    }
    res = await async_client.put("/api/v1/platform/settings/general", json=update_payload, headers=headers)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "success"
    assert res_data["settings"]["self_service_signup"] is False
    assert res_data["settings"]["phone_otp_verification"] is True

    # Revert to defaults
    revert_payload = {
        "settings": {
            "self_service_signup": True,
            "email_otp_verification": True,
            "phone_otp_verification": False,
            "maintenance_mode": False
        }
    }
    await async_client.put("/api/v1/platform/settings/general", json=revert_payload, headers=headers)


@pytest.mark.anyio
async def test_branding_and_cms_endpoints_rejected(async_client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    res_branding = await async_client.put(
        "/api/v1/platform/settings/branding",
        json={"settings": {"app_name": "Test"}},
        headers=headers
    )
    assert res_branding.status_code == 400

    res_cms = await async_client.put(
        "/api/v1/platform/settings/cms",
        json={"settings": {"hero_headline": "Test"}},
        headers=headers
    )
    assert res_cms.status_code == 400


@pytest.mark.anyio
async def test_get_and_add_superadmins(async_client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # 1. Fetch superadmins
    res = await async_client.get("/api/v1/platform/superadmins", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["total"] >= 2
    usernames = [a["username"] for a in data["admins"]]
    assert "admin" in usernames

    # 2. Add a new superadmin
    new_admin_payload = {
        "username": "test_ops_admin",
        "full_name": "Test Operations Lead",
        "email": "testops@setu.ag",
        "password": "SecurePassword2026!",
        "sub_role": "Platform Operations",
        "phone": "+91 98450 77777"
    }
    add_res = await async_client.post("/api/v1/platform/superadmins", json=new_admin_payload, headers=headers)
    assert add_res.status_code in [200, 400]
    if add_res.status_code == 200:
        created = add_res.json()["admin"]
        assert created["username"] == "test_ops_admin"
        assert created["sub_role"] == "Platform Operations"

    # 3. Test short password rejection
    invalid_payload = {
        "username": "invalid_admin",
        "full_name": "Invalid Admin",
        "email": "invalid@setu.ag",
        "password": "123",
        "sub_role": "Support"
    }
    bad_res = await async_client.post("/api/v1/platform/superadmins", json=invalid_payload, headers=headers)
    assert bad_res.status_code == 400


@pytest.mark.anyio
async def test_rbac_farmer_cannot_access_platform_settings(async_client, farmer_token):
    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}
    # Attempt to read settings
    res1 = await async_client.get("/api/v1/platform/settings", headers=farmer_headers)
    assert res1.status_code == 403

    # Attempt to list superadmins
    res2 = await async_client.get("/api/v1/platform/superadmins", headers=farmer_headers)
    assert res2.status_code == 403

    # Attempt to update credentials
    res3 = await async_client.put(
        "/api/v1/platform/superadmins/credentials",
        json={"current_password": "x", "new_email": "x@x.com"},
        headers=farmer_headers
    )
    assert res3.status_code == 403
