import logging
import os
import re
import threading
import time
from typing import Any, Dict, Optional

try:
    from twilio.rest import Client
except ImportError:
    Client = None

from app.core.config import settings

logger = logging.getLogger(__name__)

_cooldown_lock = threading.Lock()
_last_alert_timestamps: Dict[str, float] = {}


class WhatsAppAlertService:
    """Production-ready WhatsApp notifier for Setu. Supports dry-run, background dispatch, and cooldown throttling."""

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
        if Client is not None and self.account_sid and self.auth_token:
            try:
                self._client = Client(self.account_sid, self.auth_token)
            except Exception:
                self._client = None

    @property
    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.from_number)

    @staticmethod
    def normalize_whatsapp(value: str) -> str:
        """Normalizes any phone string into valid E.164 with whatsapp: prefix."""
        raw = (value or "").strip()
        if not raw:
            return ""
        if raw.startswith("whatsapp:"):
            raw = raw[len("whatsapp:"):].strip()

        # Remove spaces, dashes, parentheses, dots
        cleaned = re.sub(r"[\s\-\(\)\.]", "", raw)

        # Standardize country codes (defaulting 10-digit to India +91)
        if cleaned.startswith("+"):
            digits = re.sub(r"\D", "", cleaned[1:])
            normalized = f"+{digits}"
        else:
            digits = re.sub(r"\D", "", cleaned)
            if len(digits) == 10:
                normalized = f"+91{digits}"
            elif len(digits) == 11 and digits.startswith("0"):
                normalized = f"+91{digits[1:]}"
            elif len(digits) == 12 and digits.startswith("91"):
                normalized = f"+{digits}"
            else:
                normalized = f"+{digits}" if digits else ""

        return f"whatsapp:{normalized}" if normalized else ""

    def check_and_update_cooldown(self, cooldown_key: Optional[str], cooldown_seconds: int) -> bool:
        """Returns True if the alert is permitted, False if throttled."""
        if not cooldown_key or cooldown_seconds <= 0:
            return True
        now = time.time()
        with _cooldown_lock:
            last = _last_alert_timestamps.get(cooldown_key, 0.0)
            if now - last < cooldown_seconds:
                return False
            _last_alert_timestamps[cooldown_key] = now
            return True

    def rollback_cooldown(self, cooldown_key: Optional[str]) -> None:
        """Rolls back a cooldown lock if dispatch fails, allowing future retries."""
        if not cooldown_key:
            return
        with _cooldown_lock:
            _last_alert_timestamps.pop(cooldown_key, None)

    def build_manual_alert(
        self,
        *,
        actuator: str,
        outside_temp: Optional[float] = None,
        outside_humidity: Optional[float] = None,
        region: Optional[str] = None,
        current_temp: Optional[float] = None,
        current_humidity: Optional[float] = None,
        lang: str = "en",
    ) -> str:
        region_name = region or "the shed"
        temp_text = f"{outside_temp:.1f}°C" if outside_temp is not None else "outside conditions"
        humidity_text = (
            f"{outside_humidity:.0f}% humidity" if outside_humidity is not None else "humid"
        )
        current_temp_text = f"{current_temp:.1f}°C" if current_temp is not None else "optimal"
        current_hum_text = f"{current_humidity:.0f}%" if current_humidity is not None else "optimal"

        lang_code = (lang or "en").lower()
        if lang_code == "kn":
            if actuator == "cooler":
                return (
                    f"ಸೇತು ಕೈಚಾಲಿತ ಎಚ್ಚರಿಕೆ: {region_name} ಶೆಡ್‌ಗಾಗಿ ಕೂಲರ್ ಆರಂಭಿಸಲಾಗಿದೆ. "
                    f"ಹೊರಗಿನ ತಾಪಮಾನ {temp_text}, ಶೆಡ್ ಪ್ರಸ್ತುತ ತಾಪಮಾನ {current_temp_text} ಮತ್ತು ಆರ್ದ್ರತೆ {current_hum_text}."
                )
            if actuator == "heater":
                return (
                    f"ಸೇತು ಕೈಚಾಲಿತ ಎಚ್ಚರಿಕೆ: {region_name} ಶೆಡ್‌ಗಾಗಿ ಹೀಟರ್ ಆರಂಭಿಸಲಾಗಿದೆ. "
                    f"ಹೊರಗಿನ ಆರ್ದ್ರತೆ {humidity_text}, ಶೆಡ್ ಪ್ರಸ್ತುತ ತಾಪಮಾನ {current_temp_text} ಮತ್ತು ಆರ್ದ್ರತೆ {current_hum_text}."
                )
            return f"ಸೇತು ಎಚ್ಚರಿಕೆ: {region_name} ಶೆಡ್‌ನಲ್ಲಿ {actuator} ಹಸ್ತಚಾಲಿತವಾಗಿ ನಿಯಂತ್ರಿಸಲಾಗಿದೆ."

        if lang_code == "te":
            if actuator == "cooler":
                return (
                    f"సేతు హెచ్చరిక: {region_name} షెడ్ కోసం కూలర్ ప్రారంభించబడింది. "
                    f"వెలుపలి ఉష్ణోగ్రత {temp_text}, ప్రస్తుత షెడ్ ఉష్ణోగ్రత {current_temp_text} మరియు తేమ {current_hum_text}."
                )
            if actuator == "heater":
                return (
                    f"సేతు హెచ్చరిక: {region_name} షెడ్ కోసం హీటర్ ప్రారంభించబడింది. "
                    f"వెలుపలి తేమ {humidity_text}, ప్రస్తుత షెడ్ ఉష్ణోగ్రత {current_temp_text} మరియు తేమ {current_hum_text}."
                )
            return f"సేతు హెచ్చరిక: {region_name} షెడ్‌లో {actuator} మాన్యువల్‌గా నియంత్రించబడింది."

        # Default English
        if actuator == "cooler":
            return (
                f"Setu manual alert: cooling was started for {region_name}. "
                f"Outside temperature is {temp_text} and the shed needs cooling support. "
                f"Current shed temp is {current_temp_text} and humidity is {current_hum_text}."
            )

        if actuator == "heater":
            return (
                f"Setu manual alert: heater was started for {region_name}. "
                f"The environment is cool and wet ({humidity_text}, outside temp {temp_text}), so warming is being applied manually. "
                f"Current shed temp is {current_temp_text} and humidity is {current_hum_text}."
            )

        return (
            f"Setu manual alert: a manual control action ({actuator}) was triggered in {region_name}. "
            f"Outside conditions are {temp_text} and {humidity_text}."
        )

    def build_temperature_variation_alert(
        self,
        *,
        farmer_name: str,
        farm_name: str,
        shed_id: str,
        current_temp: float,
        temp_target: float,
        temp_min: float,
        temp_max: float,
        current_hum: float,
        status: str,
        headline: str,
        subline: str,
        cooler_active: Optional[bool] = None,
        heater_active: Optional[bool] = None,
        fan_active: Optional[bool] = None,
        lang: str = "en",
    ) -> str:
        """Builds a rich, personalized shed temperature variation alert showing live data,
        active system controls, and a concise 1-line explanation of what SeriCare is doing."""
        lang_code = (lang or "en").lower()

        # Determine actuator states if not explicitly passed
        if cooler_active is None:
            cooler_active = ("COOL" in headline.upper()) or (status == "TOO_WARM") or (current_temp > temp_target)
        if heater_active is None:
            heater_active = ("HEAT" in headline.upper()) or (status == "TOO_COOL") or (current_temp < temp_target)
        if fan_active is None:
            fan_active = cooler_active or ("FAN" in headline.upper())

        if lang_code == "kn":
            cooler_str = "ಚಾಲನೆಯಲ್ಲಿದೆ (ON) ❄️" if cooler_active else "ಆಫ್ (OFF)"
            fan_str = "ಚಾಲನೆಯಲ್ಲಿದೆ (ON) 💨" if fan_active else "ಆಫ್ (OFF)"
            heater_str = "ಚಾಲನೆಯಲ್ಲಿದೆ (ON) 🔥" if heater_active else "ಆಫ್ (OFF)"

            if cooler_active or current_temp > temp_target:
                action_expl = f"ಶೆಡ್ ತಾಪಮಾನವನ್ನು {current_temp:.1f}°C ನಿಂದ ಸೂಕ್ತ {temp_target:.1f}°C ಗೆ ತಗ್ಗಿಸಲು ಕೂಲರ್ ಮತ್ತು ಫ್ಯಾನ್ ಚಾಲನೆ ಮಾಡಲಾಗುತ್ತಿದೆ."
            elif heater_active or current_temp < temp_target:
                action_expl = f"ಶೆಡ್ ತಾಪಮಾನವನ್ನು {current_temp:.1f}°C ನಿಂದ ಸೂಕ್ತ {temp_target:.1f}°C ಗೆ ಏರಿಸಲು ಹೀಟರ್ ಚಾಲನೆ ಮಾಡಲಾಗುತ್ತಿದೆ."
            else:
                action_expl = f"ಶೆಡ್ ತಾಪಮಾನ ಮತ್ತು ಆರ್ದ್ರತೆಯನ್ನು ಸೂಕ್ತ ಮಟ್ಟದಲ್ಲಿಡಲು ಸ್ವಯಂಚಾಲಿತ ನಿಯಂತ್ರಣ ಕಾರ್ಯನಿರ್ವಹಿಸುತ್ತಿದೆ."

            return (
                f"🌾 {farmer_name} ಅವರಿಗೆ ಸೇತು ಶೆಡ್ ಎಚ್ಚರಿಕೆ\n"
                f"📍 ಶೆಡ್: {shed_id} ({farm_name})\n"
                f"⚠️ ತಾಪಮಾನದಲ್ಲಿ ವ್ಯತ್ಯಾಸ ಕಂಡುಬಂದಿದೆ!\n"
                f"• ಪ್ರಸ್ತುತ ತಾಪಮಾನ: {current_temp:.1f}°C\n"
                f"• ಸೂಕ್ತ ಮಿತಿ: {temp_min:.1f}°C - {temp_max:.1f}°C (ಗುರಿ: {temp_target:.1f}°C)\n"
                f"• ಪ್ರಸ್ತುತ ಆರ್ದ್ರತೆ: {current_hum:.0f}%\n"
                f"• ಸ್ಥಿತಿ: {headline}\n\n"
                f"⚙️ ಸಕ್ರಿಯ ನಿಯಂತ್ರಣಗಳು:\n"
                f"• ಕೂಲರ್: {cooler_str}\n"
                f"• ಎಕ್ಸಾಸ್ಟ್ ಫ್ಯಾನ್: {fan_str}\n"
                f"• ಹೀಟರ್: {heater_str}\n\n"
                f"💡 ಸೇತು ಕೈಗೊಂಡ ಕ್ರಮ: {action_expl}\n"
                f"👉 ಸೂಚನೆ: {subline}"
            )

        if lang_code == "te":
            cooler_str = "ఆన్ (ON) ❄️" if cooler_active else "ఆఫ్ (OFF)"
            fan_str = "ఆన్ (ON) 💨" if fan_active else "ఆఫ్ (OFF)"
            heater_str = "ఆన్ (ON) 🔥" if heater_active else "ఆఫ్ (OFF)"

            if cooler_active or current_temp > temp_target:
                action_expl = f"షెడ్ ఉష్ణోగ్రతను {current_temp:.1f}°C నుండి సరైన {temp_target:.1f}°C కి తగ్గించడానికి కూలర్ మరియు ఫ్యాన్ ఆన్ చేయబడ్డాయి."
            elif heater_active or current_temp < temp_target:
                action_expl = f"షెడ్ ఉష్ణోగ్రతను {current_temp:.1f}°C నుండి సరైన {temp_target:.1f}°C కి పెంచడానికి హీటర్ ఆన్ చేయబడింది."
            else:
                action_expl = f"షెడ్ ఉష్ణోగ్రతను సరైన స్థాయిలో ఉంచడానికి ఆటోమేషన్ పనిచేస్తోంది."

            return (
                f"🌾 {farmer_name} గారికి సేతు షెడ్ హెచ్చరిక\n"
                f"📍 షెడ్: {shed_id} ({farm_name})\n"
                f"⚠️ ఉష్ణోగ్రతలో తేడా గుర్తించబడింది!\n"
                f"• ప్రస్తుత ఉష్ణోగ్రత: {current_temp:.1f}°C\n"
                f"• అనుకూల పరిధి: {temp_min:.1f}°C - {temp_max:.1f}°C (లక్ష్యం: {temp_target:.1f}°C)\n"
                f"• ప్రస్తుత తేమ: {current_hum:.0f}%\n"
                f"• స్థితి: {headline}\n\n"
                f"⚙️ సిస్టమ్ కంట్రోల్స్:\n"
                f"• కూలర్: {cooler_str}\n"
                f"• ఎగ్జాస్ట్ ఫ్యాన్: {fan_str}\n"
                f"• హీటర్: {heater_str}\n\n"
                f"💡 సేతు చేపట్టిన చర్య: {action_expl}\n"
                f"👉 చర్య: {subline}"
            )

        # Default English
        cooler_str = "ON ❄️" if cooler_active else "OFF"
        fan_str = "ON 💨" if fan_active else "OFF"
        heater_str = "ON 🔥" if heater_active else "OFF"

        if cooler_active or current_temp > temp_target:
            action_expl = f"Cooling and ventilation fans are actively running to safely lower temperature from {current_temp:.1f}°C to optimal {temp_target:.1f}°C."
        elif heater_active or current_temp < temp_target:
            action_expl = f"Heating system is actively running to safely raise temperature from {current_temp:.1f}°C to optimal {temp_target:.1f}°C."
        else:
            action_expl = f"Automated climate control is actively maintaining optimal shed environment."

        return (
            f"🌾 SeriCare Alert for {farmer_name}\n"
            f"📍 Shed: {shed_id} ({farm_name})\n"
            f"⚠️ Temperature Variation Detected!\n"
            f"• Current Temp: {current_temp:.1f}°C\n"
            f"• Optimal Range: {temp_min:.1f}°C - {temp_max:.1f}°C (Target: {temp_target:.1f}°C)\n"
            f"• Current Humidity: {current_hum:.0f}%\n"
            f"• Status: {headline}\n\n"
            f"⚙️ System Controls Active:\n"
            f"• Cooler: {cooler_str}\n"
            f"• Exhaust Fan: {fan_str}\n"
            f"• Heater: {heater_str}\n\n"
            f"💡 What SeriCare Is Doing: {action_expl}\n"
            f"👉 Action: {subline}"
        )

    def build_critical_telemetry_alert(
        self,
        *,
        shed_id: str,
        temperature: float,
        humidity: float,
        status: str = "CRITICAL",
        reason: Optional[str] = None,
        lang: str = "en",
    ) -> str:
        lang_code = (lang or "en").lower()
        reason_txt = f"\nReason: {reason}" if reason else ""

        if lang_code == "kn":
            return (
                f"⚠️ ತೀವ್ರ ಎಚ್ಚರಿಕೆ - ಸೇತು ಮೈಕ್ರೋಕ್ಲೈಮೇಟ್\n"
                f"ಶೆಡ್: {shed_id}\n"
                f"ತಾಪಮಾನ: {temperature:.1f}°C\n"
                f"ಆರ್ದ್ರತೆ: {humidity:.0f}%\n"
                f"ಸ್ಥಿತಿ: {status}{reason_txt}\n"
                f"ಸೂಚನೆ: ರೇಷ್ಮೆ ಹುಳುಗಳ ಆರೋಗ್ಯ ಅಪಾಯದಲ್ಲಿದೆ! ದಯವಿಟ್ಟು ಕೂಡಲೇ ವಾತಾಯನ ಹಾಗೂ ಉಪಕರಣಗಳನ್ನು ಪರಿಶೀಲಿಸಿ."
            )

        if lang_code == "te":
            return (
                f"⚠️ అత్యవసర హెచ్చరిక - సేతు మైక్రోక్లైమేట్\n"
                f"షెడ్: {shed_id}\n"
                f"ఉష్ణోగ్రత: {temperature:.1f}°C\n"
                f"తేమ: {humidity:.0f}%\n"
                f"స్థితి: {status}{reason_txt}\n"
                f"చర్య: పట్టుపురుగుల ఆరోగ్యానికి ముప్పు ఉంది! దయచేసి వెంటనే ఫ్యాన్ లేదా వెంటిలేషన్ తనిఖీ చేయండి."
            )

        # Default English
        return (
            f"⚠️ CRITICAL ALERT - Setu Microclimate\n"
            f"Shed: {shed_id}\n"
            f"Temperature: {temperature:.1f}°C\n"
            f"Humidity: {humidity:.0f}%\n"
            f"Status: {status}{reason_txt}\n"
            f"Action: Silkworm health is at risk! Please check ventilation, cooling, or heating immediately."
        )

    def send(
        self,
        *,
        message: Optional[str] = None,
        recipient: Optional[str] = None,
        dry_run: bool = False,
        media_url: Optional[str] = None,
        cooldown_key: Optional[str] = None,
        cooldown_seconds: int = 0,
    ) -> Dict[str, Any]:
        target = self.normalize_whatsapp(recipient or self.default_to)
        if not target:
            return {
                "status": "disabled",
                "message": "No WhatsApp recipient configured. Set TWILIO_WHATSAPP_TO or pass a recipient.",
                "recipient": None,
            }

        # Check cooldown
        if cooldown_key and not self.check_and_update_cooldown(cooldown_key, cooldown_seconds):
            return {
                "status": "throttled",
                "message": f"Alert suppressed by cooldown ({cooldown_seconds}s).",
                "recipient": target,
                "preview": message,
            }

        if not self.is_configured:
            if dry_run:
                return {
                    "status": "dry-run",
                    "message": f"Setu dry run: would send to {target} -> {message or media_url}",
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
                "message": f"Setu dry run: would send to {target} -> {message or media_url}",
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
                "from_": self.normalize_whatsapp(self.from_number),
                "to": target,
            }
            if message:
                payload["body"] = message
            if media_url:
                payload["media_url"] = [media_url] if isinstance(media_url, str) else media_url

            twilio_message = self._client.messages.create(**payload)
            return {
                "status": "sent",
                "message": "WhatsApp message sent successfully.",
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

    def dispatch_in_background(
        self,
        *,
        message: Optional[str] = None,
        recipient: Optional[str] = None,
        dry_run: bool = False,
        media_url: Optional[str] = None,
        voice_url: Optional[str] = None,
        cooldown_key: Optional[str] = None,
        cooldown_seconds: int = 0,
    ) -> None:
        """Dispatches an alert in a background worker thread.
        If voice_url is provided, delivers the formatted text alert followed by the voice note audio message."""
        if cooldown_key and not self.check_and_update_cooldown(cooldown_key, cooldown_seconds):
            logger.info("Alert throttled by cooldown: %s", cooldown_key)
            return

        def _worker():
            try:
                # 1. Send text message (if present)
                if message:
                    res = self.send(
                        message=message,
                        recipient=recipient,
                        dry_run=dry_run,
                        media_url=media_url if not voice_url else None,
                        cooldown_key=None,
                        cooldown_seconds=0,
                    )
                    if res.get("status") == "error":
                        logger.error("WhatsApp dispatch failed: %s (Recipient: %s)", res.get("message"), res.get("recipient"))
                        if cooldown_key:
                            self.rollback_cooldown(cooldown_key)
                        return
                    elif res.get("status") == "sent":
                        logger.info("WhatsApp alert delivered to %s (SID: %s)", res.get("recipient"), res.get("sid"))

                # 2. If voice_url is present, send voice note audio message
                if voice_url:
                    time.sleep(1.0)
                    voice_res = self.send(
                        message=None,
                        media_url=voice_url,
                        recipient=recipient,
                        dry_run=dry_run,
                        cooldown_key=None,
                        cooldown_seconds=0,
                    )
                    if voice_res.get("status") == "sent":
                        logger.info("WhatsApp voice note delivered to %s (SID: %s)", voice_res.get("recipient"), voice_res.get("sid"))
                    else:
                        logger.warning("WhatsApp voice note dispatch status: %s (%s)", voice_res.get("status"), voice_res.get("message"))
            except Exception as e:
                logger.error("Background WhatsApp send crashed: %s", e)
                if cooldown_key:
                    self.rollback_cooldown(cooldown_key)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    # Alias for explicit clarity
    dispatch_alert_with_voice = dispatch_in_background


alert_service = WhatsAppAlertService()
