import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends, Request, Response
from app.models.schemas import UserLogin, UserCreate, Token, UserOut, UserProfileUpdate, GoogleAuthRequest
from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token, get_current_user_payload
from app.services.db_service import (
    get_user_by_username,
    get_user_by_username_or_phone,
    get_user_by_id,
    create_user,
    update_user_profile,
    set_user_whatsapp_verified,
    log_audit
)
from app.services.whatsapp_alerts import alert_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
def login(credentials: UserLogin):
    user = get_user_by_username_or_phone(credentials.username)
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active", 1):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated. Please contact Super Admin.",
        )
    
    access_token = create_access_token(
        data={"sub": user["username"], "user_id": user["id"], "role": user["role"]}
    )
    
    log_audit(user["username"], "LOGIN", f"User logged in from client (role: {user['role']})")

    user_out = UserOut(
        id=user["id"],
        username=user["username"],
        full_name=user["full_name"],
        phone=user["phone"],
        whatsapp_number=user.get("whatsapp_number"),
        whatsapp_verified=bool(user.get("whatsapp_verified", False)),
        preferred_language=user["preferred_language"],
        role=user["role"],
        farm_name=user.get("farm_name", "Green Valley Sericulture Farm"),
        region=user.get("region", "Local Rearing Shed"),
        batch_id=user.get("batch_id", "SERI-2026-M04"),
        dfl_capacity=user.get("dfl_capacity", "200 DFL"),
        breed=user.get("breed", "Double Hybrid (FC1 x FC2)"),
        is_active=bool(user.get("is_active", 1))
    )
    return Token(access_token=access_token, user=user_out)

