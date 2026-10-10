from fastapi import APIRouter, Depends, Query
from app.models.schemas import AIExplanation
from app.services.telemetry_service import telemetry_service
from app.services.ai_explainer import ai_explainer
from app.core.security import get_current_user_payload

router = APIRouter(prefix="/ai", tags=["Explainable AI"])

@router.get("/explain/{shed_id}", response_model=AIExplanation)
def get_ai_explanation(
    shed_id: str,
    lang: str = Query("en", pattern="^(en|kn|te)$"),
    payload: dict = Depends(get_current_user_payload)
):
    """
    Get explainable AI rationale for why cooling/heating is running, target limits, and farmer tips.
    Supports English, Kannada, and Telugu.
    """
    shed = telemetry_service.get_shed_overview(shed_id)
    return ai_explainer.generate_explanation(
        overall_status=shed.overall_status,
        actuators=shed.actuators,
        indoor_temp=shed.indoor_temp,
        indoor_hum=shed.indoor_humidity,
        out_temp=shed.outside_temp,
        stage=shed.current_stage,
        lang=lang
    )
