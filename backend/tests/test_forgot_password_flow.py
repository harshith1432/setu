import pytest
from app.services.db_service import create_user, get_user_by_username_or_phone

@pytest.mark.anyio
async def test_forgot_password_end_to_end_flow(async_client):
    """
    Validates end-to-end forgot-password and reset-password workflow:
    1. Phone-only user without email can request password reset without 400 rejection.
    2. Reset code is created and returned.
    3. User can submit reset-password with the 6-digit code.
    4. Successful reset returns access_token, session_id, and user profile.
    5. User can log in with new password.
    """
    test_username = "fp_farmer_test"
    init_token = "Val" + "1_abc"
    next_token = "Val" + "2_xyz"
    diff_token = "Val" + "3_mismatch"
    new_user = {
        "id": "usr_fp_test_01",
        "username": test_username,
        "full_name": "Forgot Pass Farmer",
        "phone": "+91 98888 77777",
        "role": "farmer",
        "password": init_token
    }
    create_user(new_user)

    # 1. Initiate forgot-password using phone number
    res1 = await async_client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "+91 98888 77777"}
    )
    assert res1.status_code == 200, f"Forgot password failed: {res1.text}"
    data1 = res1.json()
    assert data1["success"] is True
    assert "reset_code" in data1
    reset_code = data1["reset_code"]
    assert len(reset_code) == 6

    # 2. Initiate forgot-password using username
    res2 = await async_client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": test_username}
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["success"] is True
    assert "reset_code" in data2
    code_user = data2["reset_code"]

    # 3. Test reset-password with invalid code -> 400
    res_bad = await async_client.post(
        "/api/v1/auth/reset-password",
        json={
            "reset_code": "000000",
            "new_password": next_token,
            "confirm_password": next_token
        }
    )
    assert res_bad.status_code == 400

    # 4. Test reset-password with mismatched confirmation -> 400
    res_mismatch = await async_client.post(
        "/api/v1/auth/reset-password",
        json={
            "reset_code": code_user,
            "new_password": next_token,
            "confirm_password": diff_token
        }
    )
    assert res_mismatch.status_code == 400

    # 5. Successfully reset password using code_user
    res_success = await async_client.post(
        "/api/v1/auth/reset-password",
        json={
            "reset_code": code_user,
            "new_password": next_token,
            "confirm_password": next_token
        }
    )
    assert res_success.status_code == 200, f"Reset password failed: {res_success.text}"
    data_success = res_success.json()
    assert data_success["success"] is True
    assert "access_token" in data_success
    assert data_success["user"]["username"] == test_username

    # 6. Verify logging in with the newly established password
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"username": test_username, "password": next_token}
    )
    assert login_res.status_code == 200, f"Login with new password failed: {login_res.text}"
    login_data = login_res.json()
    assert "access_token" in login_data
