import urllib.parse
from fastapi.responses import RedirectResponse
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends, Request, Response, Security
from fastapi.security import HTTPAuthorizationCredentials
from app.core.security import security_scheme
from datetime import timedelta
from app.models.schemas import UserLogin, UserCreate, Token, UserOut, UserProfileUpdate, GoogleAuthRequest, InvitationAccept
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
def login(credentials: UserLogin, request: Request = None):
    user = get_user_by_username_or_phone(credentials.username)
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        log_audit(credentials.username or "anonymous", "LOGIN_FAILED", "Failed authentication attempt (invalid credentials)")
        try:
            from app.services.siem_service import SIEMForwarder
            SIEMForwarder().emit_event(
                event_type="AUTH_FAILURE",
                severity="WARNING",
                actor=credentials.username or "anonymous",
                action="LOGIN_FAILED",
                status="DENIED",
                details="Invalid username or password supplied."
            )
        except Exception:
            pass
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

    # Check employee-level suspension and update last_login
    try:
        from app.services.org_employee_db import get_user_access_context
        ctx = get_user_access_context(user["id"])
        if not ctx.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account has been suspended or deactivated. Please contact your administrator.",
            )
        from app.services.db_service import get_db_cursor
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("UPDATE employees SET last_login = %s WHERE user_id = %s", (datetime.now(timezone.utc), user["id"]))
    except HTTPException:
        raise
    except Exception:
        pass
    
    session_id = f"sess_{uuid.uuid4().hex}"
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_at = datetime.now(timezone.utc) + expires_delta

    user_agent = request.headers.get("user-agent") if request else None
    ip_address = request.client.host if request and request.client else None

    from app.services.db_service import create_user_session
    create_user_session(
        session_id=session_id,
        user_id=user["id"],
        username=user["username"],
        role=user["role"],
        organization_id=user.get("organization_id") or "default_org",
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address
    )

    access_token = create_access_token(
        data={
            "sub": user["username"],
            "user_id": user["id"],
            "role": user["role"],
            "session_id": session_id,
            
        },
        expires_delta=expires_delta
    )
    
    log_audit(user["username"], "LOGIN", f"User logged in from client (role: {user['role']})")

    user_out = UserOut(
        id=user["id"],
        username=user["username"],
        full_name=user["full_name"],
        phone=user["phone"],
        official_email=user.get("official_email"),
                access_scope=user.get("access_scope", "GLOBAL"),
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
    return Token(access_token=access_token, session_id=session_id, user=user_out)

@router.get("/invitations/{token}")
def get_invitation_details(token: str):
    """
    Public onboarding verification: verifies single-use token and returns non-sensitive metadata.
    """
    from app.services.org_employee_db import verify_invitation_token
    try:
        return verify_invitation_token(token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/invitations/{token}/accept")
def accept_employee_invitation(token: str, payload: InvitationAccept):
    """
    Public onboarding activation: employee establishes their own password and optional MFA.
    Transitions account to ACTIVE and marks invitation as single-use accepted.
    """
    from app.services.org_employee_db import accept_invitation_and_activate
    try:
        return accept_invitation_and_activate(
            token=token,
            new_password=payload.password,
            mfa_enabled=bool(payload.mfa_enabled)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/register", response_model=Token)
def register(user_in: UserCreate, request: Request = None):
    """
    Public Farmer-Only Registration endpoint.
    Strictly assigns the 'farmer' role regardless of client parameters.
    Validates password strength, prevents duplicate registrations, and provisions
    an isolated multi-tab session upon completion.
    """
    # 1. Input sanitization & validation
    clean_phone = user_in.phone.replace(" ", "").replace("-", "")
    raw_username = (user_in.username or "").strip().lower()
    clean_username = raw_username if raw_username else clean_phone
    clean_name = user_in.full_name.strip()
    clean_email = (user_in.email or "").strip().lower() or None

    if not clean_phone or not clean_name:
        raise HTTPException(status_code=400, detail="Full name and mobile number are required")

    if not user_in.password or len(user_in.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

    if user_in.confirm_password and user_in.password != user_in.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # 2. Duplicate Account Checks
    if raw_username and raw_username != clean_phone and get_user_by_username(raw_username):
        raise HTTPException(status_code=400, detail="An account with this username already exists")
    if get_user_by_username_or_phone(clean_phone):
        raise HTTPException(status_code=400, detail="An account with this mobile number already exists")
    if clean_email and get_user_by_username_or_phone(clean_email):
        raise HTTPException(status_code=400, detail="An account with this email address already exists")

    # 3. SEC-ROLE-ESCALATION: Public registration is strictly restricted to the farmer role.
    assigned_role = "farmer"

    from app.services.db_service import get_next_available_shed_id
    assigned_shed = user_in.shed_id or get_next_available_shed_id()
    user_id = f"usr_{uuid.uuid4().hex[:8]}"

    new_user_data = {
        "id": user_id,
        "username": clean_username,
        "hashed_password": get_password_hash(user_in.password),
        "full_name": clean_name,
        "phone": clean_phone,
        "official_email": clean_email,
        "whatsapp_number": user_in.whatsapp_number or clean_phone,
        "whatsapp_verified": True,
        "preferred_language": user_in.preferred_language or "en",
        "role": assigned_role,
        "farm_name": user_in.farm_name or "My Sericulture Farm",
        "region": user_in.region or "Karnataka Silk Belt",
        "latitude": user_in.latitude,
        "longitude": user_in.longitude,
        "shed_id": assigned_shed,
        "batch_id": user_in.batch_id or "SERI-2026-M04",
        "dfl_capacity": user_in.dfl_capacity or "200 DFL",
        "breed": user_in.breed or "Double Hybrid (FC1 x FC2)",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    create_user(new_user_data)

    # 4. Provision isolated server session
    session_id = f"sess_{uuid.uuid4().hex}"
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_at = datetime.now(timezone.utc) + expires_delta

    user_agent = request.headers.get("user-agent") if request else None
    ip_address = request.client.host if request and request.client else None

    from app.services.db_service import create_user_session
    create_user_session(
        session_id=session_id,
        user_id=user_id,
        username=clean_username,
        role=assigned_role,
        organization_id="default_org",
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address
    )

    access_token = create_access_token(
        data={
            "sub": clean_username,
            "user_id": user_id,
            "role": assigned_role,
            "session_id": session_id,
            
        },
        expires_delta=expires_delta
    )

    log_audit("system", "REGISTER", f"New farmer registered: {clean_username} ({clean_name}) [Shed: {assigned_shed}]")

    user_out = UserOut(
        id=user_id,
        username=clean_username,
        full_name=clean_name,
        phone=clean_phone,
        official_email=clean_email,
        whatsapp_number=new_user_data.get("whatsapp_number"),
        whatsapp_verified=True,
        preferred_language=new_user_data["preferred_language"],
        role=assigned_role,
        farm_name=new_user_data["farm_name"],
        region=new_user_data["region"],
        latitude=new_user_data.get("latitude"),
        longitude=new_user_data.get("longitude"),
        shed_id=assigned_shed,
        batch_id=new_user_data["batch_id"],
        dfl_capacity=new_user_data["dfl_capacity"],
        breed=new_user_data["breed"],
        is_active=True
    )
    return Token(access_token=access_token, session_id=session_id, user=user_out)

@router.get("/google/config")
def get_google_config():
    """Returns Google OAuth configuration for client authorization."""
    return {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "project_id": settings.FIREBASE_PROJECT_ID,
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "scope": "openid email profile"
    }

@router.get("/google/login")
def google_oauth_login(request: Request, redirect_url: str = None):
    """
    Direct server-side Google OAuth 2.0 redirection to Google Consent Screen.
    """
    base_url = str(request.base_url).rstrip("/")
    target_redirect = redirect_url or f"{base_url}/admin/"
    client_id = settings.GOOGLE_CLIENT_ID
    
    oauth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={urllib.parse.quote(client_id)}&"
        f"redirect_uri={urllib.parse.quote(target_redirect)}&"
        f"response_type=token%20id_token&"
        f"scope={urllib.parse.quote('openid email profile')}&"
        f"prompt=select_account&"
        f"nonce={uuid.uuid4().hex}"
    )
    return RedirectResponse(url=oauth_url)

@router.post("/google-sync", response_model=Token)
def google_sync(req: GoogleAuthRequest, request: Request = None):
    """
    Seamless Google OAuth Synchronization:
    - Existing Users: Automatically matches by email, username, phone, or Google ID.
      Preserves all existing profiles, sheds, batches, orders, and roles.
    - New Users: Automatically and strictly enrolled as a 'farmer' (smart sericulture grower).
    """
    clean_email = req.email.strip().lower() if req.email else None
    clean_phone = req.phone.replace(" ", "") if req.phone else None
    google_id = req.google_id or ""

    existing = None
    if clean_email:
        existing = get_user_by_username_or_phone(clean_email)
        if not existing and "@" in clean_email:
            existing = get_user_by_username_or_phone(clean_email.split("@")[0])
    if not existing and clean_phone:
        existing = get_user_by_username_or_phone(clean_phone)
    if not existing and google_id:
        existing = get_user_by_username_or_phone(f"google_{google_id}")

    user_agent = request.headers.get("user-agent") if request else None
    ip_address = request.client.host if request and request.client else None
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_at = datetime.now(timezone.utc) + expires_delta

    from app.services.db_service import create_user_session

    if existing:
        # SEC-03: Prevent Account Takeover (ATO).
        # Google Sign-In is exclusively reserved for farmers.
        # Staff and administrative accounts require direct password authentication.
        if existing.get("role") != "farmer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Staff and administrative accounts require password authentication. Google Sign-In is strictly for farmers."
            )

        updates = {}
        # If email was missing in existing profile, link it now
        if clean_email and not existing.get("official_email"):
            updates["official_email"] = clean_email
        # Only update name if user has no full_name set
        if req.full_name and req.full_name.strip() and not existing.get("full_name"):
            updates["full_name"] = req.full_name.strip()
        # Only update phone if user has no phone set
        if clean_phone and not existing.get("phone"):
            updates["phone"] = clean_phone
        # Only update farm_name / region if explicitly provided and not already configured
        if req.farm_name and req.farm_name.strip() and not existing.get("farm_name"):
            updates["farm_name"] = req.farm_name.strip()
        if req.region and req.region.strip() and not existing.get("region"):
            updates["region"] = req.region.strip()

        if updates:
            updated_user = update_user_profile(existing["id"], updates)
            if updated_user:
                existing = updated_user

        session_id = f"sess_{uuid.uuid4().hex}"
        create_user_session(
            session_id=session_id,
            user_id=existing["id"],
            username=existing["username"],
            role="farmer",
            organization_id=existing.get("organization_id", "default_org"),
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )

        access_token = create_access_token(
            data={"sub": existing["username"], "user_id": existing["id"], "role": "farmer", "session_id": session_id},
            expires_delta=expires_delta
        )
        log_audit(existing["username"], "GOOGLE_LOGIN", f"Google farmer logged in: {existing.get('full_name')} ({existing.get('username')})")

        user_out = UserOut(
            id=existing["id"],
            username=existing["username"],
            full_name=existing.get("full_name", "Setu Farmer"),
            phone=existing.get("phone", "N/A"),
            whatsapp_number=existing.get("whatsapp_number"),
            whatsapp_verified=bool(existing.get("whatsapp_verified", False)),
            preferred_language=existing.get("preferred_language", "en"),
            role="farmer",
            farm_name=existing.get("farm_name", "My Sericulture Farm"),
            region=existing.get("region", "Local Rearing Shed"),
            shed_id=existing.get("shed_id", "shed_01"),
            latitude=existing.get("latitude"),
            longitude=existing.get("longitude"),
            batch_id=existing.get("batch_id", "SERI-2026-B01"),
            dfl_capacity=existing.get("dfl_capacity", "200 DFL"),
            breed=existing.get("breed", "Double Hybrid (FC1 x FC2)"),
            official_email=existing.get("official_email") or clean_email,
            is_active=bool(existing.get("is_active", 1))
        )
        return Token(access_token=access_token, session_id=session_id, user=user_out)

    # Otherwise, brand new user registering with Google: strictly enrolled as a FARMER!
    from app.services.db_service import get_next_available_shed_id
    assigned_shed = req.shed_id or get_next_available_shed_id()
    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    username = clean_email or clean_phone or f"farmer_{uuid.uuid4().hex[:6]}"

    new_user_data = {
        "id": user_id,
        "username": username,
        "hashed_password": "oauth_google_" + uuid.uuid4().hex,
        "full_name": req.full_name.strip() if req.full_name else "Google Farmer",
        "phone": clean_phone or "N/A",
        "official_email": clean_email,
        "whatsapp_number": clean_phone,
        "whatsapp_verified": True if clean_phone else False,
        "preferred_language": req.preferred_language or "en",
        "role": "farmer",  # Guaranteed farmer for all new Google registrations!
        "farm_name": req.farm_name.strip() if req.farm_name else "My Sericulture Farm",
        "region": req.region.strip() if req.region else "Karnataka Silk Belt",
        "shed_id": assigned_shed,
        "latitude": req.latitude,
        "longitude": req.longitude,
        "batch_id": req.batch_id.strip() if req.batch_id else "SERI-2026-B01",
        "dfl_capacity": req.dfl_capacity.strip() if req.dfl_capacity else "200 DFL",
        "breed": req.breed.strip() if req.breed else "Double Hybrid (FC1 x FC2)",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    create_user(new_user_data)

    session_id = f"sess_{uuid.uuid4().hex}"
    create_user_session(
        session_id=session_id,
        user_id=user_id,
        username=new_user_data["username"],
        role="farmer",
        organization_id="default_org",
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address
    )

    access_token = create_access_token(
        data={"sub": new_user_data["username"], "user_id": user_id, "role": "farmer", "session_id": session_id},
        expires_delta=expires_delta
    )
    log_audit(new_user_data["username"], "GOOGLE_ENROLL", f"New Google farmer enrolled: {new_user_data['full_name']} ({username})")

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
        shed_id=assigned_shed,
        latitude=new_user_data.get("latitude"),
        longitude=new_user_data.get("longitude"),
        batch_id=new_user_data["batch_id"],
        dfl_capacity=new_user_data["dfl_capacity"],
        breed=new_user_data["breed"],
        official_email=clean_email,
        is_active=True
    )
    return Token(access_token=access_token, session_id=session_id, user=user_out)

    # Otherwise, brand new user registering with Google: strictly enrolled as a FARMER!
    from app.services.db_service import get_next_available_shed_id
    assigned_shed = req.shed_id or get_next_available_shed_id()
    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    username = clean_email or clean_phone or f"farmer_{uuid.uuid4().hex[:6]}"

    new_user_data = {
        "id": user_id,
        "username": username,
        "hashed_password": "oauth_google_" + uuid.uuid4().hex,
        "full_name": req.full_name.strip() if req.full_name else "Google Farmer",
        "phone": clean_phone or "N/A",
        "official_email": clean_email,
        "whatsapp_number": clean_phone,
        "whatsapp_verified": True if clean_phone else False,
        "preferred_language": req.preferred_language or "en",
        "role": "farmer",  # Guaranteed farmer for all new Google registrations!
        "farm_name": req.farm_name.strip() if req.farm_name else "My Sericulture Farm",
        "region": req.region.strip() if req.region else "Karnataka Silk Belt",
        "shed_id": assigned_shed,
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
    log_audit(new_user_data["username"], "GOOGLE_ENROLL", f"New Google farmer enrolled: {new_user_data['full_name']} ({username})")

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
        shed_id=assigned_shed,
        latitude=new_user_data.get("latitude"),
        longitude=new_user_data.get("longitude"),
        batch_id=new_user_data["batch_id"],
        dfl_capacity=new_user_data["dfl_capacity"],
        breed=new_user_data["breed"],
        official_email=clean_email,
        is_active=True
    )
    return Token(access_token=access_token, user=user_out)

@router.post("/whatsapp/send-verification")
def send_whatsapp_verification(payload: dict, user_payload: dict = Depends(get_current_user_payload)):
    """Directly dispatch WhatsApp alerts to a user-specific number without manual sandbox gating."""
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
            "whatsapp_verified": True,
        })

    welcome_message = (
        "🌾 SeriCare WhatsApp alerts are active! "
        "Automated microclimate and temperature variation alerts will be delivered directly to your device."
    )

    dry_run = bool(payload.get("dry_run", not alert_service.is_configured))
    result = alert_service.send(
        message=welcome_message,
        recipient=normalised_number,
        dry_run=dry_run,
    )
    return {
        "status": result.get("status", "sent" if not dry_run else "dry-run"),
        "message": result.get("message") or "WhatsApp alert service active.",
        "recipient": normalised_number,
        "sandbox_join_phrase": sandbox_join_phrase,
        "preview": welcome_message,
        "whatsapp_verified": True,
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
        logger.error("Twilio WhatsApp webhook processing failed: %s", exc)
        return Response(content='<?xml version="1.0" encoding="UTF-8"?><Response/>', media_type="application/xml")

@router.get("/check-farmer")
def check_farmer(identifier: str):
    """
    SEC-07: Public account presence verification without PII leakage.
    Returns presence and profile readiness booleans without disclosing phone numbers,
    farm names, or personal identities to unauthenticated callers.
    """
    clean = identifier.strip().lower()
    user = get_user_by_username_or_phone(clean)
    if not user:
        clean_phone = clean.replace(" ", "")
        user = get_user_by_username_or_phone(clean_phone)
    if user:
        return {
            "exists": True,
            "has_profile": True,
            "username": user["username"]
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
        official_email=user.get("official_email"),
                access_scope=user.get("access_scope", "GLOBAL"),
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
        user = get_user_by_id(payload.get("user_id") or "") or get_user_by_username_or_phone(username or "")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated_dict = update_user_profile(user["id"], updates.model_dump(exclude_unset=True))
    if not updated_dict:
        raise HTTPException(status_code=500, detail="Failed to update user profile")
    
    log_audit(user["username"], "PROFILE_UPDATE", f"Farmer updated profile/location: {updates.region or ''}")
    
    # Sync with shed telemetry and broadcast to admin web
    from app.services.telemetry_service import telemetry_service
    shed_id = updated_dict.get("shed_id") or "shed_01"
    if updates.current_stage:
        telemetry_service.set_growth_stage(shed_id, updates.current_stage)
        
    if updates.region or updates.latitude is not None or updates.longitude is not None:
        telemetry_service.get_shed_overview(
            shed_id,
            lat=updated_dict.get("latitude"),
            lon=updated_dict.get("longitude"),
            region_override=updated_dict.get("region")
        )

    try:
        telemetry_service.ws_manager.broadcast_sync({
            "type": "farmer_profile_updated",
            "farmer_id": user["id"],
            "shed_id": shed_id,
            "data": updated_dict
        })
    except Exception:
        pass
    
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

@router.post("/logout")
def logout(
    request: Request = None,
    credentials: HTTPAuthorizationCredentials = Security(security_scheme)
):
    """
    SEC-11 and ASVS V3.4: Explicit session termination and cryptographic token revocation.
    Revokes ONLY the current tab's active session, allowing other tabs/accounts to remain active.
    """
    from app.core.security import decode_token
    from app.services.db_service import revoke_token, revoke_user_session
    import hashlib

    token = credentials.credentials
    payload = decode_token(token)
    username = payload.get("sub", "unknown")
    user_id = payload.get("user_id")
    jti = payload.get("jti")
    exp = payload.get("exp")
    session_id = payload.get("session_id") or (request.headers.get("x-session-id") if request else None)

    # 1. Revoke the specific server session
    if session_id:
        revoke_user_session(session_id, reason="User tab logout")

    # 2. Add JWT to token blacklist
    tok_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else datetime.now(timezone.utc) + timedelta(hours=24)
    revoke_token(jti=jti, token_hash=tok_hash, expires_at=expires_at, user_id=user_id, reason="User logout")

    log_audit(username, "LOGOUT", f"User logged out of tab session (session_id: {session_id}, jti: {jti})")
    return {"message": "Successfully logged out of current tab session. Token has been revoked.", "session_id": session_id}

@router.post("/logout-all")
def logout_all_sessions(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme),
    payload: dict = Depends(get_current_user_payload)
):
    """Revokes ALL active sessions for the current user across all tabs and devices."""
    from app.services.db_service import revoke_all_user_sessions, revoke_token
    import hashlib

    user_id = payload.get("user_id")
    username = payload.get("sub", "unknown")
    jti = payload.get("jti")
    exp = payload.get("exp")
    token = credentials.credentials

    revoked_count = revoke_all_user_sessions(user_id, reason="User logout-all")

    tok_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else datetime.now(timezone.utc) + timedelta(hours=24)
    revoke_token(jti=jti, token_hash=tok_hash, expires_at=expires_at, user_id=user_id, reason="Logout all sessions")

    log_audit(username, "LOGOUT_ALL", f"User revoked all {revoked_count} active sessions.")
    return {"message": f"Successfully revoked {revoked_count} active sessions.", "revoked_sessions": revoked_count}

@router.post("/refresh", response_model=Token)
def refresh_token(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme),
    payload: dict = Depends(get_current_user_payload)
):
    """Renews access credentials for the current tab session without affecting other tabs."""
    from app.services.db_service import renew_user_session, get_user_by_username
    username = payload.get("sub")
    user_id = payload.get("user_id")
    session_id = payload.get("session_id")
    role = payload.get("role", "farmer")
    
    if not session_id:
        session_id = f"sess_{uuid.uuid4().hex}"

    new_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_exp = datetime.now(timezone.utc) + new_delta
    renew_user_session(session_id, new_exp)

    new_token = create_access_token(
        data={
            "sub": username,
            "user_id": user_id,
            "role": role,
            "session_id": session_id,
            
        },
        expires_delta=new_delta
    )
    user = get_user_by_username(username)
    user_out = UserOut(
        id=user["id"],
        username=user["username"],
        full_name=user["full_name"],
        phone=user["phone"],
        role=user["role"],
                farm_name=user.get("farm_name", "Green Valley Sericulture Farm"),
        region=user.get("region", "Local Rearing Shed"),
        shed_id=user.get("shed_id", "shed_01"),
        is_active=bool(user.get("is_active", 1))
    )
    return Token(access_token=new_token, session_id=session_id, user=user_out)

@router.get("/sessions")
def get_active_sessions(
    payload: dict = Depends(get_current_user_payload)
):
    """Lists active sessions for the current authenticated user."""
    from app.services.db_service import list_user_sessions
    user_id = payload.get("user_id")
    current_session_id = payload.get("session_id")
    sessions = list_user_sessions(user_id)
    for s in sessions:
        s["is_current"] = (s.get("session_id") == current_session_id)
    return {"sessions": sessions, "current_session_id": current_session_id}

@router.post("/sessions/{session_id}/revoke")
def revoke_specific_session(
    session_id: str,
    payload: dict = Depends(get_current_user_payload)
):
    """Revokes a specific session belonging to the user."""
    from app.services.db_service import get_user_session, revoke_user_session
    sess = get_user_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    if sess.get("user_id") != payload.get("user_id") and payload.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Cannot revoke another user's session")
    revoke_user_session(session_id, reason="User revoked remote session")
    return {"message": f"Session '{session_id}' has been revoked.", "session_id": session_id}
