import pytest
import httpx
from app.main import app
from app.services.whatsapp_alerts import WhatsAppAlertService, alert_service
from app.services.db_service import get_user_by_username, set_user_whatsapp_verified, get_farmer_by_shed_id


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
async def async_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


def test_whatsapp_normalization_edge_cases():
    normalize = WhatsAppAlertService.normalize_whatsapp
    # 10-digit Indian numbers
    assert normalize("9876543210") == "whatsapp:+919876543210"
    # Leading 0 (11 digits)
    assert normalize("09876543210") == "whatsapp:+919876543210"
    # Leading 91 (12 digits)
    assert normalize("919876543210") == "whatsapp:+919876543210"
    # Formatted with spaces, parens, hyphens
    assert normalize("+91 (987) 654-3210") == "whatsapp:+919876543210"
    # Already whatsapp prefix
    assert normalize("whatsapp:+919876543210") == "whatsapp:+919876543210"
    # Empty or None
    assert normalize("") == ""
    assert normalize(None) == ""


def test_multilingual_alert_templates():
    service = WhatsAppAlertService()
    # Kannada manual alert
    kn_alert = service.build_manual_alert(
        actuator="cooler",
        outside_temp=35.0,
        outside_humidity=45.0,
        region="Mysuru Shed",
        current_temp=28.5,
        current_humidity=80.0,
        lang="kn",
    )
    assert "ಕೂಲರ್" in kn_alert
    assert "35.0°C" in kn_alert

    # Telugu manual alert
    te_alert = service.build_manual_alert(
        actuator="heater",
        outside_temp=18.0,
        outside_humidity=85.0,
        region="Chittoor Shed",
        current_temp=19.0,
        current_humidity=88.0,
        lang="te",
    )
    assert "హీటర్" in te_alert

    # Critical telemetry alerts
    kn_crit = service.build_critical_telemetry_alert(
        shed_id="shed_01",
        temperature=33.5,
        humidity=40.0,
        status="CRITICAL",
        reason="High temperature threshold exceeded",
        lang="kn",
    )
    assert "ತೀವ್ರ ಎಚ್ಚರಿಕೆ" in kn_crit
    assert "33.5°C" in kn_crit

    te_crit = service.build_critical_telemetry_alert(
        shed_id="shed_02",
        temperature=34.0,
        humidity=42.0,
        status="CRITICAL",
        lang="te",
    )
    assert "అత్యవసర హెచ్చరిక" in te_crit

    en_crit = service.build_critical_telemetry_alert(
        shed_id="shed_01",
        temperature=33.5,
        humidity=40.0,
        status="CRITICAL",
        lang="en",
    )
    assert "CRITICAL ALERT" in en_crit


def test_alert_cooldown_throttling():
    service = WhatsAppAlertService()
    key = "test_cooldown_unit_key"

    # First send should pass
    res1 = service.send(
        message="Alert 1",
        recipient="+919876543210",
        dry_run=True,
        cooldown_key=key,
        cooldown_seconds=60,
    )
    assert res1["status"] == "dry-run"

    # Immediate second send with same key should be throttled
    res2 = service.send(
        message="Alert 2",
        recipient="+919876543210",
        dry_run=True,
        cooldown_key=key,
        cooldown_seconds=60,
    )
    assert res2["status"] == "throttled"
    assert "suppressed by cooldown" in res2["message"]


def test_get_farmer_by_shed_id_db():
    farmer = get_farmer_by_shed_id("shed_01")
    assert farmer is not None
    assert farmer.get("shed_id") == "shed_01"
    assert "whatsapp_number" in farmer


@pytest.mark.anyio
async def test_whatsapp_alert_service_dry_run(async_client):
    service = WhatsAppAlertService()
    result = service.send(
        message='Setu dry run test alert',
        dry_run=True,
        recipient='whatsapp:+919999999999',
    )
    assert result['status'] == 'dry-run'
    assert 'Setu dry run' in result['message']
    assert result['recipient'] == 'whatsapp:+919999999999'


@pytest.mark.anyio
async def test_manual_alert_test_endpoint(async_client):
    login_res = await async_client.post(
        '/api/v1/auth/login',
        json={'username': 'ramesh_farmer', 'password': 'setu2026'}
    )
    assert login_res.status_code == 200
    token = login_res.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    response = await async_client.post(
        '/api/v1/control/shed_01/alerts/test',
        json={
            'message': 'Manual alert simulation for cooling decision',
            'dry_run': True,
            'recipient': 'whatsapp:+919999999999',
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data['status'] in {'dry-run', 'sent', 'disabled'}
    assert 'message' in data


@pytest.mark.anyio
async def test_whatsapp_verification_and_webhook_flow(async_client):
    login_res = await async_client.post(
        '/api/v1/auth/login',
        json={'username': 'ramesh_farmer', 'password': 'setu2026'}
    )
    assert login_res.status_code == 200
    token = login_res.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    # 1. Send verification
    verify_res = await async_client.post(
        '/api/v1/auth/whatsapp/send-verification',
        json={'whatsapp_number': '+919876543210'},
        headers=headers,
    )
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert 'sandbox_join_phrase' in verify_data
    assert verify_data['recipient'] == 'whatsapp:+919876543210'

    # Check user profile updated with unverified number
    me_res = await async_client.get('/api/v1/auth/me', headers=headers)
    assert me_res.status_code == 200
    user_data = me_res.json()
    assert user_data['whatsapp_number'] == '+919876543210'
    assert user_data['whatsapp_verified'] is False

    # 2. Confirm verification endpoint
    confirm_res = await async_client.post(
        '/api/v1/auth/whatsapp/confirm-verification',
        json={'verified': True},
        headers=headers,
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()['whatsapp_verified'] is True

    # 3. Simulate inbound Twilio webhook
    webhook_res = await async_client.post(
        '/api/v1/auth/whatsapp/webhook',
        data={
            'From': 'whatsapp:+919876543210',
            'Body': 'join stay-spread',
            'AccountSid': 'ACmock123'
        },
    )
    assert webhook_res.status_code == 200
    assert 'Response' in webhook_res.text
