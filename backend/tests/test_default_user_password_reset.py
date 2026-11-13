import pytest
from app.core.config import settings
from app.services.db_service import create_user, get_user_by_username_or_phone

@pytest.mark.anyio
async def test_new_user_default_password_and_forced_reset_flow(async_client):
    default_pwd = settings.DEFAULT_NEW_USER_PASSWORD
    assert default_pwd == "Welcome@123"

    test_username = "test_farmer_welcome_flow"
    # Ensure fresh state
    new_user_payload = {
        "id": "usr_test_welcome_01",
        "username": test_username,
        "full_name": "Test Farmer Welcome",
        "phone": "+91 99999 12345",
        "role": "farmer",
        "farm_name": "Kolar Test Silk Farm",
        "preferred_language": "en"
    }
    
    # 1. Create user without explicit password -> should receive Welcome@123 and must_change_password=True
    created = create_user(new_user_payload)
    assert created["must_change_password"] is True
    
    # 2. Login with default password 'Welcome@123'
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"username": test_username, "password": default_pwd}
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    login_data = login_res.json()
    assert login_data["must_change_password"] is True
    assert login_data["user"]["must_change_password"] is True
    token = login_data["access_token"]

    # 3. Attempt to reset password with the SAME default password -> rejected with 400
    headers = {"Authorization": f"Bearer {token}"}
    fail_same = await async_client.post(
        "/api/v1/auth/first-login-reset-password",
        headers=headers,
        json={"new_password": default_pwd, "confirm_password": default_pwd}
    )
    assert fail_same.status_code == 400
    assert "default" in fail_same.json()["detail"].lower()

    # 4. Attempt with mismatched confirmation -> rejected with 400
    fail_mismatch = await async_client.post(
        "/api/v1/auth/first-login-reset-password",
        headers=headers,
        json={"new_password": "MySecretPass2026!", "confirm_password": "DifferentPass2026!"}
    )
    assert fail_mismatch.status_code == 400
    assert "match" in fail_mismatch.json()["detail"].lower()

    # 5. Successfully reset with new personal password
    new_password = "MyPersonalPass@2026"
    success_reset = await async_client.post(
        "/api/v1/auth/first-login-reset-password",
        headers=headers,
        json={"new_password": new_password, "confirm_password": new_password}
    )
    assert success_reset.status_code == 200
    reset_data = success_reset.json()
    assert reset_data["status"] == "success"
    assert reset_data["user"]["must_change_password"] is False

    # 6. Verify old default password NO LONGER works
    login_old = await async_client.post(
        "/api/v1/auth/login",
        json={"username": test_username, "password": default_pwd}
    )
    assert login_old.status_code == 401

    # 7. Verify new password logs in successfully with must_change_password=False
    login_new = await async_client.post(
        "/api/v1/auth/login",
        json={"username": test_username, "password": new_password}
    )
    assert login_new.status_code == 200
    new_data = login_new.json()
    assert new_data["must_change_password"] is False
    assert new_data["user"]["must_change_password"] is False
