import os
from typing import Any, Dict, Optional

from twilio.rest import Client

from app.core.config import settings


class WhatsAppAlertService:
    """Simple WhatsApp notifier for Setu. Supports dry-run to test without hardware or sending."""

    def __init__(self):
        self.account_sid = (
            os.getenv("TWILIO_ACCOUNT_SID")
            or os.getenv("TWILIO_ACCOUNT_SSID")
            or getattr(settings, "TWILIO_ACCOUNT_SID", "")
            or getattr(settings, "TWILIO_ACCOUNT_SSID", "")
        )
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN") or getattr(settings, "TWILIO_AUTH_TOKEN", "")
        self.from_number = os.getenv("TWILIO_WHATSAPP_FROM") or getattr(settings, "TWILIO_WHATSAPP_FROM", "")
        self.default_to = os.getenv("TWILIO_WHATSAPP_TO") or getattr(settings, "TWILIO_WHATSAPP_TO", "")

        self._client = None
        if self.account_sid and self.auth_token:
            try:
                self._client = Client(self.account_sid, self.auth_token)
            except Exception:
                self._client = None

    @staticmethod
    def normalize_whatsapp(value: str) -> str:
        value = (value or "").strip()
        if not value:
            return value
        if value.startswith("whatsapp:"):
            return value
        return f"whatsapp:{value}"

    def build_manual_alert(
        self,
        *,
        actuator: str,
        outside_temp: Optional[float] = None,
        outside_humidity: Optional[float] = None,
        region: Optional[str] = None,
        current_temp: Optional[float] = None,
        current_humidity: Optional[float] = None,
    ) -> str:
        region_name = region or "the shed"
        temp_text = f"{outside_temp:.1f}°C" if outside_temp is not None else "the outside climate"
        humidity_text = (
            f"{outside_humidity:.0f}% humidity" if outside_humidity is not None else "humid conditions"
        )

        if actuator == "cooler":
            return (
                f"Setu manual alert: cooling was started for {region_name}. "
                f"Outside temperature is {temp_text} and the shed needs cooling support. "
                f"Current shed temp is {current_temp:.1f}°C and humidity is {current_humidity:.0f}% ."
            )

        if actuator == "heater":
            return (
                f"Setu manual alert: heater was started for {region_name}. "
                f"The environment is cool and wet ({humidity_text}, outside temp {temp_text}), so warming is being applied manually. "
                f"Current shed temp is {current_temp:.1f}°C and humidity is {current_humidity:.0f}% ."
            )

        return (
            f"Setu manual alert: a manual control action was triggered in {region_name}. "
            f"Outside conditions are {temp_text} and {humidity_text}."
        )

    def send(
        self,
        *,
        message: str,
        recipient: Optional[str] = None,
        dry_run: bool = False,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        target = self.normalize_whatsapp(recipient or self.default_to)
        if not target:
            return {
                "status": "disabled",
                "message": "No WhatsApp recipient configured. Set TWILIO_WHATSAPP_TO or pass a recipient.",
                "recipient": None,
            }

        if not self.account_sid or not self.auth_token or not self.from_number:
            if dry_run:
                return {
                    "status": "dry-run",
                    "message": f"Setu dry run: would send to {target} -> {message}",
                    "recipient": target,
                    "preview": message,
                    "media_url": media_url,
                }
            return {
                "status": "disabled",
                "message": "Twilio WhatsApp is not configured. Add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM.",
                "recipient": target,
            }

        if dry_run:
            return {
                "status": "dry-run",
                "message": f"Setu dry run: would send to {target} -> {message}",
                "recipient": target,
                "preview": message,
                "media_url": media_url,
            }

        if self._client is None:
            return {
                "status": "error",
                "message": "Twilio client could not be initialized.",
                "recipient": target,
            }

        try:
            payload = {
                "body": message,
                "from_": self.normalize_whatsapp(self.from_number),
                "to": target,
            }
            if media_url:
                payload["media_url"] = [media_url]

            twilio_message = self._client.messages.create(**payload)
            return {
                "status": "sent",
                "message": "WhatsApp alert sent successfully.",
                "recipient": target,
                "sid": twilio_message.sid,
                "preview": message,
                "media_url": media_url,
            }
        except Exception as exc:  # pragma: no cover - network layer
            return {
                "status": "error",
                "message": f"Twilio WhatsApp send failed: {exc}",
                "recipient": target,
                "media_url": media_url,
            }


alert_service = WhatsAppAlertService()
