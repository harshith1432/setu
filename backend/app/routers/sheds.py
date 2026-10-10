from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.models.schemas import ShedOverview
from app.services.telemetry_service import telemetry_service
from app.core.security import get_current_user_payload

router = APIRouter(prefix="/sheds", tags=["Sheds"])

@router.get("/{shed_id}", response_model=ShedOverview)
def get_shed_status(shed_id: str, payload: dict = Depends(get_current_user_payload)):
    """
    Get live shed conditions, status headline, current stage, and equipment states.
    """
    return telemetry_service.get_shed_overview(shed_id)

@router.post("/{shed_id}/stage/{stage_num}", response_model=ShedOverview)
def set_rearing_stage(shed_id: str, stage_num: int, payload: dict = Depends(get_current_user_payload)):
    """
    Update silkworm growth stage (1 to 5). Automates environment targets.
    """
    if stage_num < 1 or stage_num > 5:
        raise HTTPException(status_code=400, detail="Stage must be between 1 and 5 (Instars)")
    return telemetry_service.set_growth_stage(shed_id, stage_num)
