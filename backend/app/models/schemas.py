from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# --- Auth & User Schemas ---
class UserRole(str, Enum):
    FARMER = "farmer"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"

class UserLogin(BaseModel):
    username: str
    password: str

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

class UserBase(BaseModel):
    username: str
    full_name: str
    phone: str
    preferred_language: str = "kn"
    role: UserRole = UserRole.FARMER
    farm_name: str = "Green Valley Farm"
    region: str = "Local Rearing Shed"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    batch_id: str = "SERI-2026-M04"
    dfl_capacity: str = "200 DFL"
    breed: str = "Double Hybrid (FC1 x FC2)"
    shed_id: Optional[str] = "shed_01"
    whatsapp_number: Optional[str] = None
    whatsapp_verified: bool = False
    current_stage: Optional[int] = 3

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    preferred_language: Optional[str] = None
    farm_name: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    batch_id: Optional[str] = None
    dfl_capacity: Optional[str] = None
    breed: Optional[str] = None
    shed_id: Optional[str] = None
    whatsapp_number: Optional[str] = None
    whatsapp_verified: Optional[bool] = None
    current_stage: Optional[int] = None

UserProfileUpdate = UserUpdate

class UserOut(BaseModel):
    id: str
    username: str
    full_name: str
    phone: str
    whatsapp_number: Optional[str] = None
    whatsapp_verified: bool = False
    preferred_language: str = "kn"
    role: str = "farmer"
    farm_name: Optional[str] = "Green Valley Sericulture Farm"
    region: Optional[str] = "Local Rearing Shed"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    shed_id: Optional[str] = "shed_01"
    batch_id: Optional[str] = "SERI-2026-M04"
    dfl_capacity: Optional[str] = "200 DFL"
    breed: Optional[str] = "Double Hybrid (FC1 x FC2)"
    is_active: Optional[bool] = True
    created_at: Optional[datetime] = None
    current_stage: Optional[int] = 3

    class Config:
        from_attributes = True

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

    # Distributed IoT Enterprise Extensions
    event_id: Optional[str] = None
    sequence_number: Optional[int] = None
    device_id: Optional[str] = None
    organization_id: Optional[str] = "default_org"
    measured_at: Optional[datetime] = None
    firmware_version: Optional[str] = "1.0.0"
    schema_version: Optional[str] = "1.0"
    quality_status: Optional[str] = "GOOD"

class TelemetryBatchPayload(BaseModel):
    items: List[TelemetryPayload]

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

# --- Command Lifecycle Schemas ---
class CommandStatus(str, Enum):
    REQUESTED = "REQUESTED"
    AUTHORIZED = "AUTHORIZED"
    QUEUED = "QUEUED"
    SENT = "SENT"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"

class DeviceCommandCreate(BaseModel):
    device_id: str
    command_type: str  # "SET_ACTUATOR", "SET_SETPOINTS", "REBOOT", "CALIBRATE"
    command_payload: Dict[str, Any]
    expires_in_seconds: int = 300
    correlation_id: Optional[str] = None

class DeviceCommandAck(BaseModel):
    command_id: str
    device_id: str
    status: CommandStatus  # ACKNOWLEDGED, APPLIED, REJECTED, FAILED
    error_message: Optional[str] = None
    applied_state: Optional[Dict[str, Any]] = None

class DeviceCommandOut(BaseModel):
    command_id: str
    organization_id: str
    device_id: str
    shed_id: str
    requested_by: str
    command_type: str
    command_payload: Dict[str, Any]
    status: CommandStatus
    created_at: datetime
    expires_at: datetime
    correlation_id: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    error_message: Optional[str] = None

# --- Device Registry Schemas ---
class DeviceRegistration(BaseModel):
    device_id: str
    shed_id: str
    organization_id: Optional[str] = "default_org"
    device_name: Optional[str] = None
    firmware_version: Optional[str] = "1.0.0"
    device_key: Optional[str] = None

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
