from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from app.models.schemas import ShedOverview
from app.services.telemetry_service import telemetry_service
from app.services.db_service import get_user_by_username, update_user_profile
from app.core.security import get_current_user_payload

router = APIRouter(prefix="/sheds", tags=["Sheds"])

@router.get("/{shed_id}", response_model=ShedOverview)
def get_shed_status(
    shed_id: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    region: Optional[str] = None,
    payload: dict = Depends(get_current_user_payload)
):
    """
    Get live shed conditions, status headline, current stage, and equipment states.
    Uses real-time weather for the user's GPS coordinates or custom region.
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
def set_rearing_stage(shed_id: str, stage_num: int, payload: dict = Depends(get_current_user_payload)):
    """
    Update silkworm growth stage (1 to 5). Automates environment targets.
    """
    if stage_num < 1 or stage_num > 5:
        raise HTTPException(status_code=400, detail="Stage must be between 1 and 5 (Instars)")

    username = payload.get("sub")
    if username:
        user = get_user_by_username(username)
        if user:
            update_user_profile(user["id"], {"current_stage": stage_num})

    return telemetry_service.set_growth_stage(shed_id, stage_num)
