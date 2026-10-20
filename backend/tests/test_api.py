import pytest
import httpx
from app.main import app
from app.core.config import settings

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
    assert "Dynamic" in data.get("mode", "") or "Global" in data.get("network", "")

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
async def test_telemetry_ingestion_and_auth_gate(async_client):
    payload = {
        "shed_id": "shed_01",
        "temperature": 27.5,
        "humidity": 73.0,
        "outside_temperature": 34.5,
        "outside_humidity": 55.0
    }
    # 1. Unauthenticated request without X-Device-Key must be rejected (SEC-05)
    unauth_res = await async_client.post("/api/v1/telemetry/record", json=payload)
    assert unauth_res.status_code == 401

    # 2. Authenticated request with pre-shared X-Device-Key succeeds
    auth_res = await async_client.post(
        "/api/v1/telemetry/record",
        json=payload,
        headers={"X-Device-Key": settings.DEVICE_API_KEY}
    )
    assert auth_res.status_code == 200
    data = auth_res.json()
    assert data["indoor_temp"] == 27.5
    assert data["shed_id"] == "shed_01"

@pytest.mark.anyio
async def test_bola_actuator_control_protection(async_client):
    # Login as ramesh_farmer (assigned to shed_01)
    ramesh_login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "ramesh_farmer", "password": "setu2026"}
    )
    assert ramesh_login.status_code == 200
    ramesh_token = ramesh_login.json()["access_token"]
    ramesh_headers = {"Authorization": f"Bearer {ramesh_token}"}

    # 1. Ramesh controls his own shed (shed_01) -> Allowed (200)
    own_res = await async_client.post(
        "/api/v1/control/shed_01/override",
        json={"actuator": "cooler", "state": True},
        headers=ramesh_headers
    )
    assert own_res.status_code == 200

    # 2. Ramesh attempts to control shed_02 (owned by another farmer) -> Forbidden (403 BOLA check SEC-06)
    alien_res = await async_client.post(
        "/api/v1/control/shed_02/override",
        json={"actuator": "cooler", "state": True},
        headers=ramesh_headers
    )
    assert alien_res.status_code == 403

    # 3. Super Admin controls any shed -> Allowed (200)
    admin_login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"}
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_res = await async_client.post(
        "/api/v1/control/shed_02/override",
        json={"actuator": "cooler", "state": True},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_res.status_code == 200

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
    assert "Green Valley" in shed["farm_name"]
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
    assert "Global" in stats_data["cluster_region"]

    # Fetch farmers list
    farmers_res = await async_client.get("/api/v1/admin/farmers", headers=admin_headers)
    assert farmers_res.status_code == 200
    farmers = farmers_res.json()
    assert any(f["username"] == "ramesh_farmer" for f in farmers)

    # Fetch farmer detail
    detail_res = await async_client.get("/api/v1/admin/farmers/ramesh_farmer", headers=admin_headers)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["status"] == "success"
    assert detail_data["farmer"]["username"] == "ramesh_farmer"
    assert "shed" in detail_data
    assert "history" in detail_data

    # Update farmer details
    update_res = await async_client.put(
        "/api/v1/admin/farmers/ramesh_farmer",
        headers=admin_headers,
        json={
            "full_name": "Ramesh Gowda Updated",
            "phone": "+91 98450 99999",
            "farm_name": "Green Valley Sericulture Farm Updated",
            "batch_id": "SERI-2026-M04-REV"
        }
    )
    assert update_res.status_code == 200
    assert update_res.json()["farmer"]["full_name"] == "Ramesh Gowda Updated"

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
        "region": "Karnataka, India",
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

@pytest.mark.anyio
async def test_admin_stage_thresholds_and_software_level_controls(async_client):
    admin_login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"}
    )
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Fetch all growth stage levels
    stages_res = await async_client.get("/api/v1/admin/stages", headers=admin_headers)
    assert stages_res.status_code == 200
    stages = stages_res.json()
    assert len(stages) == 5
    assert stages[0]["stage_id"] == 1
    assert "1st Instar" in stages[0]["name"]

    # 2. Update Stage 1 thresholds (e.g. adjust Chawki temp & hum)
    update_payload = {
        "temp_min": 27.2,
        "temp_max": 28.5,
        "hum_min": 82.0,
        "hum_max": 88.0,
        "hysteresis_temp": 0.4,
        "hysteresis_hum": 2.5,
        "fan_trigger_offset": 1.2,
        "description": "Updated optimal Chawki thresholds for summer batch."
    }
    put_res = await async_client.put("/api/v1/admin/stages/1", json=update_payload, headers=admin_headers)
    assert put_res.status_code == 200
    stage1 = put_res.json()["stage"]
    assert stage1["temp_min"] == 27.2
    assert stage1["hum_max"] == 88.0

    # 3. Verify in rules_engine that updated threshold is active
    from app.services.rules_engine import STAGE_THRESHOLDS
    assert STAGE_THRESHOLDS[1]["temp_min"] == 27.2
    assert STAGE_THRESHOLDS[1]["hum_max"] == 88.0

    # 4. Switch shed stage and verify overview
    stage_res = await async_client.post(
        "/api/v1/admin/sheds/shed_01/stage",
        json={"stage": 1},
        headers=admin_headers
    )
    assert stage_res.status_code == 200
    overview = stage_res.json()
    assert overview["current_stage"] == 1

    # 5. Fetch telemetry-live
    live_res = await async_client.get("/api/v1/admin/telemetry-live?shed_id=shed_01", headers=admin_headers)
    assert live_res.status_code == 200
    live_data = live_res.json()
    assert "compliance_index" in live_data
    assert "history" in live_data
    assert live_data["overview"]["shed_id"] == "shed_01"

    # 6. Reset stages back to CSB standard defaults
    reset_res = await async_client.post("/api/v1/admin/stages/reset", headers=admin_headers)
    assert reset_res.status_code == 200
    assert STAGE_THRESHOLDS[1]["temp_min"] == 27.0

@pytest.mark.anyio
async def test_admin_sheds_list_endpoint(async_client):
    admin_login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"}
    )
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    res = await async_client.get("/api/v1/admin/sheds", headers=admin_headers)
    assert res.status_code == 200
    sheds = res.json()
    assert isinstance(sheds, list)
    assert len(sheds) >= 1
    # Check that shed_01 is present with display name
    shed_ids = [s["shed_id"] for s in sheds]
    assert "shed_01" in shed_ids
    assert "display_name" in sheds[0]

@pytest.mark.anyio
async def test_telemetry_csv_export(async_client):
    admin_login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"}
    )
    admin_token = admin_login.json()["access_token"]

    # 1. Test CSV export with Bearer Header
    res_header = await async_client.get(
        "/api/v1/telemetry/export/csv/shed_01",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_header.status_code == 200
    assert "text/csv" in res_header.headers["content-type"]
    assert "Timestamp_UTC" in res_header.text
    assert "Indoor_Temp_C" in res_header.text

    # 2. Test CSV export with query parameter token
    res_query = await async_client.get(
        f"/api/v1/telemetry/export/csv/shed_01?token={admin_token}"
    )
    assert res_query.status_code == 200
    assert "text/csv" in res_query.headers["content-type"]
    assert "Timestamp_UTC" in res_query.text

