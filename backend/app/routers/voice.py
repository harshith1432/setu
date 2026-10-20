import base64
import json
import logging
import os
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.voice_service import voice_service, VOICE_CACHE_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice Alerts"])


class VoicePreviewRequest(BaseModel):
    text: str
    lang: str = "en"


@router.get("/{token_or_filename}")
async def get_voice_note(token_or_filename: str):
    """Stateless & cached audio endpoint.
    Decodes the base64url token or serves pre-cached audio file so Twilio WhatsApp can play voice notes."""
    # Sanitize against path injection
    clean_val = token_or_filename.strip()
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", clean_val) or ".." in clean_val or "/" in clean_val or "\\" in clean_val:
        raise HTTPException(status_code=400, detail="Invalid audio identifier")
    safe_filename = os.path.basename(clean_val)

    # 1. Direct file lookup in cache directory with path containment check
    resolved_cache = VOICE_CACHE_DIR.resolve()
    direct_path = (resolved_cache / safe_filename).resolve()
    try:
        direct_path.relative_to(resolved_cache)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid audio path")

    if direct_path.exists() and direct_path.is_file():
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

    audio_file = voice_service.generate_audio_file(text=text, lang=lang)
    if not audio_file or not audio_file.exists():
        raise HTTPException(status_code=500, detail="Failed to synthesize voice note")

    media_type = "audio/ogg" if safe_filename.endswith(".ogg") else "audio/mpeg"
    return FileResponse(str(audio_file), media_type=media_type, headers={"Accept-Ranges": "bytes"})


@router.post("/preview")
async def preview_voice_note(payload: VoicePreviewRequest):
    """Generates a preview voice note and returns its public URL and local file info."""
    voice_url = voice_service.get_voice_url_for_text(text=payload.text, lang=payload.lang)
    audio_path = voice_service.generate_audio_file(text=payload.text, lang=payload.lang)
    return {
        "status": "success",
        "voice_url": voice_url,
        "file_ready": bool(audio_path and audio_path.exists()),
        "text": payload.text,
        "lang": payload.lang,
    }
