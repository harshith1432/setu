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
import logging
from app.core.config import settings
from app.services.db_service import save_telemetry_reading, get_telemetry_history_from_db, get_latest_telemetry_reading_from_db, get_farmers_by_shed_id
from app.services.whatsapp_alerts import alert_service
from app.services.voice_service import voice_service

logger = logging.getLogger(__name__)

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
        # In-memory session cache for active control overrides (setpoints, manual actuators)
        self.sheds: Dict[str, Dict[str, Any]] = {}
        # Bounded historical ring buffer (Max 1000 items in RAM to prevent OOM)
        self.history: deque = deque(maxlen=1000)
        self.ws_manager = ConnectionManager()

    def _get_or_create_shed(self, shed_id: str) -> Dict[str, Any]:
        if shed_id not in self.sheds:
            self.sheds[shed_id] = {
                "current_stage": 3,
                "is_auto_mode": True,
                "temp_target": 26.0,
                "humidity_target": 75.0,
                "air_quality_target": 80.0,
                "light_lux_target": 25.0,
                "actuators": ActuatorStates(),
            }
        return self.sheds[shed_id]

    def record_reading(self, payload: TelemetryPayload) -> ShedOverview:
        session = self._get_or_create_shed(payload.shed_id)
        current_stage = session.get("current_stage", 3)
        is_auto_mode = session.get("is_auto_mode", True)
        temp_target = session.get("temp_target", 26.0)
        hum_target = session.get("humidity_target", 75.0)
        air_quality_target = session.get("air_quality_target", 80.0)
        light_lux_target = session.get("light_lux_target", 25.0)
        current_act = session.get("actuators", ActuatorStates())

        # Evaluate rules engine
        status, headline, subline, next_actuators, photo_mode = rules_engine.evaluate(
            current_temp=payload.temperature,
            current_hum=payload.humidity,
            outside_temp=payload.outside_temperature or 30.0,
            stage=current_stage,
            is_auto_mode=is_auto_mode,
            current_actuators=current_act,
            manual_temp_target=temp_target,
            manual_hum_target=hum_target,
            current_air_quality=payload.air_quality or 88.0,
            current_light_lux=payload.light_lux or 22.0,
            air_quality_target=air_quality_target,
            light_lux_target=light_lux_target
        )

        reading_record = {
            "shed_id": payload.shed_id,
            "timestamp": payload.timestamp or datetime.now(timezone.utc),
            "indoor_temp": payload.temperature,
            "indoor_hum": payload.humidity,
            "air_quality": payload.air_quality if payload.air_quality is not None else 88.0,
            "light_lux": payload.light_lux if payload.light_lux is not None else 22.0,
            "outside_temp": payload.outside_temperature,
            "outside_hum": payload.outside_humidity,
            "cooler": next_actuators.cooler if is_auto_mode else current_act.cooler,
            "heater": next_actuators.heater if is_auto_mode else current_act.heater,
            "fan": next_actuators.fan if is_auto_mode else current_act.fan,
            "light": next_actuators.light if is_auto_mode else current_act.light,
            "light_brightness": next_actuators.light_brightness if is_auto_mode else current_act.light_brightness,
            "mode": "AUTO" if is_auto_mode else "MANUAL"
        }

        # Persist reading to database
        self.history.append(reading_record)
        save_telemetry_reading(reading_record)

        session["actuators"] = next_actuators if is_auto_mode else current_act
        session["photoperiod_mode"] = photo_mode

        # Check for temperature variation or microclimate anomaly
        thresholds = STAGE_THRESHOLDS.get(session.get("current_stage", 3), STAGE_THRESHOLDS[3])
        target_temp_max = thresholds.get("temp_max", 27.0)
        target_temp_min = thresholds.get("temp_min", 25.0)
        temp_target = session.get("temp_target", 26.0)
        temp_deviation = abs(payload.temperature - temp_target)

        is_temp_varying = (
            status in ["TOO_WARM", "TOO_COOL", "CRITICAL", "WARNING", "ALERT"]
            or payload.temperature > target_temp_max
            or payload.temperature < target_temp_min
            or payload.temperature >= 32.0
            or payload.temperature <= 18.0
            or temp_deviation >= 2.0
        )

        if is_temp_varying:
            try:
                farmers = get_farmers_by_shed_id(payload.shed_id)
                cooldown_sec = getattr(settings, "WHATSAPP_ALERT_COOLDOWN_SECONDS", 300)
                is_cooler_on = getattr(next_actuators, "cooler", False)
                is_heater_on = getattr(next_actuators, "heater", False)
                is_fan_on = getattr(next_actuators, "fan", False)

                for farmer in farmers:
                    recipient = farmer.get("whatsapp_number") or farmer.get("phone")
                    if not recipient or recipient == "N/A":
                        continue
                    farmer_name = farmer.get("full_name") or farmer.get("username", "Farmer")
                    farm_name = farmer.get("farm_name") or session.get("farm_name", f"Shed {payload.shed_id.upper()}")
                    farmer_lang = farmer.get("preferred_language", "en")

                    var_msg = alert_service.build_temperature_variation_alert(
                        farmer_name=farmer_name,
                        farm_name=farm_name,
                        shed_id=payload.shed_id,
                        current_temp=payload.temperature,
                        temp_target=temp_target,
                        temp_min=target_temp_min,
                        temp_max=target_temp_max,
                        current_hum=payload.humidity,
                        status=status,
                        headline=headline,
                        subline=subline,
                        cooler_active=is_cooler_on,
                        heater_active=is_heater_on,
                        fan_active=is_fan_on,
                        lang=farmer_lang,
                    )

                    voice_script = voice_service.build_voice_script(
                        farmer_name=farmer_name,
                        shed_id=payload.shed_id,
                        current_temp=payload.temperature,
                        temp_target=temp_target,
                        is_cooler_on=is_cooler_on,
                        is_heater_on=is_heater_on,
                        is_fan_on=is_fan_on,
                        lang=farmer_lang,
                    )
                    voice_url = voice_service.get_voice_url_for_text(voice_script, lang=farmer_lang)

                    alert_service.dispatch_in_background(
                        message=var_msg,
                        recipient=recipient,
                        voice_url=voice_url,
                        cooldown_key=f"temp_var:{payload.shed_id}:{farmer.get('id')}",
                        cooldown_seconds=cooldown_sec,
                    )
            except Exception as e:
                logger.error("Error dispatching temperature variation alerts: %s", e)

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
        # 1. Resolve farmer details dynamically from PostgreSQL database
        farm_name = None
        user_region = region_override
        farmer_lat = lat
        farmer_lon = lon
        user_stage = None

        try:
            from app.services.db_service import get_db_cursor
            with get_db_cursor(dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT id, username, full_name, farm_name, region, latitude, longitude, shed_id 
                    FROM users 
                    WHERE shed_id = %s OR id = %s OR username = %s OR ('shed_' || id) = %s
                    ORDER BY (role = 'farmer') DESC 
                    LIMIT 1
                """, (shed_id, shed_id, shed_id, shed_id))
                user = cursor.fetchone()
                if user:
                    if user.get("farm_name"):
                        farm_name = user["farm_name"]
                    if user.get("region") and not user_region:
                        user_region = user["region"]
                    if farmer_lat is None and user.get("latitude") is not None:
                        farmer_lat = float(user["latitude"])
                    if farmer_lon is None and user.get("longitude") is not None:
                        farmer_lon = float(user["longitude"])

                    # Save detected GPS coordinates from phone into DB profile if provided
                    if lat is not None and lon is not None:
                        cursor.execute("""
                            UPDATE users 
                            SET latitude = %s, longitude = %s, region = COALESCE(%s, region)
                            WHERE id = %s
                        """, (lat, lon, region_override, user["id"]))
        except Exception:
            pass

        if not farm_name:
            farm_name = f"Shed {shed_id.upper()}"
        if not user_region:
            user_region = "Sericulture Shed"

        # 2. Fetch real-time weather dynamically from Open-Meteo for this exact phone location
        live_weather = weather_service.get_current_weather(
            lat=farmer_lat,
            lon=farmer_lon,
            region=user_region
        )
        outside_temp = float(live_weather["outside_temperature"])
        outside_hum = float(live_weather["outside_humidity"])
        display_region = region_override or live_weather.get("region") or user_region

        # 3. Retrieve real-time telemetry from database shed_telemetry table
        session = self._get_or_create_shed(shed_id)
        current_stage = session.get("current_stage") or user_stage or 3
        temp_target = session.get("temp_target", 26.0)
        hum_target = session.get("humidity_target", 75.0)
        air_quality_target = session.get("air_quality_target", 80.0)
        light_lux_target = session.get("light_lux_target", 25.0)
        is_auto_mode = session.get("is_auto_mode", True)

        latest_reading = get_latest_telemetry_reading_from_db(shed_id)
        if latest_reading:
            current_temp = float(latest_reading["indoor_temp"])
            current_hum = float(latest_reading["indoor_hum"])
            current_air_quality = float(latest_reading.get("air_quality", 88.0))
            current_light_lux = float(latest_reading.get("light_lux", 22.0))
            last_updated = latest_reading.get("timestamp") or datetime.now(timezone.utc)
            if isinstance(last_updated, str):
                try:
                    last_updated = datetime.fromisoformat(last_updated)
                except Exception:
                    last_updated = datetime.now(timezone.utc)
            db_actuators = ActuatorStates(
                cooler=bool(latest_reading.get("cooler", False)),
                fan=bool(latest_reading.get("fan", False)),
                heater=bool(latest_reading.get("heater", False)),
                light=bool(latest_reading.get("light", False)),
                light_brightness=int(latest_reading.get("light_brightness", 35 if latest_reading.get("light") else 0))
            )
            actuators = session.get("actuators") or db_actuators
            if "is_auto_mode" not in session:
                is_auto_mode = (latest_reading.get("mode", "AUTO") == "AUTO")
        else:
            # When no hardware sensor has posted yet for this shed,
            # calculate realistic indoor microclimate derived from the phone's live location ambient weather
            current_temp = round(outside_temp * 0.35 + 26.0 * 0.65, 1)
            current_hum = round(outside_hum * 0.4 + 75.0 * 0.6, 1)
            current_air_quality = 88.0
            current_light_lux = 22.0
            last_updated = datetime.now(timezone.utc)
            actuators = session.get("actuators") or ActuatorStates(
                cooler=current_temp > 26.5,
                fan=current_temp > 27.0 or current_air_quality < 80.0,
                heater=current_temp < 23.0,
                light=True,
                light_brightness=35
            )

        # 4. Evaluate rules engine
        status, headline, subline, next_act, photo_mode = rules_engine.evaluate(
            current_temp=current_temp,
            current_hum=current_hum,
            outside_temp=outside_temp,
            stage=current_stage,
            is_auto_mode=is_auto_mode,
            current_actuators=actuators,
            manual_temp_target=temp_target,
            manual_hum_target=hum_target,
            current_air_quality=current_air_quality,
            current_light_lux=current_light_lux,
            air_quality_target=air_quality_target,
            light_lux_target=light_lux_target
        )

        if is_auto_mode:
            actuators = next_act

        stage_meta = STAGE_THRESHOLDS.get(current_stage, STAGE_THRESHOLDS[3])

        return ShedOverview(
            shed_id=shed_id,
            farm_name=farm_name,
            region=display_region,
            overall_status=status,
            status_headline=headline,
            status_subline=subline,
            current_stage=current_stage,
            stage_name=stage_meta["name"],
            indoor_temp=current_temp,
            indoor_humidity=current_hum,
            indoor_air_quality=current_air_quality,
            indoor_light_lux=current_light_lux,
            outside_temp=outside_temp,
            outside_humidity=outside_hum,
            actuators=actuators,
            is_auto_mode=is_auto_mode,
            temp_target=temp_target,
            humidity_target=hum_target,
            air_quality_target=air_quality_target,
            light_lux_target=light_lux_target,
            photoperiod_mode=photo_mode,
            last_updated=last_updated
        )

    def update_setpoints(
        self,
        shed_id: str,
        is_auto: bool,
        temp_target: float,
        hum_target: float,
        air_quality_target: Optional[float] = None,
        light_lux_target: Optional[float] = None,
        light_brightness: Optional[int] = None,
        caller_user: Optional[str] = None
    ) -> ShedOverview:
        shed = self._get_or_create_shed(shed_id)
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

        overview = self.get_shed_overview(shed_id)

        # Check if updated setpoints cause a microclimate variation requiring an alert
        temp_deviation = abs(overview.indoor_temp - temp_target)
        is_temp_varying = (
            overview.overall_status in ["TOO_WARM", "TOO_COOL", "CRITICAL", "WARNING", "ALERT"]
            or temp_deviation >= 2.0
        )
        if is_temp_varying:
            try:
                farmers = get_farmers_by_shed_id(shed_id)
                if caller_user:
                    from app.services.db_service import get_user_by_username, get_user_by_id
                    caller = get_user_by_username(caller_user) or get_user_by_id(caller_user)
                    if caller and caller.get("id") not in [f.get("id") for f in farmers]:
                        farmers.append(caller)

                cooldown_sec = getattr(settings, "WHATSAPP_ALERT_COOLDOWN_SECONDS", 300)
                for farmer in farmers:
                    recipient = farmer.get("whatsapp_number") or farmer.get("phone")
                    if not recipient or recipient == "N/A":
                        continue
                    farmer_name = farmer.get("full_name") or farmer.get("username", "Farmer")
                    farm_name = farmer.get("farm_name") or shed.get("farm_name", f"Shed {shed_id.upper()}")
                    farmer_lang = farmer.get("preferred_language", "en")

                    var_msg = alert_service.build_temperature_variation_alert(
                        farmer_name=farmer_name,
                        farm_name=farm_name,
                        shed_id=shed_id,
                        current_temp=overview.indoor_temp,
                        temp_target=temp_target,
                        temp_min=temp_target - 1.0,
                        temp_max=temp_target + 1.0,
                        current_hum=overview.indoor_humidity,
                        status=overview.overall_status,
                        headline=overview.status_headline,
                        subline=overview.status_subline,
                        lang=farmer_lang,
                    )

                    alert_service.dispatch_in_background(
                        message=var_msg,
                        recipient=recipient,
                        cooldown_key=f"temp_var:{shed_id}:{farmer.get('id')}",
                        cooldown_seconds=cooldown_sec,
                    )
            except Exception as e:
                logger.error("Error dispatching setpoint variation alerts: %s", e)

        return overview

    def manual_override_actuator(
        self,
        shed_id: str,
        actuator: str,
        state: bool,
        value: Optional[int] = None,
        caller_user: Optional[str] = None
    ) -> ShedOverview:
        shed = self._get_or_create_shed(shed_id)
        shed["is_auto_mode"] = False

        # Enforce safety interlock
        if actuator == "cooler":
            shed["actuators"].cooler = state
            if state:
                shed["actuators"].heater = False
                try:
                    farmers = get_farmers_by_shed_id(shed_id)
                    if caller_user:
                        from app.services.db_service import get_user_by_username, get_user_by_id
                        caller = get_user_by_username(caller_user) or get_user_by_id(caller_user)
                        if caller and caller.get("id") not in [f.get("id") for f in farmers]:
                            farmers.append(caller)
                    cooldown_sec = getattr(settings, "WHATSAPP_ALERT_COOLDOWN_SECONDS", 300)
                    for farmer in farmers:
                        recipient = farmer.get("whatsapp_number") or farmer.get("phone")
                        if not recipient or recipient == "N/A":
                            continue
                        farmer_lang = farmer.get("preferred_language", "en")
                        farm_name = farmer.get("farm_name") or shed.get("farm_name", f"Shed {shed_id.upper()}")
                        msg = alert_service.build_manual_alert(
                            actuator="cooler",
                            outside_temp=shed.get("outside_temp", 0.0),
                            outside_humidity=shed.get("outside_hum", 0.0),
                            region=farm_name,
                            current_temp=shed.get("current_temp", 0.0),
                            current_humidity=shed.get("current_hum", 0.0),
                            lang=farmer_lang,
                        )
                        alert_service.dispatch_in_background(
                            message=msg,
                            recipient=recipient,
                            cooldown_key=f"manual:{shed_id}:cooler:{farmer.get('id')}",
                            cooldown_seconds=cooldown_sec,
                        )
                except Exception as e:
                    logger.error("Error sending cooler alert: %s", e)
        elif actuator == "heater":
            shed["actuators"].heater = state
            if state:
                shed["actuators"].cooler = False
                try:
                    farmers = get_farmers_by_shed_id(shed_id)
                    if caller_user:
                        from app.services.db_service import get_user_by_username, get_user_by_id
                        caller = get_user_by_username(caller_user) or get_user_by_id(caller_user)
                        if caller and caller.get("id") not in [f.get("id") for f in farmers]:
                            farmers.append(caller)
                    cooldown_sec = getattr(settings, "WHATSAPP_ALERT_COOLDOWN_SECONDS", 300)
                    for farmer in farmers:
                        recipient = farmer.get("whatsapp_number") or farmer.get("phone")
                        if not recipient or recipient == "N/A":
                            continue
                        farmer_lang = farmer.get("preferred_language", "en")
                        farm_name = farmer.get("farm_name") or shed.get("farm_name", f"Shed {shed_id.upper()}")
                        msg = alert_service.build_manual_alert(
                            actuator="heater",
                            outside_temp=shed.get("outside_temp", 0.0),
                            outside_humidity=shed.get("outside_hum", 0.0),
                            region=farm_name,
                            current_temp=shed.get("current_temp", 0.0),
                            current_humidity=shed.get("current_hum", 0.0),
                            lang=farmer_lang,
                        )
                        alert_service.dispatch_in_background(
                            message=msg,
                            recipient=recipient,
                            cooldown_key=f"manual:{shed_id}:heater:{farmer.get('id')}",
                            cooldown_seconds=cooldown_sec,
                        )
                except Exception as e:
                    logger.error("Error sending heater alert: %s", e)
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
        shed = self._get_or_create_shed(shed_id)
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
        if not records:
            overview = self.get_shed_overview(shed_id)
            records = [{
                "timestamp": datetime.now(timezone.utc),
                "shed_id": shed_id,
                "indoor_temp": overview.indoor_temp,
                "indoor_hum": overview.indoor_humidity,
                "air_quality": overview.indoor_air_quality,
                "light_lux": overview.indoor_light_lux,
                "outside_temp": overview.outside_temp,
                "outside_hum": overview.outside_humidity,
                "cooler": overview.actuators.cooler,
                "heater": overview.actuators.heater,
                "fan": overview.actuators.fan,
                "light": overview.actuators.light,
                "light_brightness": overview.actuators.light_brightness
            }]

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
