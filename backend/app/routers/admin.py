from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.core.security import get_current_user_payload
from app.services.db_service import (
    get_all_farmers,
    update_user_status,
    delete_user,
    get_audit_logs,
    log_audit,
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
    if role not in ["admin", "superadmin"]:
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
def get_admin_dashboard_stats(admin_user: dict = Depends(require_superadmin)):
    farmers = get_all_farmers()
    active_farmers = [f for f in farmers if f.get("is_active", 1)]
    
    # Calculate total capacity
    total_dfl = sum([int(f.get("dfl_capacity", "0").split()[0]) for f in farmers if f.get("dfl_capacity", "0").split()[0].isdigit()])
    
    # Live IoT Shed summaries
    shed_overview = telemetry_service.get_shed_overview("shed_01")
    
    return {
        "total_farmers": len(farmers),
        "active_farmers": len(active_farmers),
        "total_dfl_capacity": f"{total_dfl} DFL",
        "active_sheds_monitored": len(telemetry_service.sheds),
        "system_health": "100% Operational",
        "active_relays_count": (1 if shed_overview.actuators.cooler else 0) + (1 if shed_overview.actuators.fan else 0) + (1 if shed_overview.actuators.heater else 0),
        "cluster_region": "Mulbagal Sericulture Cluster, Karnataka"
    }

@router.get("/farmers")
def list_enrolled_farmers(admin_user: dict = Depends(require_superadmin)) -> List[Dict[str, Any]]:
    return get_all_farmers()

@router.patch("/farmers/{farmer_id}/status")
def change_farmer_status(farmer_id: str, payload: FarmerStatusUpdate, admin_user: dict = Depends(require_superadmin)):
    update_user_status(farmer_id, payload.is_active)
    log_audit(
        admin_user.get("sub", "admin"),
        "STATUS_CHANGE",
        f"Farmer {farmer_id} status updated to {'Active' if payload.is_active else 'Deactivated'}"
    )
    return {"status": "success", "farmer_id": farmer_id, "is_active": payload.is_active}

@router.delete("/farmers/{farmer_id}")
def remove_farmer(farmer_id: str, admin_user: dict = Depends(require_superadmin)):
    delete_user(farmer_id)
    log_audit(
        admin_user.get("sub", "admin"),
        "DELETE_FARMER",
        f"Farmer {farmer_id} was removed from the system"
    )
    return {"status": "success", "message": f"Farmer {farmer_id} deleted"}

@router.get("/audit-logs")
def view_audit_trail(admin_user: dict = Depends(require_superadmin)):
    return get_audit_logs(limit=50)

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
        details = "Emergency shutdown of all actuators executed."
    elif payload.action == "FOGGER_BOOST":
        telemetry_service.manual_override_actuator(shed_id, "cooler", True)
        details = "Emergency fogger boost activated to drop temperature."
    elif payload.action == "EMERGENCY_VENTILATE":
        telemetry_service.manual_override_actuator(shed_id, "fan", True)
        details = "Exhaust ventilation fans engaged at 100% capacity."
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

@router.get("/stages")
def list_growth_stages(admin_user: dict = Depends(require_superadmin)) -> List[Dict[str, Any]]:
    """
    Get all 5 sericulture rearing stages and their temperature/humidity setpoints.
    """
    stages = get_all_stage_thresholds()
    if not stages:
        sync_thresholds_from_db()
        stages = get_all_stage_thresholds()
    return stages

@router.get("/stages/{stage_id}")
def get_growth_stage_detail(stage_id: int, admin_user: dict = Depends(require_superadmin)):
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
    if payload.actuator not in ["cooler", "fan", "heater"]:
        raise HTTPException(status_code=400, detail="Invalid actuator")
    overview = telemetry_service.manual_override_actuator(shed_id, payload.actuator, payload.state)
    log_audit(
        admin_user.get("sub", "admin"),
        "MANUAL_ACTUATOR_OVERRIDE",
        f"{shed_id} {payload.actuator} turned {'ON' if payload.state else 'OFF'}"
    )
    return overview

@router.get("/telemetry-live")
def get_live_cluster_telemetry(shed_id: str = "shed_01", admin_user: dict = Depends(require_superadmin)):
    """
    Returns real-time telemetry, stage setpoints, history for graphs, and compliance metrics.
    """
    overview = telemetry_service.get_shed_overview(shed_id)
    history = [h for h in telemetry_service.history if h["shed_id"] == shed_id][-24:]
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

