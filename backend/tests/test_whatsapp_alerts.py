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
async def test_whatsapp_alert_service_dry_run(async_client):
    from app.services.whatsapp_alerts import WhatsAppAlertService

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
