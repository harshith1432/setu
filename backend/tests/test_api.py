import pytest
import httpx
from app.main import app

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.fixture
async def async_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

@pytest.mark.anyio
async def test_health_check(async_client):
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Mulbagal" in data["cluster"]

@pytest.mark.anyio
async def test_login_success_and_jwt(async_client):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "ramesh_farmer", "password": "setu2026"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == "ramesh_farmer"

@pytest.mark.anyio
async def test_login_invalid_credentials(async_client):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "ravi_farmer", "password": "wrong_password"}
    )
    assert response.status_code == 401

@pytest.mark.anyio
async def test_telemetry_ingestion(async_client):
    payload = {
        "shed_id": "shed_01",
        "temperature": 27.5,
        "humidity": 73.0,
        "outside_temperature": 34.5,
        "outside_humidity": 55.0
    }
    response = await async_client.post("/api/v1/telemetry/record", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["indoor_temp"] == 27.5
    assert data["shed_id"] == "shed_01"

@pytest.mark.anyio
async def test_authenticated_shed_status(async_client):
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "ramesh_farmer", "password": "setu2026"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await async_client.get("/api/v1/sheds/shed_01", headers=headers)
    assert response.status_code == 200
    shed = response.json()
    assert shed["farm_name"] == "Green Valley Farm"
    assert shed["current_stage"] == 3

@pytest.mark.anyio
async def test_ai_explanation_multilingual(async_client):
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "ramesh_farmer", "password": "setu2026"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res_en = await async_client.get("/api/v1/ai/explain/shed_01?lang=en", headers=headers)
    assert res_en.status_code == 200
    assert len(res_en.json()["bullet_points"]) > 0

    res_kn = await async_client.get("/api/v1/ai/explain/shed_01?lang=kn", headers=headers)
    assert res_kn.status_code == 200
    assert res_kn.json()["language"] == "kn"

@pytest.mark.anyio
async def test_csv_export(async_client):
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "ramesh_farmer", "password": "setu2026"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res_csv = await async_client.get("/api/v1/telemetry/export/csv/shed_01", headers=headers)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "Indoor_Temp_C" in res_csv.text

@pytest.mark.anyio
async def test_super_admin_stats_and_farmer_management(async_client):
    # Login as Super Admin (default admin / admin)
    admin_login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"}
    )
    assert admin_login.status_code == 200
    admin_data = admin_login.json()
    assert admin_data["user"]["role"] in ["admin", "superadmin"]
    admin_token = admin_data["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Fetch stats
    stats_res = await async_client.get("/api/v1/admin/stats", headers=admin_headers)
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert stats_data["total_farmers"] >= 3
    assert "Mulbagal" in stats_data["cluster_region"]

    # Fetch farmers list
    farmers_res = await async_client.get("/api/v1/admin/farmers", headers=admin_headers)
    assert farmers_res.status_code == 200
    farmers = farmers_res.json()
    assert any(f["username"] == "ramesh_farmer" for f in farmers)

    # Test Web Portal Static route
    portal_res = await async_client.get("/admin/")
    assert portal_res.status_code == 200
    assert "Setu | Super Admin" in portal_res.text

@pytest.mark.anyio
async def test_farmer_registration_persistence_and_subsequent_login(async_client):
    from app.services.db_service import get_user_by_username
    import time

    test_uname = f"farmer_test_{int(time.time())}"
    test_pwd = "securepassword123"

    # 1. Sign up new user
    reg_payload = {
        "username": test_uname,
        "password": test_pwd,
        "full_name": "Siddappa Gowda",
        "phone": "+91 98801 23456",
        "farm_name": "Kolar Silk Valley Farm",
        "region": "Mulbagal, Kolar, KA",
        "batch_id": "SERI-2026-N01",
        "dfl_capacity": "300 DFL",
        "breed": "Double Hybrid (FC1 x FC2)",
        "preferred_language": "kn"
    }
    reg_res = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["username"] == test_uname

    # 2. Verify stored in live PostgreSQL database
    db_user = get_user_by_username(test_uname)
    assert db_user is not None
    assert db_user["full_name"] == "Siddappa Gowda"
    assert db_user["farm_name"] == "Kolar Silk Valley Farm"

    # 3. Subsequent login using credentials
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"username": test_uname, "password": test_pwd}
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["user"]["username"] == test_uname

    # 4. Verify /auth/me returns latest database profile
    token = login_data["access_token"]
    me_res = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["farm_name"] == "Kolar Silk Valley Farm"

@pytest.mark.anyio
async def test_live_weather_endpoint(async_client):
    response = await async_client.get("/api/v1/weather/current?lat=13.1652&lon=78.3965")
    assert response.status_code == 200
    data = response.json()
    assert "outside_temperature" in data
    assert "outside_humidity" in data
    assert "condition" in data
    assert data["latitude"] == 13.1652
    assert data["longitude"] == 78.3965

