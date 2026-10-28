from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.models.schemas import ShedOverview
from app.services.telemetry_service import telemetry_service
from app.services.db_service import get_user_by_username, get_user_by_id, update_user_profile
from app.core.security import get_current_user_payload

router = APIRouter(prefix="/sheds", tags=["Sheds"])

def verify_shed_access(
    shed_id: str,
    payload: dict = Depends(get_current_user_payload)
) -> dict:
    """
    SEC-06 & BOLA/IDOR Protection:
    Ensures that regular farmers can only view and control their own assigned rearing shed.
    Superadmins and cluster operators are permitted across all sheds.
    """
    role = payload.get("role")
    if role in ["admin", "superadmin", "company_admin", "ceo", "operations_manager", "technician", "support", "sales", "analyst"]:
        return payload

    username = payload.get("sub") or payload.get("user_id")
    if username:
        user = get_user_by_username(username) or get_user_by_id(username)
        if user:
            user_shed = (user.get("shed_id") or "shed_01").lower()
            target_shed = shed_id.strip().lower()
            # Allow if user shed matches target, or user id matches
            if user_shed == target_shed or user.get("id", "").lower() == target_shed or f"shed_{user.get('id', '').lower()}" == target_shed:
                return payload

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Forbidden: You do not have authorization to access data for shed '{shed_id}'"
    )

@router.get("/{shed_id}", response_model=ShedOverview)
@router.get("/{shed_id}/overview", response_model=ShedOverview)
def get_shed_status(
    shed_id: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    region: Optional[str] = None,
    payload: dict = Depends(verify_shed_access)
):
    """
    Get live shed conditions, status headline, current stage, and equipment states.
    Uses real-time weather for the user's GPS coordinates or custom region.
    Protected with Broken Object-Level Authorization (BOLA / IDOR) check.
    """
    user_lat = lat
    user_lon = lon
    user_reg = region
    
    if (user_lat is None or user_lon is None) and not user_reg:
        username = payload.get("sub")
        if username:
            user = get_user_by_username(username)
            if user:
                user_lat = user.get("latitude")
                user_lon = user.get("longitude")
                user_reg = user.get("region")

    return telemetry_service.get_shed_overview(
        shed_id,
        lat=user_lat,
        lon=user_lon,
        region_override=user_reg
    )

@router.post("/{shed_id}/stage/{stage_num}", response_model=ShedOverview)
def set_rearing_stage(
    shed_id: str,
    stage_num: int,
    payload: dict = Depends(verify_shed_access)
):
    """
    Update silkworm growth stage (1 to 5). Automates environment targets.
    Protected with Broken Object-Level Authorization (BOLA / IDOR) check.
    """
    if stage_num < 1 or stage_num > 5:
        raise HTTPException(status_code=400, detail="Stage must be between 1 and 5 (Instars)")

    username = payload.get("sub")
    if username:
        user = get_user_by_username(username)
        if user:
            update_user_profile(user["id"], {"current_stage": stage_num})

    return telemetry_service.set_growth_stage(shed_id, stage_num)
