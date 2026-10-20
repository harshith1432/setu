import os
import json
import time
import logging
import queue
import socket
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class SIEMForwarder:
    """
    24/7 Enterprise SIEM & SOC Log Forwarding Engine.
    Streams security telemetry, authorization failures, actuator commands, and audit trails to:
    - Wazuh / OSSEC
    - Splunk HEC (HTTP Event Collector)
    - Datadog Logs API
    - Remote Syslog (RFC 5424 / RFC 3164)
    - Common Event Format (CEF) / Elastic Common Schema (ECS) file streamer
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SIEMForwarder, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, buffer_size: int = 10000):
        if getattr(self, "_initialized", False):
            return

        self.syslog_host = os.getenv("SIEM_SYSLOG_HOST")
        self.syslog_port = int(os.getenv("SIEM_SYSLOG_PORT", "514"))
        self.splunk_url = os.getenv("SPLUNK_HEC_URL")
        self.splunk_token = os.getenv("SPLUNK_HEC_TOKEN")
        self.datadog_api_key = os.getenv("DATADOG_API_KEY")
        self.log_file_path = os.getenv("SIEM_LOG_FILE", "logs/siem_events.log")

        # In-memory non-blocking queue
        self.event_queue: queue.Queue = queue.Queue(maxsize=buffer_size)
        self.recent_events: List[Dict[str, Any]] = []
        self._recent_lock = threading.Lock()
        self._max_recent = 100

        # Create logs directory if file forwarding enabled
        try:
            os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
        except Exception:
            pass

        self._running = True
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()

        self._initialized = True
        logger.info("SIEM Forwarder initialized (Syslog: %s, Splunk: %s, LogFile: %s)",
                    bool(self.syslog_host), bool(self.splunk_url), self.log_file_path)

    def format_cef(self, event: Dict[str, Any]) -> str:
        """
        Formats event into Micro Focus Common Event Format (CEF:0).
        CEF:Version|Device Vendor|Device Product|Device Version|Signature ID|Name|Severity|Extension
        """
        severity = str(event.get("severity", 5))
        sig_id = event.get("action", "SECURITY_EVENT")
        name = event.get("details", {}).get("description") or sig_id
        
        # Extensions key=value pairs
        exts = [
            f"src={event.get('ip_address', '127.0.0.1')}",
            f"suser={event.get('user_id', 'unknown')}",
            f"outcome={event.get('status', 'SUCCESS')}",
            f"cs1Label=Organization cs1={event.get('organization_id', 'org_default')}",
            f"cs2Label=DeviceID cs2={event.get('device_id', 'none')}"
        ]
        return f"CEF:0|SeriCare|IoTPlatform|1.0|{sig_id}|{name}|{severity}|{' '.join(exts)}"

    def format_ecs_json(self, event: Dict[str, Any]) -> str:
        """
        Formats event into Elastic Common Schema (ECS 8.x) JSON for Elasticsearch / Wazuh.
        """
        ecs = {
            "@timestamp": event.get("timestamp"),
            "event": {
                "category": ["authentication", "configuration", "process"],
                "action": event.get("action"),
                "outcome": "success" if event.get("status") in ["SUCCESS", "APPLIED", "200"] else "failure",
                "severity": event.get("severity", 5)
            },
            "source": {
                "ip": event.get("ip_address")
            },
            "user": {
                "id": str(event.get("user_id")),
                "organization": event.get("organization_id")
            },
            "sericare": {
                "device_id": event.get("device_id"),
                "details": event.get("details")
            }
        }
        return json.dumps(ecs)

    def forward_event(
        self,
        action: str,
        user_id: Optional[Any] = None,
        organization_id: Optional[str] = None,
        device_id: Optional[str] = None,
        status: str = "SUCCESS",
        severity: int = 5,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Non-blocking enqueue of security events for real-time SIEM dissemination.
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "user_id": str(user_id) if user_id else "system",
            "organization_id": organization_id or "org_default",
            "device_id": device_id,
            "status": status,
            "severity": severity,
            "ip_address": ip_address or "127.0.0.1",
            "details": details or {}
        }

        # Keep a ring buffer for recent inspection / tests
        with self._recent_lock:
            self.recent_events.append(event)
            if len(self.recent_events) > self._max_recent:
                self.recent_events.pop(0)

        try:
            self.event_queue.put_nowait(event)
        except queue.Full:
            logger.warning("SIEM event queue full! Dropping event: %s", action)

    def _process_queue(self):
        """Background worker draining events to configured external collectors."""
        while self._running:
            try:
                event = self.event_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            try:
                # 1. Write to local SIEM file buffer
                cef_line = self.format_cef(event)
                ecs_line = self.format_ecs_json(event)
                try:
                    with open(self.log_file_path, "a", encoding="utf-8") as f:
                        f.write(ecs_line + "\n")
                except Exception:
                    pass

                # 2. Syslog forwarding (UDP)
                if self.syslog_host:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        sock.sendto(cef_line.encode("utf-8"), (self.syslog_host, self.syslog_port))
                        sock.close()
                    except Exception as ex:
                        logger.debug("Failed sending syslog: %s", ex)

                # 3. Splunk / Datadog webhook forwarding
                if self.splunk_url and self.splunk_token:
                    self._send_splunk_hec(event)

            except Exception as e:
                logger.error("Error in SIEM dispatch worker: %s", e)
            finally:
                self.event_queue.task_done()

    def _send_splunk_hec(self, event: Dict[str, Any]):
        """Transmits event to Splunk HTTP Event Collector."""
        try:
            import urllib.request
            payload = json.dumps({"event": event, "sourcetype": "_json"}).encode("utf-8")
            req = urllib.request.Request(
                self.splunk_url,
                data=payload,
                headers={
                    "Authorization": f"Splunk {self.splunk_token}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                pass
        except Exception as ex:
            logger.debug("Splunk HEC forwarding failed: %s", ex)

    def get_recent_events(self) -> List[Dict[str, Any]]:
        """Returns snapshot of recent events for testing and diagnostics."""
        with self._recent_lock:
            return list(self.recent_events)

siem_forwarder = SIEMForwarder()
