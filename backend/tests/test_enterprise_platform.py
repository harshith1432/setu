from app.services.db_service import init_db
from app.services.enterprise_db import init_enterprise_tables
from app.services.org_employee_db import init_org_employee_tables

init_db()
init_enterprise_tables()
init_org_employee_tables()

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

@pytest.fixture
async def admin_token(async_client):
    res = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": settings.INITIAL_ADMIN_PASSWORD}
    )
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    return res.json()["access_token"]

@pytest.fixture
async def farmer_token(async_client):
    res = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "ramesh_farmer", "password": "setu2026"}
    )
    assert res.status_code == 200, f"Farmer login failed: {res.text}"
    return res.json()["access_token"]


@pytest.mark.anyio
async def test_dashboard_overview_kpis(async_client, admin_token):
    res = await async_client.get(
        "/api/v1/dashboard/overview",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "total_farmers" in data
    assert "active_farmers" in data
    assert "total_sheds" in data
    assert "online_devices" in data
    assert "active_subscriptions" in data
    assert "mrr_inr" in data
    assert "total_revenue_inr" in data
    assert "last_synced_at" in data
    # Ensure real non-empty data is returned
    assert data["total_farmers"] >= 1


@pytest.mark.anyio
async def test_dashboard_health(async_client, admin_token):
    res = await async_client.get(
        "/api/v1/dashboard/health",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["database"] == "CONNECTED"


@pytest.mark.anyio
async def test_analytics_trends(async_client, admin_token):
    res = await async_client.get(
        "/api/v1/analytics/trends?days=7",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "telemetry_trends" in data
    assert "order_trends" in data
    assert "regional_distribution" in data


@pytest.mark.anyio
async def test_products_crud_and_inventory(async_client, admin_token):
    import uuid
    test_sku = f"SKU-TEST-{uuid.uuid4().hex[:6].upper()}"
    create_res = await async_client.post(
        "/api/v1/products",
        json={
            "sku": test_sku,
            "name": "Automated Ultrasonic Fogger Test",
            "category": "Climate Control",
            "description": "High frequency piezoceramic mist disk for silkworm humidity",
            "price_minor_units": 450000,
            "currency": "INR",
            "stock_quantity": 15,
            "unit": "unit"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert create_res.status_code == 200
    prod = create_res.json()
    assert prod["sku"] == test_sku
    prod_id = prod["id"]

    # Test stock adjustment
    adj_res = await async_client.post(
        f"/api/v1/products/{prod_id}/stock-adjustment",
        json={
            "quantity_delta": 5,
            "movement_type": "PURCHASE",
            "reference_id": "PO-2026-99",
            "notes": "Direct supplier restock batch"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert adj_res.status_code == 200
    updated_prod = adj_res.json()
    assert updated_prod["stock_quantity"] == 20

    # Test inventory ledger
    ledger_res = await async_client.get(
        f"/api/v1/products/inventory-movements/ledger?product_id={prod_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert ledger_res.status_code == 200
    movements = ledger_res.json()
    assert len(movements) >= 2

    # Test product details update (name, category, price)
    put_res = await async_client.put(
        f"/api/v1/products/{prod_id}",
        json={
            "name": "Updated Automated Fogger Pro",
            "category": "Climate Control",
            "price_minor_units": 520000,
            "stock_quantity": 25
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert put_res.status_code == 200
    assert put_res.json()["name"] == "Updated Automated Fogger Pro"
    assert put_res.json()["price_minor_units"] == 520000

    # Test toggling archive status
    arch_res = await async_client.post(
        f"/api/v1/products/{prod_id}/toggle-archive",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert arch_res.status_code == 200
    assert arch_res.json()["is_active"] is False
    assert arch_res.json()["publication_status"] == "ARCHIVED"

    # Test restoring from archive
    restore_res = await async_client.post(
        f"/api/v1/products/{prod_id}/toggle-archive",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert restore_res.status_code == 200
    assert restore_res.json()["is_active"] is True

    # Test product deletion
    del_res = await async_client.delete(
        f"/api/v1/products/{prod_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert del_res.status_code == 200
    assert del_res.json()["id"] == prod_id

    # Verify 404 after deletion
    get_res = await async_client.get(
        f"/api/v1/products/{prod_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_res.status_code == 404


@pytest.mark.anyio
async def test_orders_and_invoices(async_client, admin_token, farmer_token):
    # 1. Fetch products to get a valid product ID
    prods_res = await async_client.get(
        "/api/v1/products?limit=5",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert prods_res.status_code == 200
    products = prods_res.json()
    assert len(products) > 0
    target_product = products[0]

    # 2. Farmer places an order via POST /api/v1/orders
    order_payload = {
        "items": [
            {"product_id": target_product["id"], "quantity": 2}
        ],
        "shipping_address": "Farm Shed 4, Ramanagara Silk Belt, Karnataka - 562159",
        "payment_method": "UPI",
        "notes": "Please deliver with calibrated sensor cables."
    }
    create_res = await async_client.post(
        "/api/v1/orders",
        json=order_payload,
        headers={"Authorization": f"Bearer {farmer_token}"}
    )
    assert create_res.status_code == 200, f"Order placement failed: {create_res.text}"
    created_order = create_res.json()
    assert created_order["order_number"].startswith("ORD-2026-")
    assert created_order["status"] == "PAID"
    assert len(created_order["items"]) == 1
    assert created_order["items"][0]["quantity"] == 2
    assert created_order["invoice"] is not None
    assert len(created_order["payments"]) >= 1

    # 3. Farmer lists their own orders
    farmer_orders_res = await async_client.get(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {farmer_token}"}
    )
    assert farmer_orders_res.status_code == 200
    farmer_orders = farmer_orders_res.json()
    assert any(o["id"] == created_order["id"] for o in farmer_orders)

    # 4. Admin lists all orders
    orders_res = await async_client.get(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert orders_res.status_code == 200
    orders = orders_res.json()
    assert isinstance(orders, list)

    inv_res = await async_client.get(
        "/api/v1/invoices",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert inv_res.status_code == 200

    sub_res = await async_client.get(
        "/api/v1/subscriptions",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert sub_res.status_code == 200


@pytest.mark.anyio
async def test_support_tickets_lifecycle(async_client, farmer_token, admin_token):
    # 1. Farmer creates ticket
    create_res = await async_client.post(
        "/api/v1/support/tickets",
        json={
            "subject": "Temperature Sensor Drift in Rack 2",
            "category": "SENSOR_CALIBRATION",
            "priority": "HIGH",
            "initial_message": "The SHT31 sensor on rack 2 is reading 2 degrees higher than mercury thermometer.",
            "shed_id": "shed_01"
        },
        headers={"Authorization": f"Bearer {farmer_token}"}
    )
    assert create_res.status_code == 200
    ticket = create_res.json()
    ticket_id = ticket["id"]

    # 2. Admin / Support responds
    reply_res = await async_client.post(
        f"/api/v1/support/tickets/{ticket_id}/messages",
        json={
            "message": "Field technician has been dispatched to recalibrate probe offset.",
            "is_internal": False
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert reply_res.status_code == 200

    # 3. Resolve ticket
    status_res = await async_client.patch(
        f"/api/v1/support/tickets/{ticket_id}/status",
        json={"status": "RESOLVED"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "RESOLVED"


@pytest.mark.anyio
async def test_installation_jobs(async_client, admin_token):
    res = await async_client.get(
        "/api/v1/installations",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    jobs = res.json()
    assert isinstance(jobs, list)

    team_res = await async_client.get(
        "/api/v1/installations/team",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert team_res.status_code == 200


@pytest.mark.anyio
async def test_guidance_articles_multilingual(async_client, admin_token):
    en_res = await async_client.get(
        "/api/v1/guidance?language=en",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert en_res.status_code == 200
    en_articles = en_res.json()
    assert len(en_articles) > 0

    kn_res = await async_client.get(
        "/api/v1/guidance?language=kn",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert kn_res.status_code == 200
    kn_articles = kn_res.json()
    assert len(kn_articles) > 0


@pytest.mark.anyio
async def test_sensors_and_calibration(async_client, admin_token):
    res = await async_client.get(
        "/api/v1/sensors?shed_id=shed_01",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    sensors = res.json()
    assert len(sensors) > 0
    sensor_id = sensors[0]["id"]

    cal_res = await async_client.post(
        f"/api/v1/sensors/{sensor_id}/calibrate",
        json={"calibration_offset": 0.4},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert cal_res.status_code == 200
    assert cal_res.json()["calibration_offset"] == 0.4


@pytest.mark.anyio
async def test_platform_integrations_status(async_client, admin_token):
    res = await async_client.get(
        "/api/v1/platform/integrations",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    integrations = res.json()
    assert len(integrations) >= 4
    # Ensure honest status keys exist
    keys = [item["provider_key"] for item in integrations]
    assert "razorpay" in keys
    assert "twilio" in keys
    assert "open_meteo" in keys


@pytest.mark.anyio
async def test_rbac_farmer_forbidden_from_admin_actions(async_client, farmer_token):
    # Farmer must not access platform overview KPIs
    kpi_res = await async_client.get(
        "/api/v1/dashboard/overview",
        headers={"Authorization": f"Bearer {farmer_token}"}
    )
    assert kpi_res.status_code == 403

    # Farmer must not create products
    prod_res = await async_client.post(
        "/api/v1/products",
        json={"sku": "SKU-HACK", "name": "Fake", "category": "Gateways", "price_minor_units": 100},
        headers={"Authorization": f"Bearer {farmer_token}"}
    )
    assert prod_res.status_code == 403


@pytest.mark.anyio
async def test_admin_portal_static_serving(async_client):
    res = await async_client.get("/admin/")
    assert res.status_code == 200
    assert "SeriCare" in res.text
    assert "Overview & KPIs" in res.text

    css_res = await async_client.get("/admin/style.css")
    assert css_res.status_code == 200
    assert "skin-bg" in css_res.text

    js_res = await async_client.get("/admin/app.js")
    assert js_res.status_code == 200
    assert "switchNavTab" in js_res.text


@pytest.mark.anyio
async def test_landing_page_serving(async_client):
    # 1. Direct landing route
    res = await async_client.get("/landing/")
    assert res.status_code == 200
    assert "SeriCare" in res.text
    assert "Autonomous Environmental Control" in res.text

    # 2. Static assets
    css = await async_client.get("/landing/style.css")
    assert css.status_code == 200
    assert "skin-bg" in css.text

    js = await async_client.get("/landing/app.js")
    assert js.status_code == 200
    assert "fetchLandingTelemetry" in js.text

    # 3. Home endpoint
    home_res = await async_client.get("/home")
    assert home_res.status_code == 200
    assert "SeriCare" in home_res.text

    # 4. Browser visiting / with text/html Accept header gets the landing page
    browser_res = await async_client.get("/", headers={"Accept": "text/html,application/xhtml+xml"})
    assert browser_res.status_code == 200
    assert "SeriCare" in browser_res.text
    assert "Autonomous Environmental Control" in browser_res.text

    # 5. API client visiting / gets JSON
    api_res = await async_client.get("/", headers={"Accept": "application/json"})
    assert api_res.status_code == 200
    data = api_res.json()
    assert data["status"] == "healthy"
    assert "landing_page" in data


@pytest.mark.anyio
async def test_global_search_endpoint(async_client, admin_token, farmer_token):
    # Test admin search
    res = await async_client.get(
        "/api/v1/platform/search?q=shed",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "sheds" in data
    assert "farmers" in data
    assert "devices" in data

    # Test farmer search with restricted role permissions
    res_farmer = await async_client.get(
        "/api/v1/platform/search?q=shed",
        headers={"Authorization": f"Bearer {farmer_token}"}
    )
    assert res_farmer.status_code == 200
    farmer_data = res_farmer.json()
    assert farmer_data["installation_jobs"] == []  # Farmer cannot see installation jobs


@pytest.mark.anyio
async def test_product_image_upload_and_creation(async_client, admin_token, farmer_token):
    import io
    headers = {"Authorization": f"Bearer {admin_token}"}
    file_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    files = {"file": ("automated_test_photo.png", io.BytesIO(file_bytes), "image/png")}

    # 1. Upload photo as admin
    up_res = await async_client.post("/api/v1/products/upload-image", headers=headers, files=files)
    assert up_res.status_code == 200
    up_data = up_res.json()
    assert up_data["success"] is True
    img_url = up_data["image_url"]
    assert img_url.startswith("/uploads/products/")

    # 2. Farmer forbidden from uploading product images
    farmer_res = await async_client.post(
        "/api/v1/products/upload-image",
        headers={"Authorization": f"Bearer {farmer_token}"},
        files={"file": ("bad.png", io.BytesIO(file_bytes), "image/png")}
    )
    assert farmer_res.status_code == 403

    # 3. Create product with uploaded image
    sku = "SKU-TEST-UP-99"
    prod_payload = {
        "sku": sku,
        "name": "Upload Verification Device",
        "category": "Sensors",
        "price_minor_units": 299900,
        "currency": "INR",
        "stock_quantity": 5,
        "images": [img_url]
    }
    create_res = await async_client.post("/api/v1/products", headers=headers, json=prod_payload)
    assert create_res.status_code == 200
    created = create_res.json()
    assert created["sku"] == sku
    assert created["images"] == [img_url]

    # 4. Clean up
    del_res = await async_client.delete(f"/api/v1/products/{created['id']}?force=true", headers=headers)
    assert del_res.status_code == 200
