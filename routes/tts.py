import io
import os
import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

# Pydantic model for TTS requests
class TTSRequest(BaseModel):
    text: str

# Use environment variables or replace with your keys for local testing
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "YOUR_ELEVENLABS_API_KEY_HERE")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "YOUR_VOICE_ID_HERE")

@router.post("/tts_stream", tags=["TTS"])
async def text_to_speech_stream(req: TTSRequest):
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=500, detail="ElevenLabs API key not configured.")
    if not ELEVENLABS_VOICE_ID:
        raise HTTPException(status_code=500, detail="ElevenLabs voice ID not configured.")

    # The streaming endpoint from ElevenLabs – check docs to confirm URL
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": req.text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }

    response = requests.post(url, headers=headers, json=payload, stream=True)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"ElevenLabs TTS streaming failed: {response.text}")

    # Stream audio in chunks (adjust chunk size as needed)
    def iterfile():
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                yield chunk

    return StreamingResponse(iterfile(), media_type="audio/mpeg")
