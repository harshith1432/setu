import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends
from app.models.schemas import UserLogin, UserCreate, Token, UserOut
from app.core.security import verify_password, get_password_hash, create_access_token, get_current_user_payload
from app.services.db_service import (
    get_user_by_username,
    get_user_by_id,
    create_user,
    log_audit
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
def login(credentials: UserLogin):
    user = get_user_by_username(credentials.username)
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
        preferred_language=user["preferred_language"],
        role=user["role"],
        farm_name=user.get("farm_name", "Green Valley Sericulture Farm"),
        region=user.get("region", "Mulbagal, Kolar, KA"),
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
        "preferred_language": user_in.preferred_language,
        "role": "farmer",
        "farm_name": user_in.farm_name or "Green Valley Sericulture Farm",
        "region": user_in.region or "Mulbagal, Kolar, KA",
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
        preferred_language=new_user_data["preferred_language"],
        role="farmer",
        farm_name=new_user_data["farm_name"],
        region=new_user_data["region"],
        batch_id=new_user_data["batch_id"],
        dfl_capacity=new_user_data["dfl_capacity"],
        breed=new_user_data["breed"],
        is_active=True
    )
    return Token(access_token=access_token, user=user_out)

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
        preferred_language=user["preferred_language"],
        role=user["role"],
        farm_name=user.get("farm_name", "Green Valley Sericulture Farm"),
        region=user.get("region", "Mulbagal, Kolar, KA"),
        batch_id=user.get("batch_id", "SERI-2026-M04"),
        dfl_capacity=user.get("dfl_capacity", "200 DFL"),
        breed=user.get("breed", "Double Hybrid (FC1 x FC2)"),
        is_active=bool(user.get("is_active", 1))
    )
