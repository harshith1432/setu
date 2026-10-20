import base64
import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache directory for voice notes
VOICE_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "voice_cache"
VOICE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class VoiceAlertService:
    """Generates localized Text-to-Speech audio voice notes for WhatsApp alerts."""

    def __init__(self):
        self.cache_dir = VOICE_CACHE_DIR

    @staticmethod
    def build_voice_script(
        *,
        farmer_name: str,
        shed_id: str,
        current_temp: float,
        temp_target: float,
        is_cooler_on: bool = False,
        is_heater_on: bool = False,
        is_fan_on: bool = False,
        lang: str = "en",
    ) -> str:
        """Builds a concise, natural voice note spoken script in farmer's preferred language."""
        lang_code = (lang or "en").lower()

        if lang_code == "kn":
            if is_cooler_on or current_temp > temp_target:
                action_text = "ತಾಪಮಾನವನ್ನು ಇಳಿಸಲು ಕೂಲರ್ ಮತ್ತು ಫ್ಯಾನ್ ಚಾಲನೆ ಮಾಡಲಾಗುತ್ತಿದೆ."
            elif is_heater_on or current_temp < temp_target:
                action_text = "ತಾಪಮಾನವನ್ನು ಹೆಚ್ಚಿಸಲು ಹೀಟರ್ ಚಾಲನೆ ಮಾಡಲಾಗುತ್ತಿದೆ."
            else:
                action_text = "ತಾಪಮಾನವನ್ನು ಸಮತೋಲನದಲ್ಲಿಡಲು ವಾತಾಯನ ನಿಯಂತ್ರಣ ಕಾರ್ಯನಿರ್ವಹಿಸುತ್ತಿದೆ."

            return (
                f"{farmer_name} ಅವರಿಗೆ ಸೇತು ಎಚ್ಚರಿಕೆ. "
                f"ಶೆಡ್ {shed_id} ನಲ್ಲಿ ತಾಪಮಾನ ವ್ಯತ್ಯಾಸವಾಗಿದೆ. "
                f"ಪ್ರಸ್ತುತ ತಾಪಮಾನ {current_temp:.1f} ಡಿಗ್ರಿ ಸೆಲ್ಸಿಯಸ್ ಇದೆ. "
                f"{action_text}"
            )

        if lang_code == "te":
            if is_cooler_on or current_temp > temp_target:
                action_text = "ఉష్ణోగ్రతను తగ్గించడానికి కూలర్ మరియు ఫ్యాన్ ఆన్ చేయబడ్డాయి."
            elif is_heater_on or current_temp < temp_target:
                action_text = "ఉష్ణోగ్రతను పెంచడానికి హీటర్ ఆన్ చేయబడింది."
            else:
                action_text = "వాతావరణాన్ని నియంత్రించడానికి ఆటోమేషన్ పనిచేస్తోంది."

            return (
                f"{farmer_name} గారికి సేతు హెచ్చరిక. "
                f"షెడ్ {shed_id} లో ఉష్ణోగ్రత తేడా వచ్చింది. "
                f"ప్రస్తుత ఉష్ణోగ్రత {current_temp:.1f} డిగ్రీలు ఉంది. "
                f"{action_text}"
            )

        # Default English
        if is_cooler_on or current_temp > temp_target:
            action_text = f"Cooling and exhaust fans are running to bring temperature down to {temp_target:.1f} degrees."
        elif is_heater_on or current_temp < temp_target:
            action_text = f"Heating system is running to bring temperature up to {temp_target:.1f} degrees."
        else:
            action_text = "Automated ventilation is actively regulating the shed microclimate."

        return (
            f"SeriCare alert for {farmer_name}. "
            f"Temperature variation in shed {shed_id}. "
            f"Current temperature is {current_temp:.1f} degrees Celsius. "
            f"{action_text}"
        )

    def generate_audio_file(self, text: str, lang: str = "en") -> Optional[Path]:
        """Generates an MP3 file using gTTS and caches it on disk."""
        if not text:
            return None

        # Clean language code for gTTS
        lang_code = (lang or "en").lower()
        if lang_code not in ["kn", "te", "en", "hi"]:
            lang_code = "en"

        text_hash = hashlib.md5(f"{lang_code}:{text}".encode("utf-8")).hexdigest()
        output_file = self.cache_dir / f"{text_hash}.mp3"

        if output_file.exists() and output_file.stat().st_size > 0:
            return output_file

        if gTTS is None:
            logger.warning("gTTS not installed, cannot generate audio.")
            return None

        try:
            tts = gTTS(text=text, lang=lang_code, slow=False)
            tts.save(str(output_file))
            self._cleanup_old_files()
            return output_file
        except Exception as e:
            logger.error("Failed to generate voice note audio with gTTS: %s", e)
            return None

    def get_voice_url_for_text(self, text: str, lang: str = "en") -> str:
        """Returns a public URL pointing to the voice audio. 
        Uses a stateless token containing base64url(json({text, lang}))
        so that any backend worker or Render instance can serve it immediately."""
        lang_code = (lang or "en").lower()
        payload = json.dumps({"text": text, "lang": lang_code}, separators=(",", ":")).encode("utf-8")
        token = base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")

        server_base = (
            getattr(settings, "SERVER_PUBLIC_URL", "")
            or os.getenv("RENDER_EXTERNAL_URL", "")
            or "https://setu-8vh9.onrender.com"
        ).rstrip("/")

        return f"{server_base}/api/v1/voice/{token}.mp3"

    def _cleanup_old_files(self, max_age_seconds: int = 86400):
        """Removes cached voice audio files older than 24 hours."""
        now = time.time()
        try:
            for file in self.cache_dir.glob("*.mp3"):
                if now - file.stat().st_mtime > max_age_seconds:
                    file.unlink(missing_ok=True)
        except Exception:
            pass


voice_service = VoiceAlertService()
