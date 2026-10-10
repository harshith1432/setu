from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# --- Auth Schemas ---
class UserLogin(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    phone: str
    preferred_language: str = "kn"  # "en", "kn", "te"
    farm_name: Optional[str] = "Green Valley Sericulture Farm"
    region: Optional[str] = "Mulbagal, Kolar, KA"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    batch_id: Optional[str] = "SERI-2026-M04"
    dfl_capacity: Optional[str] = "200 DFL"
    breed: Optional[str] = "Double Hybrid (FC1 x FC2)"

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    farm_name: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    batch_id: Optional[str] = None
    dfl_capacity: Optional[str] = None
    breed: Optional[str] = None
    preferred_language: Optional[str] = None

class UserOut(BaseModel):
    id: str
    username: str
    full_name: str
    phone: str
    preferred_language: str
    role: str
    farm_name: Optional[str] = "Green Valley Sericulture Farm"
    region: Optional[str] = "Mulbagal, Kolar, KA"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    batch_id: Optional[str] = "SERI-2026-M04"
    dfl_capacity: Optional[str] = "200 DFL"
    breed: Optional[str] = "Double Hybrid (FC1 x FC2)"
    is_active: Optional[bool] = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# --- Environmental & Control Schemas ---
class ActuatorStates(BaseModel):
    cooler: bool = False
    fan: bool = False
    heater: bool = False

class TelemetryPayload(BaseModel):
    shed_id: str
    temperature: float = Field(..., ge=0.0, le=60.0)
    humidity: float = Field(..., ge=0.0, le=100.0)
    outside_temperature: Optional[float] = 34.0
    outside_humidity: Optional[float] = 55.0
    timestamp: Optional[datetime] = None

class SetpointsUpdate(BaseModel):
    is_auto_mode: bool = True
    temp_target: float = Field(26.0, ge=18.0, le=35.0)
    humidity_target: float = Field(75.0, ge=40.0, le=95.0)

class ManualActuatorOverride(BaseModel):
    actuator: str  # "cooler", "fan", "heater"
    state: bool

class GrowthStageInfo(BaseModel):
    stage_number: int  # 1 to 5
    name: str
    days_range: str
    temp_min: float
    temp_max: float
    hum_min: float
    hum_max: float
    recommendation: str

class AIExplanation(BaseModel):
    why_text: str
    current_action: str
    target_description: str
    bullet_points: List[str]
    language: str

class ShedOverview(BaseModel):
    shed_id: str
    farm_name: str
    region: str
    overall_status: str  # "IDEAL", "TOO_WARM", "TOO_COOL", "CRITICAL"
    status_headline: str
    status_subline: str
    current_stage: int
    stage_name: str
    indoor_temp: float
    indoor_humidity: float
    outside_temp: float
    outside_humidity: float
    actuators: ActuatorStates
    is_auto_mode: bool
    temp_target: float
    humidity_target: float
    last_updated: datetime
