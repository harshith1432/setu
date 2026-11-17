import pytest
import hmac
import hashlib
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.services.razorpay_service import (
    verify_payment_signature,
    verify_webhook_signature,
    create_razorpay_order
)
from app.services.enterprise_db import get_order_detail, list_public_products


@pytest.mark.anyio
async def test_razorpay_public_config():
    """Verify that public Razorpay config returns safe keys and currency without exposing secrets."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/api/v1/payments/razorpay/config")
        assert res.status_code == 200
        data = res.json()
        assert "key_id" in data
        assert data["currency"] == "INR"
        assert "is_configured" in data
        assert "mode" in data


def test_hmac_sha256_signature_verification():
    """Test cryptographic HMAC SHA256 payment verification logic."""
    test_secret = "test_secret_key_12345"
    order_id = "order_rzp_test_998877"
    payment_id = "pay_rzp_test_112233"

    # Compute valid signature
    payload = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(test_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    # Temporarily set secret for verification test
    original_secret = settings.RAZORPAY_KEY_SECRET
    original_key_id = settings.RAZORPAY_KEY_ID
    try:
        settings.RAZORPAY_KEY_SECRET = test_secret
        settings.RAZORPAY_KEY_ID = "rzp_test_key"

        # Valid signature should pass
        assert verify_payment_signature(order_id, payment_id, valid_sig) is True

        # Tampered signature should fail
        tampered_sig = valid_sig[:-4] + "ffff"
        assert verify_payment_signature(order_id, payment_id, tampered_sig) is False

        # Empty inputs should fail
        assert verify_payment_signature("", payment_id, valid_sig) is False
        assert verify_payment_signature(order_id, "", valid_sig) is False
        assert verify_payment_signature(order_id, payment_id, "") is False
    finally:
        settings.RAZORPAY_KEY_SECRET = original_secret
        settings.RAZORPAY_KEY_ID = original_key_id


@pytest.mark.anyio
async def test_razorpay_order_creation_and_verification_flow():
    """End-to-end integration test: create order, initiate Razorpay payment, verify signature and confirm order."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Register a test farmer
        phone = f"98{uuid.uuid4().int % 100000000:08d}"
        password = "SecurePassword@123"
        reg_res = await client.post("/api/v1/auth/register", json={
            "username": phone,
            "phone": phone,
            "password": password,
            "confirm_password": password,
            "full_name": "Ramesh Gowda",
            "role": "farmer",
            "farm_name": "Gowda Sericulture Farm",
            "region": "Ramanagara"
        })
        assert reg_res.status_code == 200

        # Login to get JWT
        login_res = await client.post("/api/v1/auth/login", json={
            "username": phone,
            "password": password
        })
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 2. Get a valid product
        prods = list_public_products()
        assert len(prods) > 0
        target_prod = prods[0]

        # 3. Initiate Razorpay order creation
        create_res = await client.post("/api/v1/payments/razorpay/create-order", headers=auth_headers, json={
            "items": [{"product_id": target_prod["id"], "quantity": 2}],
            "shipping_address": "Shed 4, Silk Board Road, Ramanagara, Karnataka - 562159",
            "payment_method": "UPI"
        })
        assert create_res.status_code == 200
        rzp_order_data = create_res.json()

        assert "order_id" in rzp_order_data
        assert "razorpay_order_id" in rzp_order_data
        assert "amount_minor_units" in rzp_order_data
        assert rzp_order_data["currency"] == "INR"
        assert rzp_order_data["customer_name"] == "Ramesh Gowda"

        local_order_id = rzp_order_data["order_id"]
        razorpay_order_id = rzp_order_data["razorpay_order_id"]

        # Check order initially created in PAYMENT_PENDING state
        order_pre = get_order_detail(local_order_id)
        assert order_pre is not None
        assert order_pre["status"] == "PAYMENT_PENDING"

        # 4. Verify Payment with Razorpay receipt
        fake_pay_id = f"pay_{uuid.uuid4().hex[:14]}"
        fake_signature = f"rzp_mock_sig_{uuid.uuid4().hex[:20]}"

        verify_res = await client.post("/api/v1/payments/razorpay/verify", headers=auth_headers, json={
            "order_id": local_order_id,
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": fake_pay_id,
            "razorpay_signature": fake_signature,
            "method": "UPI"
        })
        assert verify_res.status_code == 200
        verify_data = verify_res.json()
        assert verify_data["status"] == "success"
        assert verify_data["order_id"] == local_order_id
        assert verify_data["payment_id"] == fake_pay_id

        # 5. Verify database state updated to PAID
        order_post = get_order_detail(local_order_id)
        assert order_post is not None
        assert order_post["status"] == "PAID"
        assert order_post["razorpay_payment_id"] == fake_pay_id

        # Check invoices and payments
        assert "invoices" in order_post and len(order_post["invoices"]) > 0
        assert order_post["invoices"][0]["status"] == "PAID"

        assert "payments" in order_post and len(order_post["payments"]) > 0
        assert order_post["payments"][0]["provider"] == "RAZORPAY"
        assert order_post["payments"][0]["provider_payment_id"] == fake_pay_id
        assert order_post["payments"][0]["status"] == "SUCCESS"

        # 6. Check order payments retrieval endpoint
        get_payments_res = await client.get(f"/api/v1/payments/orders/{local_order_id}", headers=auth_headers)
        assert get_payments_res.status_code == 200
        payments_data = get_payments_res.json()
        assert payments_data["status"] == "PAID"
        assert len(payments_data["payments"]) > 0


