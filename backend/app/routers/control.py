from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional, List, Dict, Any
from app.models.schemas import (
    SetpointsUpdate,
    ManualActuatorOverride,
    ShedOverview,
    DeviceCommandCreate,
    DeviceCommandAck,
    DeviceCommandOut,
    CommandStatus,
)
from app.services.telemetry_service import telemetry_service
from app.services.db_service import (
    get_user_by_username,
    get_user_by_id,
    create_device_command,
    acknowledge_device_command,
    get_pending_device_commands,
    get_device_command_by_id,
    get_farmer_by_shed_id,
)
from app.services.whatsapp_alerts import alert_service
from app.core.security import get_current_user_payload
from app.core.config import settings

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
    if role in ["admin", "superadmin", "company_admin", "operations_manager", "technician"]:
        return user_payload

    username = user_payload.get("sub")
    if username:
        user = get_user_by_username(username) or get_user_by_id(username)
        if user:
            user_shed = user.get("shed_id") or "shed_01"
            if user_shed == shed_id or user.get("id") == shed_id or f"shed_{user.get('id')}" == shed_id:
                return user_payload

    raise HTTPException(
        status_code=403,
        detail=f"Forbidden: You do not have authorization to control equipment in shed '{shed_id}'"
    )

def verify_device_or_operator_auth(
    x_device_key: Optional[str] = Header(None, alias="X-Device-Key"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None)
) -> dict:
    if (x_device_key and x_device_key == settings.DEVICE_API_KEY) or (x_api_key and x_api_key == settings.DEVICE_API_KEY):
        return {"auth_type": "device", "identity": "iot_node"}
    if authorization and authorization.startswith("Bearer "):
        from app.core.security import decode_token
        try:
            payload = decode_token(authorization.split(" ")[1])
            if payload and "sub" in payload:
                return {"auth_type": "user", "identity": payload.get("sub"), "payload": payload}
        except Exception:
            pass
    raise HTTPException(status_code=401, detail="Valid X-Device-Key or operator Bearer token required")


# --- Safe Command Lifecycle Endpoints ---

@router.post("/commands", response_model=Dict[str, Any])
def submit_device_command(
    cmd: DeviceCommandCreate,
    user_payload: dict = Depends(get_current_user_payload)
):
    """
    Creates an explicit, auditable command in the safe lifecycle:
    REQUESTED -> AUTHORIZED -> QUEUED -> SENT -> ACKNOWLEDGED -> APPLIED
    Enforces expiration, idempotency, and audit trail.
    """
    caller = user_payload.get("sub") or "operator"
    # Derive shed from device or caller
    shed_id = f"shed_{cmd.device_id.split('_')[-1]}" if "_" in cmd.device_id else "shed_01"
    # SEC-06 & BOLA Protection: Verify caller has access to control this shed
    verify_shed_control_access(shed_id, user_payload)
    command_record = create_device_command(
        device_id=cmd.device_id,
        shed_id=shed_id,
        requested_by=caller,
        command_type=cmd.command_type,
        command_payload=cmd.command_payload,
        expires_in_seconds=cmd.expires_in_seconds,
        correlation_id=cmd.correlation_id,
    )
    return {
        "status": "QUEUED",
        "command": command_record
    }

@router.post("/commands/ack")
def acknowledge_command(
    ack: DeviceCommandAck,
    auth_info: dict = Depends(verify_device_or_operator_auth)
):
    """
    Hardware device acknowledgement endpoint.
    Hardware nodes call this to report execution (APPLIED) or hardware failure/rejection (REJECTED / FAILED).
    """
    res = acknowledge_device_command(
        command_id=ack.command_id,
        device_id=ack.device_id,
        status=ack.status.value if hasattr(ack.status, "value") else str(ack.status),
        error_message=ack.error_message,
        applied_state=ack.applied_state
    )
    if not res:
        raise HTTPException(status_code=404, detail="Command not found or device mismatch")
    return {"status": "success", "command": res}

@router.get("/commands/{device_id}/pending")
def list_pending_commands(
    device_id: str,
    auth_info: dict = Depends(verify_device_or_operator_auth)
):
    """
    Returns non-expired, pending commands queued for this hardware node.
    Enables reliable polling and offline recovery for reconnecting nodes.
    """
    pending = get_pending_device_commands(device_id)
    return {"device_id": device_id, "pending_count": len(pending), "commands": pending}

@router.get("/commands/status/{command_id}")
def get_command_status(
    command_id: str,
    user_payload: dict = Depends(get_current_user_payload)
):
    """Farmer/operator endpoint to inspect exact lifecycle state of an issued command.
    Enforces object-level authorization (SEC-06 / BOLA / OWASP A01)."""
    cmd = get_device_command_by_id(command_id)
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")
    verify_shed_control_access(cmd.get("shed_id", "shed_01"), user_payload)
    return cmd


# --- Legacy / Flutter App Compatible Endpoints ---

@router.post("/{shed_id}/setpoints", response_model=ShedOverview)
def update_setpoints(
    shed_id: str,
    payload: SetpointsUpdate,
    user_payload: dict = Depends(verify_shed_control_access)
):
    """
    Update target setpoints (temperature, humidity, air quality, light lux, bulb brightness, and auto/manual toggle).
    Enforces object-level authorization (SEC-06) and safe command creation.
    """
    caller_identifier = user_payload.get("sub") or user_payload.get("user_id")
    return telemetry_service.update_setpoints(
        shed_id=shed_id,
        is_auto=payload.is_auto_mode,
        is_advanced_mode=bool(payload.is_advanced_mode),
        temp_target=payload.temp_target,
        hum_target=payload.humidity_target,
        air_quality_target=payload.air_quality_target,
        light_lux_target=payload.light_lux_target,
        light_brightness=payload.light_brightness,
        caller_user=caller_identifier
    )

@router.post("/{shed_id}/override", response_model=ShedOverview)
def manual_actuator_override(
    shed_id: str,
    payload: ManualActuatorOverride,
    user_payload: dict = Depends(verify_shed_control_access)
):
    """
    Manually toggle cooler, fan, heater, light, or adjust bulb brightness.
    Automatically enforces safety interlocks, object-level authorization (SEC-06),
    and safe command lifecycle queuing.
    """
    valid_actuators = ["cooler", "fan", "heater", "light", "light_brightness"]
    if payload.actuator not in valid_actuators:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid actuator '{payload.actuator}'. Must be one of {valid_actuators}"
        )

    caller_identifier = user_payload.get("sub") or user_payload.get("user_id")
    result = telemetry_service.manual_override_actuator(
        shed_id=shed_id,
        actuator=payload.actuator,
        state=payload.state,
        value=payload.value,
        caller_user=caller_identifier
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
    if not recipient:
        farmer = get_farmer_by_shed_id(shed_id)
        if farmer:
            recipient = farmer.get("whatsapp_number") or farmer.get("phone")
    media_url = payload.get("media_url")
    return alert_service.send(message=message, recipient=recipient, dry_run=dry_run, media_url=media_url)
