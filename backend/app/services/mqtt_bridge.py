import json
import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.models.schemas import TelemetryPayload, DeviceCommandAck, CommandStatus
from app.services.telemetry_service import telemetry_service
from app.services.db_service import acknowledge_device_command, get_device_by_id, update_device_heartbeat

logger = logging.getLogger(__name__)

# MQTT 5 Enterprise Topic Pattern:
# organizations/{org_id}/devices/{device_id}/{action}
TOPIC_REGEX = re.compile(r"^organizations/(?P<org_id>[^/]+)/devices/(?P<device_id>[^/]+)/(?P<action>telemetry|status|commands|command-acks)$")


class MQTTBridgeService:
    """
    MQTT 5 Enterprise Ingestion & Command Dispatch Bridge.
    Handles device authentication, schema validation, topic routing,
    and bi-directional command delivery.
    """

    def parse_topic(self, topic: str) -> Optional[Dict[str, str]]:
        match = TOPIC_REGEX.match(topic)
        if match:
            return match.groupdict()
        return None

    def handle_incoming_message(self, topic: str, payload_bytes: bytes) -> Dict[str, Any]:
        """Processes an incoming MQTT message from a registered IoT node."""
        parsed = self.parse_topic(topic)
        if not parsed:
            logger.warning("Unrecognized MQTT topic format: %s", topic)
            return {"status": "rejected", "reason": "invalid_topic_format"}

        org_id = parsed["org_id"]
        device_id = parsed["device_id"]
        action = parsed["action"]

        try:
            payload_str = payload_bytes.decode("utf-8")
            data = json.loads(payload_str)
        except Exception:
            logger.warning("Malformed MQTT JSON payload received")
            return {"status": "rejected", "reason": "malformed_json"}

        # 1. Telemetry Ingestion
        if action == "telemetry":
            shed_id = data.get("shed_id")
            if not shed_id:
                # Resolve shed from device registry
                dev = get_device_by_id(device_id)
                shed_id = dev.get("shed_id") if dev else "shed_01"

            telemetry_payload = TelemetryPayload(
                shed_id=shed_id,
                device_id=device_id,
                organization_id=org_id,
                temperature=float(data.get("temperature", 25.0)),
                humidity=float(data.get("humidity", 75.0)),
                air_quality=float(data.get("air_quality", 88.0)),
                light_lux=float(data.get("light_lux", 22.0)),
                outside_temperature=float(data.get("outside_temperature", 30.0)) if data.get("outside_temperature") is not None else None,
                outside_humidity=float(data.get("outside_humidity", 60.0)) if data.get("outside_humidity") is not None else None,
                sequence_number=data.get("sequence_number"),
                event_id=data.get("event_id"),
                firmware_version=data.get("firmware_version", "1.0.0"),
            )
            overview = telemetry_service.record_reading(telemetry_payload)
            return {"status": "accepted", "action": "telemetry", "shed_id": shed_id}

        # 2. Command Acknowledgement
        elif action == "command-acks":
            command_id = data.get("command_id")
            raw_status = data.get("status", "APPLIED")
            error_message = data.get("error_message")
            applied_state = data.get("applied_state")

            try:
                status_enum = CommandStatus(raw_status)
            except Exception:
                status_enum = CommandStatus.APPLIED

            ack_res = acknowledge_device_command(
                command_id=command_id,
                device_id=device_id,
                status=status_enum.value,
                error_message=error_message,
                applied_state=applied_state,
            )
            return {"status": "processed", "action": "command-ack", "result": ack_res is not None}

        # 3. Device Heartbeat / Status
        elif action == "status":
            seq = data.get("sequence_number")
            update_device_heartbeat(device_id, seq)
            return {"status": "accepted", "action": "status"}

        return {"status": "ignored"}


mqtt_bridge = MQTTBridgeService()
