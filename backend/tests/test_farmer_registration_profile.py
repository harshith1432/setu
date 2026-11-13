import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.db_service import get_user_by_username, get_user_by_id

@pytest.mark.anyio
async def test_farmer_registration_and_profile_update():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_phone = f"98765{uuid.uuid4().hex[:5]}"
        reg_payload = {
            "full_name": "Acchu Test Farmer",
            "phone": unique_phone,
            "username": unique_phone,
            "email": f"acchu_{unique_phone}@example.com",
            "password": "Password@123",
            "confirm_password": "Password@123",
            "farm_name": "Acchu Silk Farm",
            "region": "Kolar Cluster",
            "dfl_capacity": "250 DFL",
            "breed": "Double Hybrid (FC1 x FC2)",
            "terms_accepted": True
        }

        # 1. Register Farmer
        reg_resp = await client.post("/api/v1/auth/register", json=reg_payload)
        assert reg_resp.status_code == 200, f"Registration failed: {reg_resp.text}"
        data = reg_resp.json()
        assert "access_token" in data
        assert data["user"]["username"] == unique_phone
        token = data["access_token"]
        user_id = data["user"]["id"]

        # 2. Verify user is retrievable via db_service
        user_in_db = get_user_by_username(unique_phone) or get_user_by_id(user_id)
        assert user_in_db is not None, "User should be found in database or fallback store"

        # 3. Fetch user via /api/v1/auth/me
        headers = {"Authorization": f"Bearer {token}"}
        me_resp = await client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["username"] == unique_phone
        assert me_data["full_name"] == "Acchu Test Farmer"

        # 4. Update profile via /api/v1/auth/profile (reproducing user's Edit Profile action)
        update_payload = {
            "full_name": "Acchu Gowda Updated",
            "phone": unique_phone,
            "email": "acchu_updated@example.com",
            "farm_name": "Acchu Premium Silk Rearing",
            "region": "Chintamani Kolar Belt",
            "preferred_language": "kn"
        }
        update_resp = await client.put("/api/v1/auth/profile", json=update_payload, headers=headers)
        assert update_resp.status_code == 200, f"Profile update failed with status {update_resp.status_code}: {update_resp.text}"
        updated_data = update_resp.json()
        assert updated_data["full_name"] == "Acchu Gowda Updated"
        assert updated_data["farm_name"] == "Acchu Premium Silk Rearing"
