import asyncio
import json
from fastapi import APIRouter, Depends, Response, Header, HTTPException, WebSocket, WebSocketDisconnect, Query, status
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.models.schemas import TelemetryPayload, TelemetryBatchPayload, ShedOverview
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

@router.post("/batch")
def ingest_telemetry_batch(
    payload: TelemetryBatchPayload,
    auth_info: dict = Depends(verify_telemetry_auth)
):
    """
    High-throughput bulk ingestion for gateways, collectors, and high-frequency sensor networks.
    Ingests hundreds or thousands of readings in a single batched database transaction.
    """
    inserted = telemetry_service.record_batch_readings(payload.items)
    return {
        "status": "success",
        "ingested_count": inserted,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

from app.routers.sheds import verify_shed_access

@router.get("/history/{shed_id}")
def get_telemetry_history(
    shed_id: str,
    payload: dict = Depends(verify_shed_access)
) -> List[Dict[str, Any]]:
    """
    Get historical timeseries for chart rendering from PostgreSQL timeseries storage.
    Protected with Broken Object-Level Authorization (BOLA / IDOR) check.
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
    Protected with Broken Object-Level Authorization (BOLA / IDOR) check.
    """
    role = payload.get("role")
    if role not in ["admin", "superadmin"]:
        from app.services.db_service import get_user_by_username, get_user_by_id
        username = payload.get("sub") or payload.get("user_id")
        user = get_user_by_username(username) or get_user_by_id(username) if username else None
        user_shed = (user.get("shed_id") if user else "shed_01") or "shed_01"
        if user_shed.lower() != shed_id.lower() and user.get("id", "").lower() != shed_id.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: You do not have authorization to export data for shed '{shed_id}'"
            )

    csv_data = telemetry_service.generate_csv_export(shed_id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=setu_{shed_id}_telemetry.csv"}
    )

@router.get("/sse/{shed_id}")
async def sse_telemetry_stream(
    shed_id: str,
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None)
):
    """
    Server-Sent Events (SSE) streaming endpoint for mobile & web telemetry synchronization.
    Protected with token authentication and shed tenancy verification (SEC-06).
    """
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ")[1].strip()
    elif token:
        raw_token = token

    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token required for SSE stream")

    try:
        user_payload = decode_token(raw_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token for SSE stream")

    role = user_payload.get("role")
    if role not in ["admin", "superadmin"]:
        from app.services.db_service import get_user_by_username, get_user_by_id
        username = user_payload.get("sub") or user_payload.get("user_id")
        user = get_user_by_username(username) or get_user_by_id(username) if username else None
        user_shed = (user.get("shed_id") if user else "shed_01") or "shed_01"
        if user_shed.lower() != shed_id.lower() and user.get("id", "").lower() != shed_id.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Unauthorized shed stream access")

    async def event_generator():
        overview = telemetry_service.get_shed_overview(shed_id)
        data_dict = overview.model_dump() if hasattr(overview, "model_dump") else overview.dict()
        yield f"event: initial\ndata: {json.dumps(data_dict, default=str)}\n\n"
        
        while True:
            await asyncio.sleep(5)
            yield f"event: ping\ndata: {json.dumps({'time': datetime.now(timezone.utc).isoformat()})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.websocket("/ws/{shed_id}")
async def websocket_telemetry_stream(
    websocket: WebSocket,
    shed_id: str,
    token: Optional[str] = Query(None)
):
    """
    Real-time streaming WebSocket endpoint for live telemetry updates.
    Enforces authentication and tenant isolation during handshake (VULN-06).
    """
    raw_token = token
    if not raw_token:
        auth_h = websocket.headers.get("authorization")
        if auth_h and auth_h.startswith("Bearer "):
            raw_token = auth_h.split("Bearer ")[1].strip()

    if not raw_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication token required")
        return

    try:
        payload = decode_token(raw_token)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid credentials")
        return

    role = payload.get("role")
    if role not in ["admin", "superadmin"]:
        from app.services.db_service import get_user_by_username, get_user_by_id
        username = payload.get("sub") or payload.get("user_id")
        user = get_user_by_username(username) or get_user_by_id(username) if username else None
        user_shed = (user.get("shed_id") if user else "shed_01") or "shed_01"
        if user_shed.lower() != shed_id.lower() and user.get("id", "").lower() != shed_id.lower():
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Forbidden: Unauthorized shed stream")
            return

    await telemetry_service.ws_manager.connect(websocket, shed_id)
    try:
        overview = telemetry_service.get_shed_overview(shed_id)
        data_dict = overview.model_dump() if hasattr(overview, "model_dump") else overview.dict()
        await websocket.send_json({
            "type": "initial_state",
            "shed_id": shed_id,
            "data": data_dict
        })
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        telemetry_service.ws_manager.disconnect(websocket, shed_id)
    except Exception:
        telemetry_service.ws_manager.disconnect(websocket, shed_id)
