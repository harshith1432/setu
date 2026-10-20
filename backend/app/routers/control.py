from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import SetpointsUpdate, ManualActuatorOverride, ShedOverview
from app.services.telemetry_service import telemetry_service
from app.services.db_service import get_user_by_username
from app.services.whatsapp_alerts import alert_service
from app.core.security import get_current_user_payload

router = APIRouter(prefix="/control", tags=["Control & Automation"])

def verify_shed_control_access(
    shed_id: str,
    user_payload: dict = Depends(get_current_user_payload)
) -> dict:
    """
    SEC-06: Broken Object-Level Authorization (BOLA / IDOR) Protection.
    Verifies that the caller is either an admin/superadmin OR is assigned to the target shed.
    """
    role = user_payload.get("role")
    if role in ["admin", "superadmin"]:
        return user_payload

    username = user_payload.get("sub")
    if username:
        user = get_user_by_username(username)
        if user:
            user_shed = user.get("shed_id") or "shed_01"
            if user_shed == shed_id:
                return user_payload

    raise HTTPException(
        status_code=403,
        detail=f"Forbidden: You do not have authorization to control equipment in shed '{shed_id}'"
    )

@router.post("/{shed_id}/setpoints", response_model=ShedOverview)
def update_setpoints(
    shed_id: str,
    payload: SetpointsUpdate,
    user_payload: dict = Depends(verify_shed_control_access)
):
    """
    Update target setpoints (temperature, humidity, air quality, light lux, bulb brightness, and auto/manual toggle).
    Enforces object-level authorization (SEC-06).
    """
    return telemetry_service.update_setpoints(
        shed_id=shed_id,
        is_auto=payload.is_auto_mode,
        temp_target=payload.temp_target,
        hum_target=payload.humidity_target,
        air_quality_target=payload.air_quality_target,
        light_lux_target=payload.light_lux_target,
        light_brightness=payload.light_brightness
    )

@router.post("/{shed_id}/override", response_model=ShedOverview)
def manual_actuator_override(
    shed_id: str,
    payload: ManualActuatorOverride,
    user_payload: dict = Depends(verify_shed_control_access)
):
    """
    Manually toggle cooler, fan, heater, light, or adjust bulb brightness. Automatically enforces safety interlocks
    and object-level authorization (SEC-06).
    """
    valid_actuators = ["cooler", "fan", "heater", "light", "light_brightness"]
    if payload.actuator not in valid_actuators:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid actuator '{payload.actuator}'. Must be one of {valid_actuators}"
        )

    result = telemetry_service.manual_override_actuator(
        shed_id=shed_id,
        actuator=payload.actuator,
        state=payload.state,
        value=payload.value
    )
    return result


@router.post("/{shed_id}/alerts/test")
def test_alert_dispatch(
    shed_id: str,
    payload: dict,
    user_payload: dict = Depends(verify_shed_control_access)
):
    """Dry-run or real alert path for testing WhatsApp notifications without hardware."""
    message = payload.get("message") or "Setu WhatsApp alert test message."
    dry_run = bool(payload.get("dry_run", True))
    recipient = payload.get("recipient")
    return alert_service.send(message=message, recipient=recipient, dry_run=dry_run)

