import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Security, Request, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.services.voice_service import voice_service, VOICE_CACHE_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice Alerts"])
security_optional = HTTPBearer(auto_error=False)

ALLOWED_LANGS = {"en", "kn", "te", "hi", "ta", "mr"}


class VoicePreviewRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500, description="Voice note text (max 500 characters to prevent resource exhaustion)")
    lang: str = Field("en", pattern="^(en|kn|te|hi|ta|mr)$", description="Supported language code")
    language: Optional[str] = Field(None, pattern="^(en|kn|te|hi|ta|mr)$", description="Optional language parameter")


@router.get("/{token_or_filename}")
async def get_voice_note(token_or_filename: str):
    """Stateless & cached audio endpoint.
    Decodes the base64url token or serves pre-cached audio file so Twilio WhatsApp can play voice notes."""
    # Sanitize against path injection (OWASP A05 / ASVS V5.3)
    clean_val = token_or_filename.strip()
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", clean_val) or ".." in clean_val or "/" in clean_val or "\\" in clean_val:
        raise HTTPException(status_code=400, detail="Invalid audio identifier")
    safe_filename = os.path.basename(clean_val)

    # 1. Direct file lookup in cache directory using dictionary lookup against existing files
    cached_files = {f.name: f for f in VOICE_CACHE_DIR.iterdir() if f.is_file()}
    if safe_filename in cached_files:
        direct_path = cached_files[safe_filename]
        media_type = "audio/ogg" if safe_filename.endswith(".ogg") else "audio/mpeg"
        return FileResponse(str(direct_path), media_type=media_type, headers={"Accept-Ranges": "bytes"})

    # 2. Extract token by stripping extension (.mp3 / .ogg)
    token = safe_filename
    for ext in [".mp3", ".ogg", ".wav"]:
        if token.endswith(ext):
            token = token[:-len(ext)]
            break

    # Fix base64 padding if needed
    padded_token = token + "=" * (-len(token) % 4)

    try:
        decoded_bytes = base64.urlsafe_b64decode(padded_token.encode("utf-8"))
        data = json.loads(decoded_bytes.decode("utf-8"))
        text = data.get("text", "")
        lang = data.get("lang", "en")
    except Exception as e:
        logger.warning("Could not decode voice note token: %s", e)
        raise HTTPException(status_code=404, detail="Invalid voice token or audio not found")

    if not text:
        raise HTTPException(status_code=400, detail="Empty text in voice token")

    # Guard against resource exhaustion via unbounded synthetic audio generation
    if len(text) > 500:
        raise HTTPException(status_code=400, detail="Voice note text exceeds 500 character limit")

    if lang not in ALLOWED_LANGS:
        lang = "en"

    audio_file = voice_service.generate_audio_file(text=text, lang=lang)
    if not audio_file or not audio_file.exists():
        raise HTTPException(status_code=500, detail="Failed to synthesize voice note")

    media_type = "audio/ogg" if safe_filename.endswith(".ogg") else "audio/mpeg"
    return FileResponse(str(audio_file), media_type=media_type, headers={"Accept-Ranges": "bytes"})


@router.post("/preview")
async def preview_voice_note(
    payload: VoicePreviewRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_optional)
):
    """
    Generates a preview voice note and returns its public URL and local file info.
    Payload strictly bounded to 500 chars to prevent compute exhaustion (ASVS V5.1).
    """
    selected_lang = payload.language or payload.lang
    voice_url = voice_service.get_voice_url_for_text(text=payload.text, lang=selected_lang)
    audio_path = voice_service.generate_audio_file(text=payload.text, lang=selected_lang)
    return {
        "status": "success",
        "voice_url": voice_url,
        "file_ready": bool(audio_path and audio_path.exists()),
        "text": payload.text,
        "lang": payload.lang,
    }
