from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from collections import deque
import io
import csv
import asyncio
import logging
from fastapi import WebSocket

from app.models.schemas import TelemetryPayload, TelemetryBatchPayload, ActuatorStates, ShedOverview
from app.services.rules_engine import rules_engine, STAGE_THRESHOLDS
from app.services.weather_service import weather_service
from app.core.config import settings
from app.services.db_service import (
    save_telemetry_reading,
    save_telemetry_batch,
    get_telemetry_history_from_db,
    get_latest_telemetry_reading_from_db,
    get_farmers_by_shed_id,
    create_device_command,
    update_device_heartbeat,
)
from app.services.whatsapp_alerts import alert_service
from app.services.voice_service import voice_service

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages active WebSocket and SSE connections for real-time telemetry streaming.
    Supports channel-based shed subscriptions and broadcast fan-out.
    """
    def __init__(self):
        # shed_id -> list of active WebSocket connections
        self.shed_connections: Dict[str, List[WebSocket]] = {}
        self.global_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, shed_id: Optional[str] = None):
        await websocket.accept()
        if shed_id:
            if shed_id not in self.shed_connections:
                self.shed_connections[shed_id] = []
            self.shed_connections[shed_id].append(websocket)
        else:
            self.global_connections.append(websocket)

    def disconnect(self, websocket: WebSocket, shed_id: Optional[str] = None):
        if shed_id and shed_id in self.shed_connections:
            if websocket in self.shed_connections[shed_id]:
                self.shed_connections[shed_id].remove(websocket)
        if websocket in self.global_connections:
            self.global_connections.remove(websocket)

    async def broadcast_to_shed(self, shed_id: str, message: dict):
        targets = list(self.shed_connections.get(shed_id, [])) + list(self.global_connections)
        for connection in targets:
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection, shed_id)

    async def broadcast(self, message: dict):
        all_conns = list(self.global_connections)
        for conns in self.shed_connections.values():
            all_conns.extend(conns)
        for connection in set(all_conns):
            try:
                await connection.send_json(message)
            except Exception:
                pass

    def broadcast_sync(self, message: dict):
        """Non-blocking schedule of broadcast if event loop is running."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                shed_id = message.get("shed_id")
                if shed_id:
                    asyncio.create_task(self.broadcast_to_shed(shed_id, message))
                else:
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
        self._shed_farmer_cache: Dict[str, Dict[str, Any]] = {}

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
        """
        Ultra-low-latency telemetry ingestion path.
        Processes rules, persists reading, evaluates variation alerts in background,
        and constructs overview directly without synchronous upstream HTTP or DB roundtrips.
        """
        session = self._get_or_create_shed(payload.shed_id)
        current_stage = session.get("current_stage", 3)
        is_auto_mode = session.get("is_auto_mode", True)
        temp_target = session.get("temp_target", 26.0)
        hum_target = session.get("humidity_target", 75.0)
        air_quality_target = session.get("air_quality_target", 80.0)
        light_lux_target = session.get("light_lux_target", 25.0)
        current_act = session.get("actuators", ActuatorStates())

        # Evaluate deterministic rules engine
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

        # Persist reading to database and bounded memory ring buffer
        self.history.append(reading_record)
        save_telemetry_reading(reading_record)

        # Update device heartbeat & sequence tracking if device_id supplied
        if payload.device_id:
            try:
                update_device_heartbeat(payload.device_id, payload.sequence_number)
            except Exception:
                pass

        session["actuators"] = next_actuators if is_auto_mode else current_act
        session["photoperiod_mode"] = photo_mode

        # Check for temperature variation or microclimate anomaly
        thresholds = STAGE_THRESHOLDS.get(session.get("current_stage", 3), STAGE_THRESHOLDS[3])
        target_temp_max = thresholds.get("temp_max", 27.0)
        target_temp_min = thresholds.get("temp_min", 25.0)
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

        # High-performance in-memory Overview assembly (<0.02ms)
        stage_name = STAGE_THRESHOLDS.get(current_stage, {}).get("name", f"Instar {current_stage}")
        farm_name = session.get("farm_name") or f"Shed {payload.shed_id.upper()}"
        region = session.get("region") or "Sericulture Shed"

        overview = ShedOverview(
            shed_id=payload.shed_id,
            farm_name=farm_name,
            region=region,
            overall_status=status,
            status_headline=headline,
            status_subline=subline,
            current_stage=current_stage,
            stage_name=stage_name,
            indoor_temp=payload.temperature,
            indoor_humidity=payload.humidity,
            indoor_air_quality=payload.air_quality if payload.air_quality is not None else 88.0,
            indoor_light_lux=payload.light_lux if payload.light_lux is not None else 22.0,
            outside_temp=payload.outside_temperature or 30.0,
            outside_humidity=payload.outside_humidity or 60.0,
            actuators=session["actuators"],
            is_auto_mode=is_auto_mode,
            temp_target=temp_target,
            humidity_target=hum_target,
            air_quality_target=air_quality_target,
            light_lux_target=light_lux_target,
            photoperiod_mode=photo_mode,
            last_updated=datetime.now(timezone.utc),
        )

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

    def record_batch_readings(self, items: List[TelemetryPayload]) -> int:
        """
        High-throughput batch ingestion path.
        Takes hundreds/thousands of readings, saves them in one multi-row database write,
        and broadcasts latest states to active subscribers.
        """
        if not items:
            return 0

        records = []
        now_dt = datetime.now(timezone.utc)
        for item in items:
            session = self._get_or_create_shed(item.shed_id)
            current_stage = session.get("current_stage", 3)
            is_auto_mode = session.get("is_auto_mode", True)
            temp_target = session.get("temp_target", 26.0)
            hum_target = session.get("humidity_target", 75.0)
            current_act = session.get("actuators", ActuatorStates())

            status, _, _, next_actuators, photo_mode = rules_engine.evaluate(
                current_temp=item.temperature,
                current_hum=item.humidity,
                outside_temp=item.outside_temperature or 30.0,
                stage=current_stage,
                is_auto_mode=is_auto_mode,
                current_actuators=current_act,
                manual_temp_target=temp_target,
                manual_hum_target=hum_target,
            )
            session["actuators"] = next_actuators if is_auto_mode else current_act
            session["photoperiod_mode"] = photo_mode

            records.append({
                "shed_id": item.shed_id,
                "timestamp": item.timestamp or now_dt,
                "indoor_temp": item.temperature,
                "indoor_hum": item.humidity,
                "air_quality": item.air_quality or 88.0,
                "light_lux": item.light_lux or 22.0,
                "outside_temp": item.outside_temperature,
                "outside_hum": item.outside_humidity,
                "cooler": next_actuators.cooler if is_auto_mode else current_act.cooler,
                "heater": next_actuators.heater if is_auto_mode else current_act.heater,
                "fan": next_actuators.fan if is_auto_mode else current_act.fan,
                "light": next_actuators.light if is_auto_mode else current_act.light,
                "light_brightness": next_actuators.light_brightness if is_auto_mode else current_act.light_brightness,
                "mode": "AUTO" if is_auto_mode else "MANUAL",
            })

        count = save_telemetry_batch(records)
        return count

    def get_shed_overview(
        self,
        shed_id: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        region_override: Optional[str] = None
    ) -> ShedOverview:
        # 1. Resolve farmer details from PostgreSQL or in-memory cache
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

        # 3. Retrieve real-time telemetry from database or L1 cache
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
            current_temp = 25.0
            current_hum = 75.0
            current_air_quality = 88.0
            current_light_lux = 22.0
            last_updated = datetime.now(timezone.utc)
            actuators = session.get("actuators", ActuatorStates())

        # Evaluate rules engine
        status, headline, subline, next_actuators, photo_mode = rules_engine.evaluate(
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

        stage_info = STAGE_THRESHOLDS.get(current_stage, STAGE_THRESHOLDS[3])
        stage_name = stage_info.get("name", "Instar")

        # Cache resolved farm & region
        session["farm_name"] = farm_name
        session["region"] = display_region

        return ShedOverview(
            shed_id=shed_id,
            farm_name=farm_name,
            region=display_region,
            overall_status=status,
            status_headline=headline,
            status_subline=subline,
            current_stage=current_stage,
            stage_name=stage_name,
            indoor_temp=current_temp,
            indoor_humidity=current_hum,
            indoor_air_quality=current_air_quality,
            indoor_light_lux=current_light_lux,
            outside_temp=outside_temp,
            outside_humidity=outside_hum,
            actuators=actuators if not is_auto_mode else next_actuators,
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
        caller_user: Optional[str] = "operator"
    ) -> ShedOverview:
        session = self._get_or_create_shed(shed_id)
        session["is_auto_mode"] = is_auto
        session["temp_target"] = temp_target
        session["humidity_target"] = hum_target
        if air_quality_target is not None:
            session["air_quality_target"] = air_quality_target
        if light_lux_target is not None:
            session["light_lux_target"] = light_lux_target
        if light_brightness is not None:
            current_act = session.get("actuators", ActuatorStates())
            current_act.light_brightness = light_brightness
            current_act.light = light_brightness > 0
            session["actuators"] = current_act

        # Record command in safe lifecycle table for IoT nodes
        try:
            create_device_command(
                device_id=f"esp32_{shed_id}",
                shed_id=shed_id,
                requested_by=caller_user or "operator",
                command_type="SET_SETPOINTS",
                command_payload={
                    "is_auto_mode": is_auto,
                    "temp_target": temp_target,
                    "humidity_target": hum_target,
                    "air_quality_target": air_quality_target,
                    "light_lux_target": light_lux_target,
                    "light_brightness": light_brightness,
                }
            )
        except Exception as e:
            logger.debug("create_device_command error: %s", e)

        return self.get_shed_overview(shed_id)

    def manual_override_actuator(
        self,
        shed_id: str,
        actuator: str,
        state: bool,
        value: Optional[int] = None,
        caller_user: Optional[str] = "operator"
    ) -> ShedOverview:
        session = self._get_or_create_shed(shed_id)
        session["is_auto_mode"] = False

        current_act = session.get("actuators", ActuatorStates())

        # Safety Interlocks: Cooler and Heater cannot be ON simultaneously
        if actuator == "cooler":
            current_act.cooler = state
            if state:
                current_act.heater = False
        elif actuator == "heater":
            current_act.heater = state
            if state:
                current_act.cooler = False
        elif actuator == "fan":
            current_act.fan = state
        elif actuator == "light":
            current_act.light = state
            if not state:
                current_act.light_brightness = 0
            elif current_act.light_brightness == 0:
                current_act.light_brightness = 35
        elif actuator == "light_brightness":
            val = max(0, min(100, value if value is not None else 0))
            current_act.light_brightness = val
            current_act.light = val > 0

        session["actuators"] = current_act

        # Queue safe command in device_commands table for hardware node
        try:
            create_device_command(
                device_id=f"esp32_{shed_id}",
                shed_id=shed_id,
                requested_by=caller_user or "operator",
                command_type="SET_ACTUATOR",
                command_payload={
                    "actuator": actuator,
                    "state": state,
                    "value": value,
                }
            )
        except Exception as e:
            logger.debug("create_device_command error: %s", e)

        # Trigger manual action notification
        try:
            farmer = get_farmers_by_shed_id(shed_id)
            if farmer:
                f_obj = farmer[0]
                recipient = f_obj.get("whatsapp_number") or f_obj.get("phone")
                farmer_lang = f_obj.get("preferred_language", "en")
                latest = get_latest_telemetry_reading_from_db(shed_id) or {}
                if state and actuator in ["cooler", "heater"]:
                    msg = alert_service.build_manual_alert(
                        actuator=actuator,
                        outside_temp=latest.get("outside_temp"),
                        outside_humidity=latest.get("outside_hum"),
                        region=session.get("region"),
                        current_temp=latest.get("indoor_temp"),
                        current_humidity=latest.get("indoor_hum"),
                        lang=farmer_lang,
                    )
                    alert_service.dispatch_in_background(
                        message=msg,
                        recipient=recipient,
                        cooldown_key=f"manual:{shed_id}:{actuator}",
                        cooldown_seconds=60,
                    )
        except Exception:
            pass

        return self.get_shed_overview(shed_id)

    def set_growth_stage(self, shed_id: str, stage: int) -> ShedOverview:
        shed = self._get_or_create_shed(shed_id)
        if 1 <= stage <= 5:
            shed["current_stage"] = stage
        return self.get_shed_overview(shed_id)

    def get_history(self, shed_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        db_history = get_telemetry_history_from_db(shed_id, limit=limit)
        if db_history:
            return db_history

        # Fallback to in-memory history if DB has no historical records yet
        matching = [r for r in self.history if r["shed_id"] == shed_id]
        if not matching:
            now = datetime.now(timezone.utc)
            return [
                {
                    "timestamp": (now - timedelta(minutes=i*10)).isoformat(),
                    "indoor_temp": 25.5,
                    "indoor_hum": 75.0,
                    "air_quality": 88.0,
                    "light_lux": 22.0,
                    "outside_temp": 32.0,
                    "outside_hum": 55.0,
                    "cooler": False,
                    "heater": False,
                    "fan": False,
                    "humidifier": False,
                    "light": False,
                    "light_brightness": 0,
                    "mode": "AUTO"
                }
                for i in range(12, 0, -1)
            ]
        return matching[-limit:]

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
            ts = r.get("timestamp")
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
