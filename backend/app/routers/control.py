from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import SetpointsUpdate, ManualActuatorOverride, ShedOverview
from app.services.telemetry_service import telemetry_service
from app.core.security import get_current_user_payload

router = APIRouter(prefix="/control", tags=["Control & Automation"])

@router.post("/{shed_id}/setpoints", response_model=ShedOverview)
def update_setpoints(
    shed_id: str,
    payload: SetpointsUpdate,
    user_payload: dict = Depends(get_current_user_payload)
):
    """
    Update target setpoints (temperature setpoint, humidity setpoint, and auto/manual toggle).
    """
    return telemetry_service.update_setpoints(
        shed_id=shed_id,
        is_auto=payload.is_auto_mode,
        temp_target=payload.temp_target,
        hum_target=payload.humidity_target
    )

@router.post("/{shed_id}/override", response_model=ShedOverview)
def manual_actuator_override(
    shed_id: str,
    payload: ManualActuatorOverride,
    user_payload: dict = Depends(get_current_user_payload)
):
    """
    Manually toggle cooler, fan, or heater. Automatically enforces safety interlocks.
    """
    if payload.actuator not in ["cooler", "fan", "heater"]:
        raise HTTPException(status_code=400, detail="Invalid actuator. Must be cooler, fan, or heater")
    
    return telemetry_service.manual_override_actuator(
        shed_id=shed_id,
        actuator=payload.actuator,
        state=payload.state
    )
