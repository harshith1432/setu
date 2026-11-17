from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import json

from app.core.security import get_current_user_payload
from app.services.razorpay_service import (
    get_razorpay_public_config,
    create_razorpay_order,
    verify_payment_signature,
    verify_webhook_signature,
    fetch_payment_details
)
from app.services.enterprise_db import (
    get_order_detail,
    create_customer_order,
    record_razorpay_payment,
    list_orders
)
from app.services.db_service import get_user_by_id, get_user_by_username, log_audit

router = APIRouter(prefix="/payments", tags=["payments"])
logger = logging.getLogger("payments_router")


class RazorpayCreateOrderPayload(BaseModel):
    order_id: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None
    shipping_address: Optional[str] = None
    payment_method: Optional[str] = "UPI"
    notes: Optional[str] = None


class RazorpayVerifyPaymentPayload(BaseModel):
    order_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    method: Optional[str] = "RAZORPAY"


@router.get("/razorpay/config")
def get_razorpay_configuration():
    """Returns safe, client-facing Razorpay configuration (Public Key ID)."""
    return get_razorpay_public_config()


@router.post("/razorpay/create-order")
def initiate_razorpay_order(
    payload: RazorpayCreateOrderPayload,
    user: dict = Depends(get_current_user_payload)
):
    """
    Initiates a Razorpay payment order for an existing or newly submitted order.
    Returns the Razorpay Order ID and transaction payload for frontend SDK initialization.
    """
    uid = user.get("user_id") or user.get("sub")
    if not uid:
        raise HTTPException(status_code=401, detail="Authentication required to initiate checkout payment.")

    target_user = get_user_by_id(uid) or get_user_by_username(uid)
    customer_name = target_user.get("full_name") if target_user else user.get("username", "Farmer")
    customer_phone = target_user.get("phone", "") if target_user else ""

    order = None
    if payload.order_id:
        order = get_order_detail(payload.order_id)
        if not order:
            raise HTTPException(status_code=404, detail=f"Order '{payload.order_id}' not found.")
    elif payload.items and len(payload.items) > 0:
        shipping_addr = (
            payload.shipping_address
            or (target_user.get("farm_name") + ", " + target_user.get("region") if target_user else "Karnataka Silk Belt")
        )
        try:
            order = create_customer_order(
                user_id=uid,
                items=payload.items,
                shipping_address=shipping_addr,
                payment_method=payload.payment_method or "UPI",
                notes=payload.notes or "Checkout via Razorpay Gateway",
                status="PAYMENT_PENDING"
            )
        except Exception as e:
            logger.error("Failed to create customer order for Razorpay checkout: %s", e)
            raise HTTPException(status_code=400, detail=f"Order creation failed: {str(e)}")
    else:
        raise HTTPException(
            status_code=400,
            detail="Either an existing 'order_id' or a non-empty list of 'items' must be provided."
        )

    total_minor_units = int(order.get("total_amount_minor_units") or 0)
    if total_minor_units < 100:
        raise HTTPException(status_code=400, detail="Total order amount must be at least ₹1.00 (100 paise).")

    notes = {
        "order_id": order.get("id"),
        "order_number": order.get("order_number", ""),
        "user_id": str(uid),
        "customer_name": customer_name
    }

    try:
        rzp_order = create_razorpay_order(
            amount_paise=total_minor_units,
            currency="INR",
            receipt=order.get("order_number"),
            notes=notes
        )
    except Exception as e:
        logger.error("Razorpay order creation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Payment gateway error: {str(e)}")

    public_cfg = get_razorpay_public_config()

    return {
        "order_id": order.get("id"),
        "order_number": order.get("order_number"),
        "razorpay_order_id": rzp_order.get("id"),
        "amount_minor_units": rzp_order.get("amount", total_minor_units),
        "currency": rzp_order.get("currency", "INR"),
        "key_id": public_cfg.get("key_id"),
        "is_mock": rzp_order.get("is_mock", False),
        "customer_name": customer_name,
        "customer_phone": customer_phone
    }


