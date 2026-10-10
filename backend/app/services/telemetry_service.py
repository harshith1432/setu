from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import io
import csv
from app.models.schemas import TelemetryPayload, ActuatorStates, ShedOverview
from app.services.rules_engine import rules_engine, STAGE_THRESHOLDS
from app.services.weather_service import weather_service

class TelemetryService:
    def __init__(self):
        # In-memory storage for shed state & timeseries (ready for PostgreSQL)
        self.sheds: Dict[str, Dict[str, Any]] = {
            "shed_01": {
                "farm_name": "Green Valley Farm",
                "region": "Mulbagal, Karnataka",
                "current_stage": 3,
                "is_auto_mode": True,
                "temp_target": 26.0,
                "humidity_target": 75.0,
                "current_temp": 26.2,
                "current_hum": 74.0,
                "outside_temp": 34.2,
                "outside_hum": 58.0,
                "actuators": ActuatorStates(cooler=True, fan=False, heater=False),
                "last_updated": datetime.now(timezone.utc)
            }
        }
        
        # Historical buffer
        self.history: List[Dict[str, Any]] = []
        self._populate_sample_history("shed_01")

    def _populate_sample_history(self, shed_id: str):
        now = datetime.now(timezone.utc)
        for h in range(24, 0, -2):
            t = now - timedelta(hours=h)
            temp = 25.0 + (1.5 if 10 <= t.hour <= 16 else -1.0)
            hum = 75.0 - (4.0 if 10 <= t.hour <= 16 else -2.0)
            self.history.append({
                "shed_id": shed_id,
                "timestamp": t,
                "indoor_temp": round(temp, 1),
                "indoor_hum": round(hum, 1),
                "outside_temp": round(temp + 7.0, 1),
                "outside_hum": round(hum - 15.0, 1),
                "cooler": True if temp > 26.0 else False,
                "heater": False,
                "fan": True if temp > 26.5 else False
            })

    def record_reading(self, payload: TelemetryPayload) -> ShedOverview:
        shed = self.sheds.get(payload.shed_id)
        if not shed:
            shed = {
                "farm_name": f"Farm for {payload.shed_id}",
                "region": "Mulbagal, Karnataka",
                "current_stage": 3,
                "is_auto_mode": True,
                "temp_target": 26.0,
                "humidity_target": 75.0,
                "current_temp": payload.temperature,
                "current_hum": payload.humidity,
                "outside_temp": payload.outside_temperature or 34.0,
                "outside_hum": payload.outside_humidity or 55.0,
                "actuators": ActuatorStates(),
                "last_updated": datetime.now(timezone.utc)
            }
            self.sheds[payload.shed_id] = shed

        shed["current_temp"] = payload.temperature
        shed["current_hum"] = payload.humidity
        if payload.outside_temperature is not None:
            shed["outside_temp"] = payload.outside_temperature
        if payload.outside_humidity is not None:
            shed["outside_hum"] = payload.outside_humidity
        shed["last_updated"] = payload.timestamp or datetime.now(timezone.utc)

        # Run automation rules
        status, headline, subline, next_actuators = rules_engine.evaluate(
            current_temp=shed["current_temp"],
            current_hum=shed["current_hum"],
            outside_temp=shed["outside_temp"],
            stage=shed["current_stage"],
            is_auto_mode=shed["is_auto_mode"],
            current_actuators=shed["actuators"],
            manual_temp_target=shed["temp_target"],
            manual_hum_target=shed["humidity_target"]
        )

        shed["actuators"] = next_actuators

        # Record to history
        self.history.append({
            "shed_id": payload.shed_id,
            "timestamp": shed["last_updated"],
            "indoor_temp": shed["current_temp"],
            "indoor_hum": shed["current_hum"],
            "outside_temp": shed["outside_temp"],
            "outside_hum": shed["outside_hum"],
            "cooler": next_actuators.cooler,
            "heater": next_actuators.heater,
            "fan": next_actuators.fan
        })

        return self.get_shed_overview(payload.shed_id)

    def get_shed_overview(self, shed_id: str) -> ShedOverview:
        shed = self.sheds.get(shed_id)
        if not shed:
            shed = self.sheds["shed_01"]

        status, headline, subline, _ = rules_engine.evaluate(
            current_temp=shed["current_temp"],
            current_hum=shed["current_hum"],
            outside_temp=shed["outside_temp"],
            stage=shed["current_stage"],
            is_auto_mode=shed["is_auto_mode"],
            current_actuators=shed["actuators"],
            manual_temp_target=shed["temp_target"],
            manual_hum_target=shed["humidity_target"]
        )

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
            outside_temp=shed["outside_temp"],
            outside_humidity=shed["outside_hum"],
            actuators=shed["actuators"],
            is_auto_mode=shed["is_auto_mode"],
            temp_target=shed["temp_target"],
            humidity_target=shed["humidity_target"],
            last_updated=shed["last_updated"]
        )

    def update_setpoints(self, shed_id: str, is_auto: bool, temp_target: float, hum_target: float) -> ShedOverview:
        shed = self.sheds.get(shed_id, self.sheds["shed_01"])
        shed["is_auto_mode"] = is_auto
        shed["temp_target"] = temp_target
        shed["humidity_target"] = hum_target
        return self.get_shed_overview(shed_id)

    def manual_override_actuator(self, shed_id: str, actuator: str, state: bool) -> ShedOverview:
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
            
        return self.get_shed_overview(shed_id)

    def set_growth_stage(self, shed_id: str, stage: int) -> ShedOverview:
        shed = self.sheds.get(shed_id, self.sheds["shed_01"])
        if 1 <= stage <= 5:
            shed["current_stage"] = stage
        return self.get_shed_overview(shed_id)

    def generate_csv_export(self, shed_id: str) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Timestamp_UTC", "Shed_ID", "Indoor_Temp_C", "Indoor_Humidity_pct",
            "Outside_Temp_C", "Outside_Humidity_pct", "Cooler_Active", "Heater_Active", "Fan_Active"
        ])
        
        records = [r for r in self.history if r["shed_id"] == shed_id]
        if not records:
            records = self.history

        for r in records:
            writer.writerow([
                r["timestamp"].isoformat(),
                r["shed_id"],
                r["indoor_temp"],
                r["indoor_hum"],
                r["outside_temp"],
                r["outside_hum"],
                "YES" if r["cooler"] else "NO",
                "YES" if r["heater"] else "NO",
                "YES" if r["fan"] else "NO"
            ])
            
        return output.getvalue()

telemetry_service = TelemetryService()
