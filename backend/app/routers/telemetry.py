from fastapi import APIRouter, Depends, Response, Header, HTTPException, WebSocket, WebSocketDisconnect, Query
from typing import List, Dict, Any, Optional
from app.models.schemas import TelemetryPayload, ShedOverview
from app.services.telemetry_service import telemetry_service
from app.core.security import get_current_user_payload, decode_token
from app.core.config import settings

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])

def verify_telemetry_auth(
    x_device_key: Optional[str] = Header(None, alias="X-Device-Key"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None)
):
    """
    SEC-05: Authenticates IoT hardware nodes or authenticated users.
    Accepts:
    1. Pre-shared hardware device key via X-Device-Key or X-API-Key header.
    2. Bearer JWT authorization token from authenticated operators/mobile users.
    Rejects unauthenticated requests with HTTP 401 Unauthorized.
    """
    # Check pre-shared device API key
    if x_device_key and x_device_key == settings.DEVICE_API_KEY:
        return {"auth_type": "device", "identity": "iot_node"}
    if x_api_key and x_api_key == settings.DEVICE_API_KEY:
        return {"auth_type": "device", "identity": "iot_node"}

    # Check user Bearer token
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            from app.core.security import decode_token
            payload = decode_token(token)
            if payload and "sub" in payload:
                return {"auth_type": "user", "identity": payload.get("sub")}
        except Exception:
            pass

    raise HTTPException(
        status_code=401,
        detail="Unauthorized: Valid X-Device-Key or user Bearer token required for telemetry ingestion"
    )

@router.post("/record", response_model=ShedOverview)
def ingest_telemetry(
    payload: TelemetryPayload,
    auth_info: dict = Depends(verify_telemetry_auth)
):
    """
    Ingest live reading from ESP32 IoT node or authenticated simulation.
    Protected with device or user authentication (SEC-05).
    Automatically evaluates safety rules, hysteresis, updates actuator states, and persists to DB.
    """
    return telemetry_service.record_reading(payload)

@router.get("/history/{shed_id}")
def get_telemetry_history(
    shed_id: str,
    payload: dict = Depends(get_current_user_payload)
) -> List[Dict[str, Any]]:
    """
    Get historical timeseries for chart rendering from PostgreSQL timeseries storage.
    """
    return telemetry_service.get_history(shed_id, limit=50)

def get_user_from_header_or_query(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
) -> dict:
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ")[1].strip()
    elif token:
        raw_token = token
    if not raw_token:
        raise HTTPException(status_code=401, detail="Authentication token required")
    return decode_token(raw_token)

@router.get("/export/csv/{shed_id}")
def export_csv(
    shed_id: str,
    payload: dict = Depends(get_user_from_header_or_query)
):
    """
    Download raw telemetry records as a formatted CSV file.
    Accepts Bearer token in header or token in query param.
    """
    csv_data = telemetry_service.generate_csv_export(shed_id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=setu_{shed_id}_telemetry.csv"}
    )

@router.websocket("/ws/{shed_id}")
async def websocket_telemetry_stream(websocket: WebSocket, shed_id: str):
    """
    Real-time streaming WebSocket endpoint for live telemetry updates without HTTP polling.
    """
    await telemetry_service.ws_manager.connect(websocket)
    try:
        overview = telemetry_service.get_shed_overview(shed_id)
        data_dict = overview.model_dump() if hasattr(overview, "model_dump") else overview.dict()
        await websocket.send_json({
            "type": "initial_state",
            "shed_id": shed_id,
            "data": data_dict
        })
        while True:
            # Keep socket open and receive any client ping messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        telemetry_service.ws_manager.disconnect(websocket)
    except Exception:
        telemetry_service.ws_manager.disconnect(websocket)
