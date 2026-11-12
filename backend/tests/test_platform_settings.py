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


@pytest.mark.anyio
async def test_env_superadmin_verification_and_toggle_flow(async_client, admin_token):
    from app.core.config import settings
    from app.services.enterprise_db import set_default_admin_enabled
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Reset state to enabled initially
    set_default_admin_enabled(True, "test_setup")

    # 1. Fetch superadmins and verify default_admin_enabled is True
    res = await async_client.get("/api/v1/platform/superadmins", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["default_admin_enabled"] is True

    # 2. Verify default admin can authenticate via /auth/login with .env password
    default_pw = settings.SUPERADMIN_PASSWORD
    login_default = await async_client.post(
        "/api/v1/auth/login",
        json={"username": settings.SUPERADMIN_USERNAME, "password": default_pw}
    )
    assert login_default.status_code == 200
    assert "access_token" in login_default.json()

    # 3. Create a secondary active super admin
    new_admin_user = f"custom_sa_{settings.SUPERADMIN_USERNAME}"
    new_admin_pw = "CustomSecurePassword123!"
    add_res = await async_client.post(
        "/api/v1/platform/superadmins",
        json={
            "username": new_admin_user,
            "full_name": "Custom Platform Admin",
            "email": f"{new_admin_user}@setu.ag",
            "password": new_admin_pw,
            "sub_role": "Platform Operations"
        },
        headers=headers
    )
    assert add_res.status_code in [200, 400]

    # Verify custom admin can authenticate
    login_custom = await async_client.post(
        "/api/v1/auth/login",
        json={"username": new_admin_user, "password": new_admin_pw}
    )
    assert login_custom.status_code == 200

    # 4. Disable the default .env super admin
    toggle_off = await async_client.post(
        "/api/v1/platform/superadmins/toggle-default",
        json={"enabled": False},
        headers=headers
    )
    assert toggle_off.status_code == 200
    assert toggle_off.json()["default_admin_enabled"] is False

    # 5. Verify default admin from .env is now BLOCKED (403 Forbidden)
    blocked_login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": settings.SUPERADMIN_USERNAME, "password": default_pw}
    )
    assert blocked_login.status_code == 403
    assert "disabled" in blocked_login.json()["detail"].lower()

    # 6. Verify custom super admin can STILL authenticate while default admin is disabled
    login_custom_while_disabled = await async_client.post(
        "/api/v1/auth/login",
        json={"username": new_admin_user, "password": new_admin_pw}
    )
    assert login_custom_while_disabled.status_code == 200

    # 7. Re-enable the default super admin
    toggle_on = await async_client.post(
        "/api/v1/platform/superadmins/toggle-default",
        json={"enabled": True},
        headers=headers
    )
    assert toggle_on.status_code == 200
    assert toggle_on.json()["default_admin_enabled"] is True

    # 8. Verify default admin can log in again
    re_login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": settings.SUPERADMIN_USERNAME, "password": default_pw}
    )
    assert re_login.status_code == 200