@pytest.mark.anyio
async def test_razorpay_firebase_only_mode():
    """Verify Razorpay order initiation, verification, and persistence in pure Firebase/JSON fallback mode."""
    transport = ASGITransport(app=app)
    original_firebase_only = settings.USE_FIREBASE_ONLY
    try:
        settings.USE_FIREBASE_ONLY = True
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            phone = f"97{uuid.uuid4().int % 100000000:08d}"
            password = "SecurePassword@123"
            reg_res = await client.post("/api/v1/auth/register", json={
                "username": phone,
                "phone": phone,
                "password": password,
                "confirm_password": password,
                "full_name": "Suresh Patil",
                "role": "farmer",
                "farm_name": "Patil Farms",
                "region": "Belagavi"
            })
            assert reg_res.status_code == 200

            login_res = await client.post("/api/v1/auth/login", json={
                "username": phone,
                "password": password
            })
            assert login_res.status_code == 200
            token = login_res.json()["access_token"]
            auth_headers = {"Authorization": f"Bearer {token}"}

            prods = list_public_products()
            target_prod = prods[0]

            create_res = await client.post("/api/v1/payments/razorpay/create-order", headers=auth_headers, json={
                "items": [{"product_id": target_prod["id"], "quantity": 1}],
                "shipping_address": "Patil Farms, Belagavi, Karnataka",
                "payment_method": "CARD"
            })
            assert create_res.status_code == 200
            rzp_order = create_res.json()
            order_id = rzp_order["order_id"]

            fake_pay_id = f"pay_{uuid.uuid4().hex[:14]}"
            verify_res = await client.post("/api/v1/payments/razorpay/verify", headers=auth_headers, json={
                "order_id": order_id,
                "razorpay_order_id": rzp_order["razorpay_order_id"],
                "razorpay_payment_id": fake_pay_id,
                "razorpay_signature": "rzp_mock_sig_fb_mode",
                "method": "CARD"
            })
            assert verify_res.status_code == 200
            assert verify_res.json()["status"] == "success"

            order_post = get_order_detail(order_id)
            assert order_post is not None
            assert order_post["status"] == "PAID"
    finally:
        settings.USE_FIREBASE_ONLY = original_firebase_only


@pytest.mark.anyio
async def test_razorpay_webhook_event_handling():
    """Verify webhook endpoint accepts and processes Razorpay captured payment events."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        webhook_payload = {
            "entity": "event",
            "account_id": "acc_mock_12345",
            "event": "payment.captured",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_mock_webhook_999",
                        "entity": "payment",
                        "amount": 250000,
                        "currency": "INR",
                        "status": "captured",
                        "order_id": "order_mock_webhook_999",
                        "method": "upi",
                        "notes": {
                            "order_id": "ord_mock_test_123"
                        }
                    }
                }
            }
        }
        res = await client.post(
            "/api/v1/payments/razorpay/webhook",
            json=webhook_payload,
            headers={"X-Razorpay-Signature": "rzp_mock_webhook_signature"}
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
        assert res.json()["received"] == "payment.captured"


    """Verify webhook endpoint accepts and processes Razorpay captured payment events."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        webhook_payload = {
            "entity": "event",
            "account_id": "acc_mock_12345",
            "event": "payment.captured",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_mock_webhook_999",
                        "entity": "payment",
                        "amount": 250000,
                        "currency": "INR",
                        "status": "captured",
                        "order_id": "order_mock_webhook_999",
                        "method": "upi",
                        "notes": {
                            "order_id": "ord_mock_test_123"
                        }
                    }
                }
            }
        }
        res = await client.post(
            "/api/v1/payments/razorpay/webhook",
            json=webhook_payload,
            headers={"X-Razorpay-Signature": "rzp_mock_webhook_signature"}
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
        assert res.json()["received"] == "payment.captured"
