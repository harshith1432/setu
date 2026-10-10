from fastapi import APIRouter, Depends, Response
from typing import List, Dict, Any
from app.models.schemas import TelemetryPayload, ShedOverview
from app.services.telemetry_service import telemetry_service
from app.core.security import get_current_user_payload

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])

@router.post("/record", response_model=ShedOverview)
def ingest_telemetry(payload: TelemetryPayload):
    """
    Ingest live reading from ESP32 IoT node or simulation.
    Automatically evaluates safety rules, hysteresis, and updates actuator states.
    """
    return telemetry_service.record_reading(payload)

@router.get("/history/{shed_id}")
def get_telemetry_history(shed_id: str, payload: dict = Depends(get_current_user_payload)) -> List[Dict[str, Any]]:
    """
    Get historical timeseries for chart rendering.
    """
    history = [h for h in telemetry_service.history if h["shed_id"] == shed_id]
    return history[-20:]

@router.get("/export/csv/{shed_id}")
def export_csv(shed_id: str, payload: dict = Depends(get_current_user_payload)):
    """
    Download raw telemetry records as a formatted CSV file.
    """
    csv_data = telemetry_service.generate_csv_export(shed_id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=setu_{shed_id}_telemetry.csv"}
    )
