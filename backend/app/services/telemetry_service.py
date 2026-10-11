from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from collections import deque
import io
import csv
import asyncio
from fastapi import WebSocket
from app.models.schemas import TelemetryPayload, ActuatorStates, ShedOverview
from app.services.rules_engine import rules_engine, STAGE_THRESHOLDS
from app.services.weather_service import weather_service
from app.services.db_service import save_telemetry_reading, get_telemetry_history_from_db

class ConnectionManager:
    """
    Manages active WebSocket connections for real-time telemetry streaming.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

    def broadcast_sync(self, message: dict):
        """
        Non-blocking schedule of broadcast if event loop is running.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.broadcast(message))
        except Exception:
            pass

class TelemetryService:
    def __init__(self):
        # In-memory live state for active sheds
        self.sheds: Dict[str, Dict[str, Any]] = {
            "shed_01": {
                "farm_name": "Green Valley Farm",
                "region": "Sericulture Shed",
                "current_stage": 3,
                "is_auto_mode": True,
                "temp_target": 26.0,
                "humidity_target": 75.0,
                "air_quality_target": 80.0,
                "light_lux_target": 25.0,
                "current_temp": 26.2,
                "current_hum": 74.0,
                "current_air_quality": 88.0,
                "current_light_lux": 22.0,
                "photoperiod_mode": "DAY",
                "outside_temp": 34.2,
                "outside_hum": 58.0,
                "actuators": ActuatorStates(cooler=True, fan=False, heater=False, light=True, light_brightness=35),
                "last_updated": datetime.now(timezone.utc)
            }
        }
        
        # Bounded historical ring buffer (Max 1000 items in RAM to prevent OOM)
        self.history: deque = deque(maxlen=1000)
        self.ws_manager = ConnectionManager()
        self._populate_sample_history("shed_01")

    def _populate_sample_history(self, shed_id: str):
        now = datetime.now(timezone.utc)
        for h in range(24, 0, -2):
            t = now - timedelta(hours=h)
            temp = 25.0 + (1.5 if 10 <= t.hour <= 16 else -1.0)
            hum = 75.0 - (4.0 if 10 <= t.hour <= 16 else -2.0)
            aqi = 88.0 - (5.0 if 12 <= t.hour <= 18 else 0.0)
            lux = 24.0 if 6 <= t.hour <= 22 else 2.0
            record = {
                "shed_id": shed_id,
                "timestamp": t,
                "indoor_temp": round(temp, 1),
                "indoor_hum": round(hum, 1),
                "air_quality": round(aqi, 1),
                "light_lux": round(lux, 1),
                "outside_temp": round(temp + 7.0, 1),
                "outside_hum": round(hum - 15.0, 1),
                "cooler": True if temp > 26.0 else False,
                "heater": False,
                "fan": True if temp > 26.5 or aqi < 80.0 else False,
                "light": True if 6 <= t.hour <= 22 else False,
                "light_brightness": 35 if 6 <= t.hour <= 22 else 0,
                "mode": "AUTO"
            }
            self.history.append(record)

    def record_reading(self, payload: TelemetryPayload) -> ShedOverview:
        shed = self.sheds.get(payload.shed_id)
        if not shed:
            shed = {
                "farm_name": f"Farm for {payload.shed_id}",
                "region": "Sericulture Shed",
                "current_stage": 3,
                "is_auto_mode": True,
                "temp_target": 26.0,
                "humidity_target": 75.0,
                "air_quality_target": 80.0,
                "light_lux_target": 25.0,
                "current_temp": payload.temperature,
                "current_hum": payload.humidity,
                "current_air_quality": payload.air_quality if payload.air_quality is not None else 88.0,
                "current_light_lux": payload.light_lux if payload.light_lux is not None else 22.0,
                "photoperiod_mode": "DAY",
                "outside_temp": payload.outside_temperature or 34.0,
                "outside_hum": payload.outside_humidity or 55.0,
                "actuators": ActuatorStates(),
                "last_updated": datetime.now(timezone.utc)
            }
            self.sheds[payload.shed_id] = shed

        shed["current_temp"] = payload.temperature
        shed["current_hum"] = payload.humidity
        if payload.air_quality is not None:
            shed["current_air_quality"] = payload.air_quality
        if payload.light_lux is not None:
            shed["current_light_lux"] = payload.light_lux
        if payload.outside_temperature is not None:
            shed["outside_temp"] = payload.outside_temperature
        if payload.outside_humidity is not None:
            shed["outside_hum"] = payload.outside_humidity
        shed["last_updated"] = payload.timestamp or datetime.now(timezone.utc)

        # Run automation rules
        status, headline, subline, next_actuators, photo_mode = rules_engine.evaluate(
            current_temp=shed["current_temp"],
            current_hum=shed["current_hum"],
            outside_temp=shed["outside_temp"],
            stage=shed["current_stage"],
            is_auto_mode=shed["is_auto_mode"],
            current_actuators=shed["actuators"],
            manual_temp_target=shed["temp_target"],
            manual_hum_target=shed["humidity_target"],
            current_air_quality=shed["current_air_quality"],
            current_light_lux=shed["current_light_lux"],
            air_quality_target=shed["air_quality_target"],
            light_lux_target=shed["light_lux_target"]
        )

        shed["actuators"] = next_actuators
        shed["photoperiod_mode"] = photo_mode

        # Record to memory buffer
        record = {
            "shed_id": payload.shed_id,
            "timestamp": shed["last_updated"],
            "indoor_temp": shed["current_temp"],
            "indoor_hum": shed["current_hum"],
            "air_quality": shed["current_air_quality"],
            "light_lux": shed["current_light_lux"],
            "outside_temp": shed["outside_temp"],
            "outside_hum": shed["outside_hum"],
            "cooler": next_actuators.cooler,
            "heater": next_actuators.heater,
            "fan": next_actuators.fan,
            "light": next_actuators.light,
            "light_brightness": next_actuators.light_brightness,
            "mode": "AUTO" if shed["is_auto_mode"] else "MANUAL"
        }
        self.history.append(record)

        # Persist to PostgreSQL timeseries table
        save_telemetry_reading(record)

        overview = self.get_shed_overview(payload.shed_id)

        # Broadcast real-time update to WebSocket clients
        try:
            self.ws_manager.broadcast_sync({
                "type": "telemetry_update",
                "shed_id": payload.shed_id,
                "data": overview.model_dump() if hasattr(overview, "model_dump") else overview.dict()
            })
        except Exception:
            pass

        return overview

    def get_shed_overview(
        self,
        shed_id: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        region_override: Optional[str] = None
    ) -> ShedOverview:
        shed = self.sheds.get(shed_id)
        if not shed:
            shed = self.sheds["shed_01"]

        # Fetch real-time weather dynamically from Open-Meteo
        lookup_region = region_override
        if not lookup_region and (lat is None or lon is None):
            lookup_region = shed.get("region")

        try:
            live_weather = weather_service.get_current_weather(
                lat=lat,
                lon=lon,
                region=lookup_region
            )
            shed["outside_temp"] = live_weather["outside_temperature"]
            shed["outside_hum"] = live_weather["outside_humidity"]
            if region_override:
                shed["region"] = region_override
            elif live_weather.get("region"):
                shed["region"] = live_weather["region"]
        except Exception:
            pass

        status, headline, subline, next_act, photo_mode = rules_engine.evaluate(
            current_temp=shed["current_temp"],
            current_hum=shed["current_hum"],
            outside_temp=shed["outside_temp"],
            stage=shed["current_stage"],
            is_auto_mode=shed["is_auto_mode"],
            current_actuators=shed["actuators"],
            manual_temp_target=shed["temp_target"],
            manual_hum_target=shed["humidity_target"],
            current_air_quality=shed.get("current_air_quality", 88.0),
            current_light_lux=shed.get("current_light_lux", 22.0),
            air_quality_target=shed.get("air_quality_target", 80.0),
            light_lux_target=shed.get("light_lux_target", 25.0)
        )

        if shed["is_auto_mode"]:
            shed["actuators"] = next_act
        shed["photoperiod_mode"] = photo_mode

        stage_meta = STAGE_THRESHOLDS.get(shed["current_stage"], STAGE_THRESHOLDS[3])

        return ShedOverview(
            shed_id=shed_id,
            farm_name=shed["farm_name"],
            region=shed["region"],
            overall_status=status,
            status_headline=headline,
            status_subline=subline,
            current_stage=shed["current_stage"],
            stage_name=stage_meta["name"],
            indoor_temp=shed["current_temp"],
            indoor_humidity=shed["current_hum"],
            indoor_air_quality=shed.get("current_air_quality", 88.0),
            indoor_light_lux=shed.get("current_light_lux", 22.0),
            outside_temp=shed["outside_temp"],
            outside_humidity=shed["outside_hum"],
            actuators=shed["actuators"],
            is_auto_mode=shed["is_auto_mode"],
            temp_target=shed["temp_target"],
            humidity_target=shed["humidity_target"],
            air_quality_target=shed.get("air_quality_target", 80.0),
            light_lux_target=shed.get("light_lux_target", 25.0),
            photoperiod_mode=shed.get("photoperiod_mode", "DAY"),
            last_updated=shed["last_updated"]
        )

    def update_setpoints(
        self,
        shed_id: str,
        is_auto: bool,
        temp_target: float,
        hum_target: float,
        air_quality_target: Optional[float] = None,
        light_lux_target: Optional[float] = None,
        light_brightness: Optional[int] = None
    ) -> ShedOverview:
        shed = self.sheds.get(shed_id, self.sheds["shed_01"])
        shed["is_auto_mode"] = is_auto
        shed["temp_target"] = temp_target
        shed["humidity_target"] = hum_target
        if air_quality_target is not None:
            shed["air_quality_target"] = air_quality_target
        if light_lux_target is not None:
            shed["light_lux_target"] = light_lux_target
        if light_brightness is not None:
            shed["actuators"].light_brightness = light_brightness
            shed["actuators"].light = light_brightness > 0
        return self.get_shed_overview(shed_id)

    def manual_override_actuator(
        self,
        shed_id: str,
        actuator: str,
        state: bool,
        value: Optional[int] = None
    ) -> ShedOverview:
        shed = self.sheds.get(shed_id, self.sheds["shed_01"])
        shed["is_auto_mode"] = False
        
        # Enforce safety interlock
        if actuator == "cooler":
            shed["actuators"].cooler = state
            if state:
                shed["actuators"].heater = False
        elif actuator == "heater":
            shed["actuators"].heater = state
            if state:
                shed["actuators"].cooler = False
        elif actuator == "fan":
            shed["actuators"].fan = state
        elif actuator == "light":
            shed["actuators"].light = state
            if not state:
                shed["actuators"].light_brightness = 0
            elif shed["actuators"].light_brightness == 0:
                shed["actuators"].light_brightness = 35
        elif actuator == "light_brightness":
            val = max(0, min(100, value if value is not None else (35 if state else 0)))
            shed["actuators"].light_brightness = val
            shed["actuators"].light = val > 0
            
        return self.get_shed_overview(shed_id)

    def set_growth_stage(self, shed_id: str, stage: int) -> ShedOverview:
        shed = self.sheds.get(shed_id, self.sheds["shed_01"])
        if 1 <= stage <= 5:
            shed["current_stage"] = stage
        return self.get_shed_overview(shed_id)

    def get_history(self, shed_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        # Query from database first
        db_history = get_telemetry_history_from_db(shed_id, limit=limit)
        if db_history:
            return db_history
        # Fall back to bounded in-memory buffer
        mem = [r for r in self.history if r["shed_id"] == shed_id]
        return list(mem)[-limit:]

    def generate_csv_export(self, shed_id: str) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Timestamp_UTC", "Shed_ID", "Indoor_Temp_C", "Indoor_Humidity_pct",
            "Indoor_Air_Quality_pct", "Indoor_Light_Lux", "Outside_Temp_C", "Outside_Humidity_pct",
            "Cooler_Active", "Heater_Active", "Fan_Active", "Light_Active", "Light_Brightness_pct"
        ])
        
        records = self.get_history(shed_id, limit=200)

        for r in records:
            ts = r["timestamp"]
            ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
            writer.writerow([
                ts_str,
                r.get("shed_id", shed_id),
                r.get("indoor_temp"),
                r.get("indoor_hum"),
                r.get("air_quality", 88.0),
                r.get("light_lux", 22.0),
                r.get("outside_temp"),
                r.get("outside_hum"),
                "YES" if r.get("cooler") else "NO",
                "YES" if r.get("heater") else "NO",
                "YES" if r.get("fan") else "NO",
                "YES" if r.get("light") else "NO",
                r.get("light_brightness", 0)
            ])
            
        return output.getvalue()


telemetry_service = TelemetryService()