@router.post("/razorpay/verify")
def verify_razorpay_payment(
    payload: RazorpayVerifyPaymentPayload,
    user: dict = Depends(get_current_user_payload)
):
    """
    Verifies the cryptographic HMAC SHA256 payment signature from Razorpay.
    Upon verification, transitions the order, invoice, and payment status to PAID/SUCCESS.
    """
    is_valid = verify_payment_signature(
        razorpay_order_id=payload.razorpay_order_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        razorpay_signature=payload.razorpay_signature
    )

    if not is_valid:
        logger.warning(
            "Razorpay signature verification rejected for order %s (payment %s)",
            payload.order_id, payload.razorpay_payment_id
        )
        raise HTTPException(
            status_code=400,
            detail="Razorpay payment signature verification failed. Untrusted transaction."
        )

    actor = user.get("sub") or user.get("username", "customer")
    try:
        updated_order = record_razorpay_payment(
            order_id=payload.order_id,
            razorpay_order_id=payload.razorpay_order_id,
            razorpay_payment_id=payload.razorpay_payment_id,
            razorpay_signature=payload.razorpay_signature,
            method=payload.method or "RAZORPAY",
            actor=actor
        )
    except Exception as e:
        logger.error("Failed to record Razorpay payment for order %s: %s", payload.order_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to record payment: {str(e)}")

    return {
        "status": "success",
        "message": "Payment verified and order confirmed successfully.",
        "order_id": payload.order_id,
        "order_number": updated_order.get("order_number"),
        "payment_id": payload.razorpay_payment_id,
        "order": updated_order
    }


@router.post("/razorpay/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature")
):
    """
    Asynchronous Webhook listener for Razorpay platform notifications (payment.captured, order.paid).
    Validates webhook secret and ensures idempotent state alignment.
    """
    raw_body = await request.body()

    if x_razorpay_signature:
        valid_sig = verify_webhook_signature(raw_body, x_razorpay_signature)
        if not valid_sig:
            logger.warning("Rejected Razorpay webhook with invalid HMAC signature.")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        event = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook JSON body")

    event_type = event.get("event")
    logger.info("Received Razorpay webhook event: %s", event_type)

    if event_type in ("payment.captured", "order.paid"):
        payload_data = event.get("payload", {})
        payment_entity = payload_data.get("payment", {}).get("entity", {})
        notes = payment_entity.get("notes", {})
        order_id = notes.get("order_id")
        razorpay_order_id = payment_entity.get("order_id")
        razorpay_payment_id = payment_entity.get("id")

        if order_id and razorpay_payment_id:
            try:
                record_razorpay_payment(
                    order_id=order_id,
                    razorpay_order_id=razorpay_order_id or "",
                    razorpay_payment_id=razorpay_payment_id,
                    razorpay_signature="webhook_verified",
                    method=payment_entity.get("method", "RAZORPAY").upper(),
                    actor="razorpay_webhook"
                )
            except Exception as e:
                logger.debug("Webhook payment update notice: %s", e)

    return {"status": "ok", "received": event_type}


@router.get("/orders/{order_id}")
def get_order_payments(
    order_id: str,
    user: dict = Depends(get_current_user_payload)
):
    """Fetches payment records for a given order."""
    order = get_order_detail(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    role = user.get("role", "farmer")
    current_uid = user.get("user_id") or user.get("sub")
    if role == "farmer" and order.get("user_id") != current_uid:
        raise HTTPException(status_code=403, detail="Forbidden")

    return {
        "order_id": order_id,
        "order_number": order.get("order_number"),
        "status": order.get("status"),
        "total_amount_minor_units": order.get("total_amount_minor_units"),
        "payments": order.get("payments", []),
        "invoices": order.get("invoices", [])
    }
