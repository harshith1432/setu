import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.security import create_access_token


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def admin_token():
    return create_access_token(data={"sub": "admin", "role": "admin", "shed_id": "shed_01"})


@pytest.fixture
def farmer_token():
    return create_access_token(data={"sub": "farmer_01", "role": "farmer", "shed_id": "shed_01"})


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_public_products_list_and_category_filter(async_client):
    # 1. Fetch all public products
    res = await async_client.get("/api/v1/public/products")
    assert res.status_code == 200
    products = res.json()
    assert isinstance(products, list)
    assert len(products) >= 8

    # Verify every product has public publication_status = PUBLISHED
    for p in products:
        assert p.get("publication_status") == "PUBLISHED"
        assert "name" in p
        assert "category" in p
        assert "price_minor_units" in p
        assert "specifications" in p

    # 2. Filter by category
    cat_res = await async_client.get("/api/v1/public/products?category=IoT Gateways and Connectivity")
    assert cat_res.status_code == 200
    gateways = cat_res.json()
    assert len(gateways) >= 1
    for g in gateways:
        assert g["category"] == "IoT Gateways and Connectivity"


@pytest.mark.anyio
async def test_public_product_detail_by_id_and_slug(async_client):
    # Retrieve by ID
    res_id = await async_client.get("/api/v1/public/products/prod_gw_01")
    assert res_id.status_code == 200
    prod = res_id.json()
    assert prod["id"] == "prod_gw_01"
    assert "Gateway" in prod["name"]
    assert "specifications" in prod

    # Retrieve by Slug
    slug = prod.get("slug") or "setu-iot-industrial-gateway-node"
    res_slug = await async_client.get(f"/api/v1/public/products/{slug}")
    assert res_slug.status_code == 200
    assert res_slug.json()["id"] == "prod_gw_01"

    # Non-existent product returns 404
    res_404 = await async_client.get("/api/v1/public/products/non-existent-product-id-999")
    assert res_404.status_code == 404


@pytest.mark.anyio
async def test_draft_product_hidden_from_public(async_client, admin_token):
    # Admin creates a draft product
    import uuid
    draft_sku = f"SKU-DRAFT-{uuid.uuid4().hex[:6].upper()}"
    create_res = await async_client.post(
        "/api/v1/products",
        json={
            "sku": draft_sku,
            "name": "Experimental Sensor (Draft)",
            "category": "Sensors",
            "description": "Internal test sensor not ready for public release",
            "price_minor_units": 99000,
            "stock_quantity": 5,
            "unit": "unit"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert create_res.status_code == 200
    draft_prod = create_res.json()
    prod_id = draft_prod["id"]

    # Mark as DRAFT
    patch_res = await async_client.patch(
        f"/api/v1/products/{prod_id}/publication",
        json={"publication_status": "DRAFT"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert patch_res.status_code == 200

    # Public endpoint must not expose this draft product
    pub_detail = await async_client.get(f"/api/v1/public/products/{prod_id}")
    assert pub_detail.status_code == 404

    pub_list = await async_client.get("/api/v1/public/products")
    assert pub_list.status_code == 200
    public_ids = [p["id"] for p in pub_list.json()]
    assert prod_id not in public_ids


@pytest.mark.anyio
async def test_public_categories_and_faqs(async_client):
    # Categories
    cat_res = await async_client.get("/api/v1/public/categories")
    assert cat_res.status_code == 200
    cats = cat_res.json()
    assert isinstance(cats, list)
    assert len(cats) >= 3

    # FAQs
    faq_res = await async_client.get("/api/v1/public/faqs")
    assert faq_res.status_code == 200
    faqs = faq_res.json()
    assert isinstance(faqs, list)
    assert len(faqs) >= 9
    assert any("SeriCare" in f["answer"] for f in faqs)


@pytest.mark.anyio
async def test_enquiry_submission_persistence_and_admin_management(async_client, admin_token, farmer_token):
    # 1. Valid enquiry submission
    enq_payload = {
        "full_name": "Siddaraju Gowda",
        "organization": "Siddaraju Silks Co-op",
        "email": "siddaraju@gowda-sericulture.org",
        "phone": "+91 98451 99887",
        "state_region": "Karnataka",
        "product_id": "prod_gw_01",
        "product_name": "Setu IoT Industrial Gateway Node v2.4",
        "enquiry_type": "DEMO_REQUEST",
        "message": "We operate a 500 DFL cluster in Sidlaghatta and request an on-site technical demonstration.",
        "privacy_consent": True
    }
    submit_res = await async_client.post("/api/v1/public/enquiries", json=enq_payload)
    assert submit_res.status_code == 201
    body = submit_res.json()
    assert body["success"] is True
    ref = body["enquiry_reference"]
    assert ref.startswith("ENQ-2026-")
    enq_id = body["enquiry"]["id"]

    # 2. Validation error - invalid email
    bad_email_res = await async_client.post(
        "/api/v1/public/enquiries",
        json={**enq_payload, "email": "not-a-valid-email"}
    )
    assert bad_email_res.status_code == 422

    # 3. Validation error - missing consent
    no_consent_res = await async_client.post(
        "/api/v1/public/enquiries",
        json={**enq_payload, "privacy_consent": False}
    )
    assert no_consent_res.status_code == 400

    # 4. Admin retrieves enquiries list
    admin_list_res = await async_client.get(
        "/api/v1/enquiries",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_list_res.status_code == 200
    all_enqs = admin_list_res.json()
    assert any(e["id"] == enq_id for e in all_enqs)

    # 5. Admin updates status
    patch_res = await async_client.patch(
        f"/api/v1/enquiries/{enq_id}",
        json={
            "status": "CONTACTED",
            "assigned_to": "usr_sales_01",
            "notes": "Spoke with farm manager. Demo scheduled for Friday 11 AM."
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert patch_res.status_code == 200
    updated_enq = patch_res.json()
    assert updated_enq["status"] == "CONTACTED"
    assert updated_enq["assigned_to"] == "usr_sales_01"

    # 6. RBAC: Farmer cannot view admin enquiries
    farmer_forbidden = await async_client.get(
        "/api/v1/enquiries",
        headers={"Authorization": f"Bearer {farmer_token}"}
    )
    assert farmer_forbidden.status_code == 403


@pytest.mark.anyio
async def test_landing_page_static_assets_and_root_delivery(async_client):
    # 1. Fetch root with text/html Accept header
    root_res = await async_client.get("/", headers={"Accept": "text/html"})
    assert root_res.status_code == 200
    html = root_res.text
    assert "Smarter Sericulture. Healthier Silkworms. Better Insights." in html
    assert "Precision IoT for Silkworm Rearing Sheds" in html
    assert "id=\"hero\"" in html
    assert "id=\"products\"" in html
    assert "id=\"solutions\"" in html
    assert "id=\"how-it-works\"" in html
    assert "id=\"technology\"" in html
    assert "id=\"benefits\"" in html
    assert "id=\"operations\"" in html
    assert "id=\"installation\"" in html
    assert "id=\"faqs\"" in html
    assert "id=\"demo-request\"" in html
    assert "id=\"enquiryForm\"" in html
    assert "id=\"productDetailModal\"" in html

    # 2. Verify static stylesheet delivery
    css_res = await async_client.get("/landing/style.css")
    assert css_res.status_code == 200
    assert "--emerald-600: #059669;" in css_res.text

    # 3. Verify static application script delivery
    js_res = await async_client.get("/landing/app.js")
    assert js_res.status_code == 200
    assert "fetchLiveTelemetry" in js_res.text
    assert "openProductDetails" in js_res.text
