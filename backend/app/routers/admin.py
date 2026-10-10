from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any
from pydantic import BaseModel
from app.core.security import get_current_user_payload
from app.services.db_service import (
    get_all_farmers,
    update_user_status,
    delete_user,
    get_audit_logs,
    log_audit
)
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
