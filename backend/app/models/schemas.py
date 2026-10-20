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
    whatsapp_number: Optional[str] = None
    whatsapp_verified: bool = False
    preferred_language: str = "kn"  # "en", "kn", "te"
    farm_name: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    shed_id: Optional[str] = None
    batch_id: Optional[str] = None
    dfl_capacity: Optional[str] = None
    breed: Optional[str] = "Double Hybrid (FC1 x FC2)"

class GoogleAuthRequest(BaseModel):
    email: Optional[str] = None
    google_id: Optional[str] = None
    full_name: str
    phone: Optional[str] = None
    farm_name: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    shed_id: Optional[str] = None
    batch_id: Optional[str] = None
    dfl_capacity: Optional[str] = None
    breed: Optional[str] = "Double Hybrid (FC1 x FC2)"
    preferred_language: Optional[str] = "en"

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    whatsapp_verified: Optional[bool] = None
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
    whatsapp_number: Optional[str] = None
    whatsapp_verified: bool = False
    preferred_language: str
    role: str
    farm_name: Optional[str] = "Green Valley Sericulture Farm"
    region: Optional[str] = "Local Rearing Shed"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    shed_id: Optional[str] = "shed_01"
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
    light: bool = False
    light_brightness: int = 0  # 0 to 100% PWM dimming

class TelemetryPayload(BaseModel):
    shed_id: str
    temperature: float = Field(..., ge=0.0, le=60.0)
    humidity: float = Field(..., ge=0.0, le=100.0)
    air_quality: Optional[float] = Field(88.0, ge=0.0, le=100.0)  # 0-100% index (safe > 80%, CO2 < 1%)
    light_lux: Optional[float] = Field(22.0, ge=0.0, le=500.0)    # Research target 15-30 Lux
    outside_temperature: Optional[float] = 34.0
    outside_humidity: Optional[float] = 55.0
    timestamp: Optional[datetime] = None

class SetpointsUpdate(BaseModel):
    is_auto_mode: bool = True
    temp_target: float = Field(26.0, ge=18.0, le=35.0)
    humidity_target: float = Field(75.0, ge=40.0, le=95.0)
    air_quality_target: Optional[float] = Field(80.0, ge=50.0, le=100.0)
    light_lux_target: Optional[float] = Field(25.0, ge=5.0, le=100.0)
    light_brightness: Optional[int] = Field(None, ge=0, le=100)

class ManualActuatorOverride(BaseModel):
    actuator: str  # "cooler", "fan", "heater", "light", "light_brightness"
    state: bool = False
    value: Optional[int] = None  # for light_brightness PWM 0-100

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
    indoor_air_quality: float = 88.0
    indoor_light_lux: float = 22.0
    outside_temp: float
    outside_humidity: float
    actuators: ActuatorStates
    is_auto_mode: bool
    temp_target: float
    humidity_target: float
    air_quality_target: float = 80.0
    light_lux_target: float = 25.0
    photoperiod_mode: str = "DAY"  # "DAY", "NIGHT", "SPINNING"
    last_updated: datetime

