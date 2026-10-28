import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
async def test_technician_can_access_stages_and_sheds():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login as technician
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"username": "tech_kiran", "password": "tech2026"}
        )
        assert login_res.status_code == 200, f"Technician login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Stage thresholds (fixes "Failed to load stage climate setpoints")
        stages_res = await client.get("/api/v1/admin/stages", headers=headers)
        assert stages_res.status_code == 200, f"Failed to get stages: {stages_res.text}"
        stages = stages_res.json()
        assert len(stages) >= 5
        assert stages[0]["stage_id"] == 1
        assert "temp_min" in stages[0]

        # 3. Stage detail
        stage_1 = await client.get("/api/v1/admin/stages/1", headers=headers)
        assert stage_1.status_code == 200
        assert stage_1.json()["stage_id"] == 1

        # 4. Sheds list
        sheds_res = await client.get("/api/v1/admin/sheds", headers=headers)
        assert sheds_res.status_code == 200, f"Failed to get sheds: {sheds_res.text}"
        sheds = sheds_res.json()
        assert len(sheds) >= 1

        # 5. Shed overview
        overview_res = await client.get("/api/v1/sheds/shed_01/overview", headers=headers)
        assert overview_res.status_code == 200, f"Failed to get shed overview: {overview_res.text}"
        overview = overview_res.json()
        assert "indoor_temp" in overview

        # 6. Admin stats (used by devices view)
        stats_res = await client.get("/api/v1/admin/stats", headers=headers)
        assert stats_res.status_code == 200, f"Failed to get admin stats: {stats_res.text}"

        # 7. Hardware Sensors
        sensors_res = await client.get("/api/v1/sensors?shed_id=shed_01", headers=headers)
        assert sensors_res.status_code == 200

        # 8. Installations
        installs_res = await client.get("/api/v1/installations", headers=headers)
        assert installs_res.status_code == 200

        # 9. Installation Team
        team_res = await client.get("/api/v1/installations/team", headers=headers)
        assert team_res.status_code == 200

        # 10. Verify superadmin-only actions are still protected against technician
        reset_res = await client.post("/api/v1/admin/stages/reset", headers=headers)
        assert reset_res.status_code == 403


@pytest.mark.anyio
async def test_operations_manager_can_access_farmers_sheds_and_telemetry():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login as operations manager
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"username": "ops_manoj", "password": "ops2026"}
        )
        assert login_res.status_code == 200, f"Operations Manager login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Farmers directory (fixes "Error: Failed to load farmers")
        farmers_res = await client.get("/api/v1/admin/farmers", headers=headers)
        assert farmers_res.status_code == 200, f"Failed to load farmers: {farmers_res.text}"
        farmers = farmers_res.json()
        assert len(farmers) >= 1

        # 3. Sheds list & overview
        sheds_res = await client.get("/api/v1/admin/sheds", headers=headers)
        assert sheds_res.status_code == 200
        overview_res = await client.get("/api/v1/sheds/shed_01/overview", headers=headers)
        assert overview_res.status_code == 200

        # 4. Stage setpoints
        stages_res = await client.get("/api/v1/admin/stages", headers=headers)
        assert stages_res.status_code == 200

        # 5. Sensors & Incidents
        sensors_res = await client.get("/api/v1/sensors?shed_id=shed_01", headers=headers)
        assert sensors_res.status_code == 200
        alerts_res = await client.get("/api/v1/alerts", headers=headers)
        assert alerts_res.status_code == 200


@pytest.mark.anyio
async def test_all_personas_can_read_stages_and_sheds():
    personas = [
        ("admin", "admin"),
        ("ceo", "ceo2026"),
        ("ops_manoj", "ops2026"),
        ("support_priya", "support2026"),
        ("sales_anand", "sales2026"),
        ("ramesh_farmer", "setu2026")
    ]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for u, p in personas:
            login = await client.post("/api/v1/auth/login", json={"username": u, "password": p})
            assert login.status_code == 200, f"Login failed for {u}: {login.text}"
            token = login.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            stages = await client.get("/api/v1/admin/stages", headers=headers)
            assert stages.status_code == 200, f"Stages failed for {u}: {stages.text}"

            sheds = await client.get("/api/v1/admin/sheds", headers=headers)
            assert sheds.status_code == 200, f"Sheds failed for {u}: {sheds.text}"
