import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.voice_service import voice_service
from app.services.whatsapp_alerts import alert_service


@pytest.mark.anyio
async def test_voice_script_multilingual():
    en_script = voice_service.build_voice_script(
        farmer_name="Harshith",
        shed_id="shed_01",
        current_temp=26.2,
        temp_target=25.0,
        is_cooler_on=True,
        is_heater_on=False,
        is_fan_on=True,
        lang="en",
    )
    assert "Harshith" in en_script
    assert "shed_01" in en_script
    assert "26.2" in en_script
    assert "Cooling and exhaust fans are running" in en_script

    kn_script = voice_service.build_voice_script(
        farmer_name="ರಮೇಶ್",
        shed_id="shed_01",
        current_temp=27.0,
        temp_target=25.0,
        is_cooler_on=True,
        lang="kn",
    )
    assert "ರಮೇಶ್" in kn_script
    assert "ಕೂಲರ್ ಮತ್ತು ಫ್ಯಾನ್" in kn_script

    te_script = voice_service.build_voice_script(
        farmer_name="రమేష్",
        shed_id="shed_01",
        current_temp=28.0,
        temp_target=25.0,
        is_cooler_on=True,
        lang="te",
    )
    assert "రమేష్" in te_script
    assert "కూలర్ మరియు ఫ్యాన్" in te_script


@pytest.mark.anyio
async def test_temperature_variation_alert_has_actuators_and_one_line_explanation():
    msg = alert_service.build_temperature_variation_alert(
        farmer_name="Harshith Kd",
        farm_name="vfgt",
        shed_id="shed_01",
        current_temp=26.2,
        temp_target=25.0,
        temp_min=24.0,
        temp_max=26.0,
        current_hum=80.0,
        status="TOO_WARM",
        headline="Too Warm — Cooling Active",
        subline="Cooling running to prevent heat stress.",
        cooler_active=True,
        heater_active=False,
        fan_active=True,
        lang="en",
    )
    # Check that actuator status is shown
    assert "⚙️ System Controls Active:" in msg
    assert "Cooler: ON ❄️" in msg
    assert "Exhaust Fan: ON 💨" in msg
    assert "Heater: OFF" in msg
    
    # Check that the 1-line explanation is present
    assert "💡 What SeriCare Is Doing:" in msg
    assert "Cooling and ventilation fans are actively running to safely lower temperature from 26.2°C to optimal 25.0°C." in msg


@pytest.mark.anyio
async def test_voice_endpoint_stateless_audio_streaming():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        text = "SeriCare alert test audio."
        url = voice_service.get_voice_url_for_text(text=text, lang="en")
        assert "/api/v1/voice/" in url
        assert url.endswith(".mp3")
        
        # Extract path
        path = "/api/v1/voice/" + url.split("/api/v1/voice/")[1]
        
        response = await client.get(path)
        assert response.status_code == 200
        assert response.headers.get("content-type") == "audio/mpeg"
        assert len(response.content) > 0


@pytest.mark.anyio
async def test_voice_preview_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {"text": "Test preview note", "lang": "en"}
        res = await client.post("/api/v1/voice/preview", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "voice_url" in data
        assert data["file_ready"] is True