@router.post("/register", response_model=Token)
def register(user_in: UserCreate):
    existing = get_user_by_username(user_in.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    new_user_data = {
        "id": user_id,
        "username": user_in.username,
        "hashed_password": get_password_hash(user_in.password),
        "full_name": user_in.full_name,
        "phone": user_in.phone,
        "whatsapp_number": user_in.whatsapp_number or user_in.phone,
        "whatsapp_verified": bool(user_in.whatsapp_verified),
        "preferred_language": user_in.preferred_language,
        "role": "farmer",
        "farm_name": user_in.farm_name or "Green Valley Sericulture Farm",
        "region": user_in.region or "Local Rearing Shed",
        "latitude": user_in.latitude,
        "longitude": user_in.longitude,
        "batch_id": user_in.batch_id or "SERI-2026-M04",
        "dfl_capacity": user_in.dfl_capacity or "200 DFL",
        "breed": user_in.breed or "Double Hybrid (FC1 x FC2)",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    create_user(new_user_data)
    
    access_token = create_access_token(
        data={"sub": new_user_data["username"], "user_id": user_id, "role": "farmer"}
    )
    
    log_audit("system", "REGISTER", f"New farmer registered: {new_user_data['username']} ({new_user_data['full_name']})")

    user_out = UserOut(
        id=user_id,
        username=new_user_data["username"],
        full_name=new_user_data["full_name"],
        phone=new_user_data["phone"],
        whatsapp_number=new_user_data.get("whatsapp_number"),
        whatsapp_verified=bool(new_user_data.get("whatsapp_verified", False)),
        preferred_language=new_user_data["preferred_language"],
        role="farmer",
        farm_name=new_user_data["farm_name"],
        region=new_user_data["region"],
        latitude=new_user_data.get("latitude"),
        longitude=new_user_data.get("longitude"),
        batch_id=new_user_data["batch_id"],
        dfl_capacity=new_user_data["dfl_capacity"],
        breed=new_user_data["breed"],
        is_active=True
    )
    return Token(access_token=access_token, user=user_out)

@router.post("/google-sync", response_model=Token)
def google_sync(req: GoogleAuthRequest):
    # Lookup by email or phone or username
    lookup_key = (req.email.strip().lower() if req.email else None) or (req.phone.replace(" ", "") if req.phone else None) or f"google_{req.google_id or uuid.uuid4().hex[:6]}"
    existing = get_user_by_username_or_phone(lookup_key)
    if not existing and req.phone:
        existing = get_user_by_username_or_phone(req.phone.replace(" ", ""))

    if existing:
        updates = {}
        if req.full_name and req.full_name.strip():
            updates["full_name"] = req.full_name.strip()
        if req.phone and req.phone.strip():
            updates["phone"] = req.phone.strip()
        if req.farm_name and req.farm_name.strip():
            updates["farm_name"] = req.farm_name.strip()
        if req.region and req.region.strip():
            updates["region"] = req.region.strip()
        if req.batch_id and req.batch_id.strip():
            updates["batch_id"] = req.batch_id.strip()
        if req.dfl_capacity and req.dfl_capacity.strip():
            updates["dfl_capacity"] = req.dfl_capacity.strip()
        if req.breed and req.breed.strip():
            updates["breed"] = req.breed.strip()
        if req.latitude is not None:
            updates["latitude"] = req.latitude
        if req.longitude is not None:
            updates["longitude"] = req.longitude

        if updates:
            updated_user = update_user_profile(existing["id"], updates)
            if updated_user:
                existing = updated_user

        access_token = create_access_token(
            data={"sub": existing["username"], "user_id": existing["id"], "role": existing.get("role", "farmer")}
        )
        log_audit(existing["username"], "GOOGLE_LOGIN", f"Google user logged in: {existing['full_name']}")

        user_out = UserOut(
            id=existing["id"],
            username=existing["username"],
            full_name=existing["full_name"],
            phone=existing.get("phone", "N/A"),
            whatsapp_number=existing.get("whatsapp_number"),
            whatsapp_verified=bool(existing.get("whatsapp_verified", False)),
            preferred_language=existing.get("preferred_language", "en"),
            role=existing.get("role", "farmer"),
            farm_name=existing.get("farm_name", "My Sericulture Farm"),
            region=existing.get("region", "Local Rearing Shed"),
            latitude=existing.get("latitude"),
            longitude=existing.get("longitude"),
            batch_id=existing.get("batch_id", "SERI-2026-B01"),
            dfl_capacity=existing.get("dfl_capacity", "200 DFL"),
            breed=existing.get("breed", "Double Hybrid (FC1 x FC2)"),
            is_active=bool(existing.get("is_active", 1))
        )
        return Token(access_token=access_token, user=user_out)

    # Otherwise create new enrolled farmer
    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    new_user_data = {
        "id": user_id,
        "username": lookup_key,
        "hashed_password": get_password_hash("oauth_google_" + uuid.uuid4().hex),
        "full_name": req.full_name.strip() if req.full_name else "Google Farmer",
        "phone": req.phone.strip() if req.phone else "N/A",
        "preferred_language": req.preferred_language or "en",
        "role": "farmer",
        "farm_name": req.farm_name.strip() if req.farm_name else "My Sericulture Farm",
        "region": req.region.strip() if req.region else "Local Rearing Shed",
        "latitude": req.latitude,
        "longitude": req.longitude,
        "batch_id": req.batch_id.strip() if req.batch_id else "SERI-2026-B01",
        "dfl_capacity": req.dfl_capacity.strip() if req.dfl_capacity else "200 DFL",
        "breed": req.breed.strip() if req.breed else "Double Hybrid (FC1 x FC2)",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    create_user(new_user_data)

    access_token = create_access_token(
        data={"sub": new_user_data["username"], "user_id": user_id, "role": "farmer"}
    )
    log_audit(new_user_data["username"], "GOOGLE_ENROLL", f"New Google farmer enrolled: {new_user_data['full_name']} ({lookup_key})")

    user_out = UserOut(
        id=user_id,
        username=new_user_data["username"],
        full_name=new_user_data["full_name"],
        phone=new_user_data["phone"],
        whatsapp_number=new_user_data.get("whatsapp_number"),
        whatsapp_verified=bool(new_user_data.get("whatsapp_verified", False)),
        preferred_language=new_user_data["preferred_language"],
        role="farmer",
        farm_name=new_user_data["farm_name"],
        region=new_user_data["region"],
        latitude=new_user_data.get("latitude"),
        longitude=new_user_data.get("longitude"),
        batch_id=new_user_data["batch_id"],
        dfl_capacity=new_user_data["dfl_capacity"],
        breed=new_user_data["breed"],
        is_active=True
    )
    return Token(access_token=access_token, user=user_out)

@router.post("/whatsapp/send-verification")
def send_whatsapp_verification(payload: dict, user_payload: dict = Depends(get_current_user_payload)):
    """Send a WhatsApp sandbox verification prompt for a user-specific number."""
    whatsapp_number = (payload.get("whatsapp_number") or payload.get("phone") or "").strip()
    if not whatsapp_number:
        raise HTTPException(status_code=400, detail="whatsapp_number is required")

    sandbox_join_phrase = getattr(settings, "TWILIO_SANDBOX_JOIN_PHRASE", "join stay-spread")
    normalised_number = alert_service.normalize_whatsapp(whatsapp_number)
    clean_digits = normalised_number.replace("whatsapp:", "")
    user_id = user_payload.get("user_id") or user_payload.get("sub")
    if user_id:
        update_user_profile(user_id, {
            "whatsapp_number": clean_digits,
            "whatsapp_verified": False,
        })

    verification_message = (
        f"Setu verification: reply with '{sandbox_join_phrase}' to confirm your WhatsApp number "
        f"for alerts."
    )

    dry_run = bool(payload.get("dry_run", not alert_service.is_configured))
    result = alert_service.send(
        message=verification_message,
        recipient=normalised_number,
        dry_run=dry_run,
    )
    return {
        "status": result.get("status", "dry-run"),
        "message": verification_message,
        "recipient": normalised_number,
        "sandbox_join_phrase": sandbox_join_phrase,
        "preview": verification_message,
    }

@router.post("/whatsapp/confirm-verification")
def confirm_whatsapp_verification(payload: dict, user_payload: dict = Depends(get_current_user_payload)):
    """Confirm WhatsApp verification status for the authenticated user."""
    user_id = user_payload.get("user_id") or user_payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="User context missing")
    verified = bool(payload.get("verified", True))
    set_user_whatsapp_verified(user_id, verified=verified)
    return {"status": "success", "whatsapp_verified": verified}

@router.post("/whatsapp/webhook")
async def twilio_whatsapp_webhook(request: Request):
    """Inbound webhook called by Twilio when farmer replies in WhatsApp sandbox."""
    try:
        form_data = await request.form()
        from_number = form_data.get("From", "")
        body = form_data.get("Body", "").strip()

        if from_number:
            clean_number = from_number.replace("whatsapp:", "").strip()
            set_user_whatsapp_verified(clean_number, verified=True)
            log_audit("twilio_webhook", "WHATSAPP_VERIFIED", f"WhatsApp verified for {clean_number} (Body: {body[:30]})")

        twiml_resp = '<?xml version="1.0" encoding="UTF-8"?><Response><Message>Your SeriCare WhatsApp alerts are now active!</Message></Response>'
        return Response(content=twiml_resp, media_type="application/xml")
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}

@router.get("/check-farmer")
def check_farmer(identifier: str):
    clean = identifier.strip().lower()
    user = get_user_by_username_or_phone(clean)
    if not user:
        clean_phone = clean.replace(" ", "")
        user = get_user_by_username_or_phone(clean_phone)
    if user:
        phone_val = user.get("phone", "")
        farm_val = user.get("farm_name", "")
        has_real_profile = (
            phone_val and phone_val != "N/A" and
            farm_val and farm_val != "My Sericulture Farm"
        )
        return {
            "exists": True,
            "has_profile": bool(has_real_profile),
            "user": {
                "id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "phone": user.get("phone"),
                "farm_name": user.get("farm_name"),
                "batch_id": user.get("batch_id"),
                "dfl_capacity": user.get("dfl_capacity"),
                "region": user.get("region"),
                "breed": user.get("breed"),
            }
        }
    return {"exists": False, "has_profile": False}

@router.get("/me", response_model=UserOut)
def get_current_user(payload: dict = Depends(get_current_user_payload)):
    username = payload.get("sub")
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(
        id=user["id"],
        username=user["username"],
        full_name=user["full_name"],
        phone=user["phone"],
        whatsapp_number=user.get("whatsapp_number"),
        whatsapp_verified=bool(user.get("whatsapp_verified", False)),
        preferred_language=user["preferred_language"],
        role=user["role"],
        farm_name=user.get("farm_name", "Green Valley Sericulture Farm"),
        region=user.get("region", "Local Rearing Shed"),
        latitude=user.get("latitude"),
        longitude=user.get("longitude"),
        batch_id=user.get("batch_id", "SERI-2026-M04"),
        dfl_capacity=user.get("dfl_capacity", "200 DFL"),
        breed=user.get("breed", "Double Hybrid (FC1 x FC2)"),
        is_active=bool(user.get("is_active", 1))
    )

@router.put("/profile", response_model=UserOut)
def update_profile(updates: UserProfileUpdate, payload: dict = Depends(get_current_user_payload)):
    username = payload.get("sub")
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated_dict = update_user_profile(user["id"], updates.model_dump(exclude_unset=True))
    if not updated_dict:
        raise HTTPException(status_code=500, detail="Failed to update user profile")
    
    log_audit(username, "PROFILE_UPDATE", f"Farmer updated profile/location: {updates.region or ''}")
    
    return UserOut(
        id=updated_dict["id"],
        username=updated_dict["username"],
        full_name=updated_dict["full_name"],
        phone=updated_dict["phone"],
        whatsapp_number=updated_dict.get("whatsapp_number"),
        whatsapp_verified=bool(updated_dict.get("whatsapp_verified", False)),
        preferred_language=updated_dict["preferred_language"],
        role=updated_dict["role"],
        farm_name=updated_dict.get("farm_name", "Green Valley Sericulture Farm"),
        region=updated_dict.get("region", "Local Rearing Shed"),
        latitude=updated_dict.get("latitude"),
        longitude=updated_dict.get("longitude"),
        batch_id=updated_dict.get("batch_id", "SERI-2026-M04"),
        dfl_capacity=updated_dict.get("dfl_capacity", "200 DFL"),
        breed=updated_dict.get("breed", "Double Hybrid (FC1 x FC2)"),
        is_active=bool(updated_dict.get("is_active", 1))
    )
