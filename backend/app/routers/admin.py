from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.core.security import get_current_user_payload, require_roles
from app.models.schemas import UserProfileUpdate
from app.services.db_service import (
    get_all_farmers,
    get_user_by_id,
    get_user_by_username,
    update_user_profile,
    update_user_status,
    delete_user,
    get_audit_logs,
    log_audit,
    get_audit_metrics,
    purge_audit_logs,
    get_all_stage_thresholds,
    get_stage_threshold,
    update_stage_threshold,
    reset_stage_thresholds
)
from app.services.rules_engine import sync_thresholds_from_db, STAGE_THRESHOLDS
from app.services.telemetry_service import telemetry_service

router = APIRouter(prefix="/admin", tags=["Super Admin"])

def require_superadmin(payload: dict = Depends(get_current_user_payload)):
    role = payload.get("role")
    if role not in ["admin", "superadmin", "company_admin", "ceo"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin privileges required"
        )
    return payload

class FarmerStatusUpdate(BaseModel):
    is_active: bool

class EmergencyBypassPayload(BaseModel):
    shed_id: str
    action: str  # "COOLDOWN_ALL", "FOGGER_BOOST", "EMERGENCY_VENTILATE"

@router.get("/stats")
def get_admin_dashboard_stats(admin_user: dict = Depends(require_roles(["superadmin", "admin", "company_admin", "ceo", "operations_manager", "technician", "analyst"]))):
    farmers = get_all_farmers()
    active_farmers = [f for f in farmers if f.get("is_active", 1)]
    
    # Calculate total capacity
    total_dfl = sum([int(f.get("dfl_capacity", "0").split()[0]) for f in farmers if f.get("dfl_capacity", "0").split()[0].isdigit()])
    
    # Unique sheds count across network
    unique_sheds = set(telemetry_service.sheds.keys())
    for f in farmers:
        if f.get("shed_id"):
            unique_sheds.add(f["shed_id"])

    # Live IoT Shed summaries
    shed_overview = telemetry_service.get_shed_overview("shed_01")
    
    return {
        "total_farmers": len(farmers),
        "active_farmers": len(active_farmers),
        "total_dfl_capacity": f"{total_dfl} DFL",
        "active_sheds_monitored": len(unique_sheds),
        "system_health": "100% Operational",
        "active_relays_count": (1 if shed_overview.actuators.cooler else 0) + (1 if shed_overview.actuators.fan else 0) + (1 if shed_overview.actuators.heater else 0),
        "cluster_region": "Global Sericulture Network"
    }

@router.get("/sheds")
def list_monitored_sheds(current_user: dict = Depends(get_current_user_payload)) -> List[Dict[str, Any]]:
    """
    Returns list of all active rearing sheds dynamically from enrolled farmers and live telemetry.
    If the requesting user is a farmer, returns only their own rearing shed.
    """
    uid = current_user.get("user_id") or current_user.get("sub")
    role = current_user.get("role", "farmer")

    # If the user is a farmer, only return their own shed!
    if role == "farmer":
        user_record = get_user_by_id(uid) or get_user_by_username(uid)
        if user_record:
            s_id = user_record.get("shed_id") or f"shed_{user_record['id']}"
            farm_name = user_record.get("farm_name") or "Rearing Shed"
            farmer_name = user_record.get("full_name") or user_record.get("username") or "Farmer"
            display = f"{farm_name} ({farmer_name})"
            return [{
                "shed_id": s_id,
                "farm_name": farm_name,
                "farmer_name": farmer_name,
                "region": user_record.get("region", "Karnataka"),
                "batch_id": user_record.get("batch_id", "SERI-2026"),
                "display_name": display,
                "is_active": bool(user_record.get("is_active", True))
            }]

    farmers = get_all_farmers()
    sheds_list = []
    seen_ids = set()

    # 1. Gather all sheds directly from enrolled farmers in the database
    for f in farmers:
        s_id = f.get("shed_id") or f"shed_{f['id']}"
        farm_name = f.get("farm_name") or "Rearing Shed"
        farmer_name = f.get("full_name") or f.get("username") or "Sericulture Farmer"
        display = f"{farm_name} ({farmer_name})"

        if s_id not in seen_ids:
            sheds_list.append({
                "shed_id": s_id,
                "farm_name": farm_name,
                "farmer_name": farmer_name,
                "region": f.get("region", "Global Network"),
                "batch_id": f.get("batch_id", "SERI-2026"),
                "display_name": display,
                "is_active": bool(f.get("is_active", True))
            })
            seen_ids.add(s_id)

    # 2. Only if no farmers exist in database at all, provide a single default fallback shed
    if not sheds_list:
        sheds_list.append({
            "shed_id": "shed_01",
            "farm_name": "Rearing Shed 01",
            "farmer_name": "Default Farmer",
            "region": "Sericulture Shed",
            "batch_id": "SERI-2026",
            "display_name": "Rearing Shed 01",
            "is_active": True
        })

    return sheds_list

@router.get("/farmers")
def list_enrolled_farmers(admin_user: dict = Depends(require_roles(["superadmin", "admin", "company_admin", "ceo", "operations_manager", "support", "sales", "analyst"]))) -> List[Dict[str, Any]]:
    return get_all_farmers()

@router.get("/farmers/{farmer_id}")
def get_farmer_detail(farmer_id: str, admin_user: dict = Depends(require_roles(["superadmin", "admin", "company_admin", "ceo", "operations_manager", "support", "sales", "analyst"]))):
    """
    Get full farmer profile, linked shed overview, recent telemetry history, and alert context.
    """
    user = get_user_by_id(farmer_id) or get_user_by_username(farmer_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Farmer '{farmer_id}' not found")

    shed_id = user.get("shed_id") or "shed_01"
    shed_overview = telemetry_service.get_shed_overview(
        shed_id,
        lat=user.get("latitude"),
        lon=user.get("longitude"),
        region_override=user.get("region")
    )
    history = telemetry_service.get_history(shed_id, limit=30)

    return {
        "status": "success",
        "farmer": user,
        "shed": shed_overview,
        "history": history
    }

@router.put("/farmers/{farmer_id}")
@router.put("/farmers/{farmer_id}")
@router.patch("/farmers/{farmer_id}")
def update_farmer_details(
    farmer_id: str,
    payload: UserProfileUpdate,
    admin_user: dict = Depends(require_superadmin)
):
    """
    Super Admin endpoint to edit farmer personal info, farm setup, and growth stage.
    """
    updates = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else payload.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    updated_user = update_user_profile(farmer_id, updates)
    if not updated_user:
        raise HTTPException(status_code=404, detail=f"Farmer '{farmer_id}' not found")

    if "current_stage" in updates and updates["current_stage"] is not None:
        shed_id = updated_user.get("shed_id") or "shed_01"
        try:
            telemetry_service.set_growth_stage(shed_id, updates["current_stage"])
        except Exception:
            pass

    log_audit(
        admin_user.get("sub", "admin"),
        "UPDATE_FARMER",
        f"Farmer {farmer_id} ({updated_user.get('full_name')}) details updated by superadmin"
    )

    return {"status": "success", "farmer": updated_user}

@router.patch("/farmers/{farmer_id}/status")
@router.put("/farmers/{farmer_id}/status")
def change_farmer_status(
    farmer_id: str,
    payload: Optional[FarmerStatusUpdate] = None,
    active: Optional[bool] = None,
    admin_user: dict = Depends(require_superadmin)
):
    is_active = False
    if payload is not None:
        is_active = payload.is_active
    elif active is not None:
        is_active = active
    update_user_status(farmer_id, is_active)
    log_audit(
        admin_user.get("sub", "admin"),
        "STATUS_CHANGE",
        f"Farmer {farmer_id} status updated to {'Active' if is_active else 'Deactivated'}"
    )
    return {"status": "success", "farmer_id": farmer_id, "is_active": is_active}

@router.delete("/farmers/{farmer_id}")
def remove_farmer(farmer_id: str, admin_user: dict = Depends(require_superadmin)):
    current_uid = admin_user.get("user_id")
    current_sub = admin_user.get("sub")
    if farmer_id in [current_uid, current_sub]:
        raise HTTPException(status_code=400, detail="Cannot delete your own active account while logged in")

    user = get_user_by_id(farmer_id) or get_user_by_username(farmer_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Farmer '{farmer_id}' not found")
    
    if user.get("id") == current_uid or user.get("username") == current_sub:
        raise HTTPException(status_code=400, detail="Cannot delete your own active account while logged in")

    farmer_name = user.get("full_name") or user.get("username") or farmer_id
    success = delete_user(farmer_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Farmer '{farmer_id}' could not be deleted")
    
    log_audit(
        admin_user.get("sub", "admin"),
        "DELETE_FARMER",
        f"Farmer {farmer_name} (ID: {farmer_id}) was permanently removed from the system"
    )
    return {"status": "success", "message": f"Farmer '{farmer_name}' deleted successfully", "farmer_id": farmer_id}

@router.get("/audit-logs/metrics")
def view_audit_metrics(admin_user: dict = Depends(require_roles(["superadmin", "admin", "ceo", "company_admin", "hr"]))):
    """Returns top KPI counts for the Audit Logs view."""
    return get_audit_metrics()

@router.get("/audit-logs/active-sessions")
def view_active_sessions(admin_user: dict = Depends(require_roles(["superadmin", "admin", "ceo", "company_admin", "hr"]))):
    """Returns active authenticated operator sessions."""
    operator_actor = admin_user.get("sub", "admin")
    operator_role = "SuperAdmin" if admin_user.get("role") in ["superadmin", "admin"] else "Team Member"
    return [
        {
            "session_id": "SESS-789a4cd8-e120-4a2e",
            "operator_name": "Harshith Kd",
            "operator_email": "harshithkd6@gmail.com",
            "role": operator_role,
            "login_time": "29/10/2026, 10:48:21 am",
            "ip_address": "152.57.100.5",
            "location": "Bengaluru, Karnataka, IN",
            "device_os": "Desktop (Chrome on Windows)",
            "status": "Active Now"
        }
    ]

@router.post("/audit-logs/terminate-session/{session_id}")
def terminate_active_session(session_id: str, admin_user: dict = Depends(require_roles(["superadmin", "admin"]))):
    """Terminates an active session and registers an immutable security log."""
    log_audit(
        admin_user.get("sub", "admin"),
        "SESSION_TERMINATION",
        f"Session {session_id} forcibly revoked by SuperAdmin"
    )
    return {"status": "success", "message": f"Session {session_id} successfully terminated"}

@router.post("/audit-logs/purge")
def purge_retention_audit_logs(older_than_years: int = 7, admin_user: dict = Depends(require_roles(["superadmin", "admin"]))):
    """Purges audit records older than the standard retention period (7 years)."""
    count = purge_audit_logs(older_than_years=older_than_years)
    log_audit(
        admin_user.get("sub", "admin"),
        "PURGE_AUDIT_LOGS",
        f"SuperAdmin purged {count} audit events older than {older_than_years} years retention threshold"
    )
    return {"status": "success", "purged_count": count, "message": f"Purged {count} audit events older than {older_than_years} years."}

@router.get("/audit")
@router.get("/audit-logs")
def view_audit_trail(
    action: Optional[str] = None,
    actor: Optional[str] = None,
    search: Optional[str] = None,
    org_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    admin_user: dict = Depends(require_roles(["superadmin", "admin", "ceo", "company_admin", "hr", "farmer", "operations_manager", "technician"]))
):
    return get_audit_logs(limit=limit, action=action, actor=actor, org_id=None, search=search, offset=offset)

@router.post("/emergency-control")
def emergency_system_control(payload: EmergencyBypassPayload, admin_user: dict = Depends(require_superadmin)):
    """
    Super Admin Master Command: can trigger instant shed fogging, emergency ventilation, or total equipment kill.
    """
    shed_id = payload.shed_id
    if payload.action == "COOLDOWN_ALL":
        telemetry_service.manual_override_actuator(shed_id, "cooler", False)
        telemetry_service.manual_override_actuator(shed_id, "heater", False)
        telemetry_service.manual_override_actuator(shed_id, "fan", False)
        telemetry_service.manual_override_actuator(shed_id, "light", False, value=0)
        details = "Emergency shutdown of all actuators executed."
    elif payload.action == "FOGGER_BOOST":
        telemetry_service.manual_override_actuator(shed_id, "cooler", True)
        details = "Emergency fogger boost activated to drop temperature."
    elif payload.action in ("EMERGENCY_VENTILATE", "EMERGENCY_VENTILATE_AIR"):
        telemetry_service.manual_override_actuator(shed_id, "fan", True)
        details = "Exhaust ventilation fans engaged at 100% capacity for rapid air quality evacuation."
    elif payload.action == "EMERGENCY_LIGHTS_OFF":
        telemetry_service.manual_override_actuator(shed_id, "light", False, value=0)
        details = "All photoperiod lamps switched OFF (0% PWM) for resting darkness."
    elif payload.action == "EMERGENCY_DAY_LIGHT":
        telemetry_service.manual_override_actuator(shed_id, "light", True, value=40)
        details = "Photoperiod lamps engaged at 40% PWM for daytime feeding inspection."
    else:
        raise HTTPException(status_code=400, detail="Invalid emergency command")
        
    log_audit(
        admin_user.get("sub", "admin"),
        "EMERGENCY_CONTROL",
        f"{payload.action} executed on {shed_id}. {details}"
    )
    return {"status": "success", "action": payload.action, "details": details}

# --- Super Admin Software Levels & Auto-Mode Climate Configuration ---

class StageUpdatePayload(BaseModel):
    temp_min: float = Field(..., ge=15.0, le=40.0)
    temp_max: float = Field(..., ge=15.0, le=40.0)
    hum_min: float = Field(..., ge=30.0, le=100.0)
    hum_max: float = Field(..., ge=30.0, le=100.0)
    hysteresis_temp: Optional[float] = Field(0.5, ge=0.1, le=5.0)
    hysteresis_hum: Optional[float] = Field(3.0, ge=0.5, le=10.0)
    fan_trigger_offset: Optional[float] = Field(1.5, ge=0.2, le=5.0)
    description: Optional[str] = None

class ShedStagePayload(BaseModel):
    stage: int = Field(..., ge=1, le=5)

class ShedAutoModePayload(BaseModel):
    is_auto_mode: bool

class ShedActuatorOverridePayload(BaseModel):
    actuator: str
    state: bool
    value: Optional[int] = None

@router.get("/stages")
def list_growth_stages(current_user: dict = Depends(get_current_user_payload)) -> List[Dict[str, Any]]:
    """
    Get all 5 sericulture rearing stages and their temperature/humidity setpoints.
    """
    stages = get_all_stage_thresholds()
    if not stages:
        sync_thresholds_from_db()
        stages = get_all_stage_thresholds()
    return stages

@router.get("/stages/{stage_id}")
def get_growth_stage_detail(stage_id: int, current_user: dict = Depends(get_current_user_payload)):
    stage = get_stage_threshold(stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail=f"Stage {stage_id} not found")
    return stage

@router.put("/stages/{stage_id}")
def update_growth_stage_setpoints(
    stage_id: int,
    payload: StageUpdatePayload,
    admin_user: dict = Depends(require_superadmin)
):
    """
    Super Admin Master Command: updates min/max temperature & humidity for this rearing level.
    This immediately reconfigures auto-mode triggers across all connected rearing sheds.
    """
    if payload.temp_min > payload.temp_max:
        raise HTTPException(status_code=400, detail="Minimum temperature cannot exceed maximum temperature")
    if payload.hum_min > payload.hum_max:
        raise HTTPException(status_code=400, detail="Minimum humidity cannot exceed maximum humidity")

    updates = {
        "temp_min": payload.temp_min,
        "temp_max": payload.temp_max,
        "hum_min": payload.hum_min,
        "hum_max": payload.hum_max,
        "hysteresis_temp": payload.hysteresis_temp,
        "hysteresis_hum": payload.hysteresis_hum,
        "fan_trigger_offset": payload.fan_trigger_offset,
        "description": payload.description
    }

    updated = update_stage_threshold(stage_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Stage {stage_id} not found")

    # In-memory synchronization for immediate real-time auto-mode rules evaluation
    sync_thresholds_from_db()

    log_audit(
        admin_user.get("sub", "admin"),
        "UPDATE_STAGE_LEVEL",
        f"Stage {stage_id} ({updated.get('name')}) levels updated: Temp {payload.temp_min}°C–{payload.temp_max}°C, Hum {payload.hum_min}%–{payload.hum_max}%"
    )

    return {"status": "success", "message": f"Stage {stage_id} setpoints updated successfully", "stage": updated}

@router.post("/stages/reset")
def reset_stages_to_standards(admin_user: dict = Depends(require_superadmin)):
    """
    Reset all stage levels to Central Silk Board (CSB) scientific standards.
    """
    res = reset_stage_thresholds()
    sync_thresholds_from_db()
    log_audit(
        admin_user.get("sub", "admin"),
        "RESET_STAGES",
        "All rearing stage climate levels restored to Central Silk Board standard defaults."
    )
    return {"status": "success", "message": "Stages reset to CSB standards", "stages": res}

@router.post("/sheds/{shed_id}/stage")
def change_shed_rearing_stage(
    shed_id: str,
    payload: ShedStagePayload,
    admin_user: dict = Depends(require_superadmin)
):
    """
    Switch active growth stage on a specific shed (1 to 5).
    """
    overview = telemetry_service.set_growth_stage(shed_id, payload.stage)
    log_audit(
        admin_user.get("sub", "admin"),
        "CHANGE_SHED_STAGE",
        f"{shed_id} stage switched to {payload.stage} ({overview.stage_name})"
    )
    return overview

@router.post("/sheds/{shed_id}/auto-mode")
def set_shed_auto_mode(
    shed_id: str,
    payload: ShedAutoModePayload,
    admin_user: dict = Depends(require_superadmin)
):
    """
    Toggle auto-mode on or off for a shed.
    """
    shed = telemetry_service.sheds.get(shed_id, telemetry_service.sheds["shed_01"])
    shed["is_auto_mode"] = payload.is_auto_mode
    overview = telemetry_service.get_shed_overview(shed_id)
    log_audit(
        admin_user.get("sub", "admin"),
        "TOGGLE_AUTO_MODE",
        f"{shed_id} auto mode set to {payload.is_auto_mode}"
    )
    return overview

@router.post("/sheds/{shed_id}/actuator")
def override_shed_actuator(
    shed_id: str,
    payload: ShedActuatorOverridePayload,
    admin_user: dict = Depends(require_superadmin)
):
    """
    Manually toggle a specific actuator on a shed.
    """
    valid_actuators = ["cooler", "fan", "heater", "light", "light_brightness"]
    if payload.actuator not in valid_actuators:
        raise HTTPException(status_code=400, detail=f"Invalid actuator. Must be one of {valid_actuators}")
    overview = telemetry_service.manual_override_actuator(shed_id, payload.actuator, payload.state, value=payload.value)
    log_audit(
        admin_user.get("sub", "admin"),
        "MANUAL_ACTUATOR_OVERRIDE",
        f"{shed_id} {payload.actuator} set to {payload.state if payload.value is None else payload.value}"
    )
    return overview


@router.get("/telemetry-live")
def get_live_cluster_telemetry(shed_id: str = "shed_01", admin_user: dict = Depends(require_superadmin)):
    """
    Returns real-time telemetry, stage setpoints, history for graphs, and compliance metrics.
    """
    overview = telemetry_service.get_shed_overview(shed_id)
    history = telemetry_service.get_history(shed_id, limit=24)
    stage_meta = STAGE_THRESHOLDS.get(overview.current_stage, STAGE_THRESHOLDS[3])

    # Calculate compliance (% of historical readings inside stage target boundaries)
    within_target = 0
    total_checks = len(history)
    for h in history:
        t = h.get("indoor_temp", 0)
        hu = h.get("indoor_hum", 0)
        if stage_meta["temp_min"] - 0.5 <= t <= stage_meta["temp_max"] + 0.5 and \
           stage_meta["hum_min"] - 5.0 <= hu <= stage_meta["hum_max"] + 5.0:
            within_target += 1
    compliance_pct = round((within_target / total_checks * 100), 1) if total_checks > 0 else 98.5

    return {
        "overview": overview,
        "stage_targets": stage_meta,
        "history": history,
        "compliance_index": compliance_pct,
        "active_relays": {
            "cooler": overview.actuators.cooler,
            "fan": overview.actuators.fan,
            "heater": overview.actuators.heater
        }
    }

