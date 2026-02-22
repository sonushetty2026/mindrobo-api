"""Speech-to-Text service with multiple provider support.

Supports:
- Deepgram Nova-2 (primary) — fast streaming STT
- OpenAI Whisper (secondary) — high-accuracy batch transcription

For real-time streaming, use Deepgram.
For post-call high-accuracy transcripts, use Whisper.
"""

import logging
import os
from typing import Optional, Literal
import httpx

logger = logging.getLogger(__name__)


async def transcribe(
    audio_bytes: bytes,
    provider: Literal["deepgram", "whisper", "auto"] = "auto",
    language: str = "en",
    model: Optional[str] = None,
) -> dict:
    """Transcribe audio to text.

    Args:
        audio_bytes: Raw audio bytes (WAV, MP3, etc.)
        provider: STT provider to use (auto tries deepgram then whisper)
        language: Language code (e.g. 'en', 'es', 'fr')
        model: Specific model to use (provider-specific)

    Returns:
        {
            "text": str,           # Transcribed text
            "confidence": float,   # Confidence score (0-1)
            "words": list,         # Word-level timestamps (optional)
            "provider": str,       # Provider used
        }

    Raises:
        ValueError: If all providers fail
    """
    if not audio_bytes:
        raise ValueError("Audio bytes cannot be empty")

    if len(audio_bytes) > 25 * 1024 * 1024:  # 25MB limit
        raise ValueError("Audio file too large (max 25MB)")

    # Try providers
    if provider == "auto":
        # Try deepgram first (faster), fall back to whisper
        try:
            result = await _deepgram_stt(audio_bytes, language, model)
            logger.info("Deepgram STT success: '%s...'", result["text"][:50])
            return result
        except Exception as e:
            logger.warning("Deepgram STT failed: %s, falling back to Whisper", e)
            try:
                result = await _whisper_stt(audio_bytes, language)
                logger.info("Whisper STT success (fallback): '%s...'", result["text"][:50])
                return result
            except Exception as e2:
                logger.error("Whisper STT also failed: %s", e2)
                raise ValueError(f"All STT providers failed. Deepgram: {e}, Whisper: {e2}")

    elif provider == "deepgram":
        return await _deepgram_stt(audio_bytes, language, model)

    elif provider == "whisper":
        return await _whisper_stt(audio_bytes, language)

    else:
        raise ValueError(f"Unknown provider: {provider}")


async def _deepgram_stt(
    audio_bytes: bytes,
    language: str = "en",
    model: Optional[str] = None
) -> dict:
    """Deepgram Nova-2 STT implementation (batch transcription).

    For streaming, use the Deepgram SDK with WebSocket.
    """
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        raise ValueError("DEEPGRAM_API_KEY not set in environment")

    model = model or "nova-2"
    url = "https://api.deepgram.com/v1/listen"
    params = {
        "model": model,
        "language": language,
        "punctuate": "true",
        "utterances": "true",
        "diarize": "false",  # Set to true for multi-speaker
    }
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "audio/wav",  # Deepgram auto-detects format
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, content=audio_bytes, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

    # Extract transcript and metadata
    results = data.get("results", {})
    channels = results.get("channels", [])
    if not channels:
        raise ValueError("No transcription results from Deepgram")

    alternatives = channels[0].get("alternatives", [])
    if not alternatives:
        raise ValueError("No alternatives in Deepgram response")

    best = alternatives[0]
    text = best.get("transcript", "")
    confidence = best.get("confidence", 0.0)
    words = best.get("words", [])

    return {
        "text": text.strip(),
        "confidence": confidence,
        "words": words,  # List of {word, start, end, confidence}
        "provider": "deepgram",
        "model": model,
    }


async def _whisper_stt(audio_bytes: bytes, language: str = "en") -> dict:
    """OpenAI Whisper STT implementation (batch transcription)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in environment")

    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    
    # Whisper requires multipart/form-data
    files = {
        "file": ("audio.wav", audio_bytes, "audio/wav"),
    }
    data = {
        "model": "whisper-1",
        "language": language,
        "response_format": "verbose_json",  # Get word-level timestamps
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, files=files, data=data, headers=headers)
        resp.raise_for_status()
        result = resp.json()

    text = result.get("text", "")
    # Whisper doesn't provide overall confidence, but we can estimate from word-level
    segments = result.get("segments", [])
    words = []
    total_confidence = 0.0
    word_count = 0
    
    for segment in segments:
        for word_info in segment.get("words", []):
            words.append({
                "word": word_info.get("word", ""),
                "start": word_info.get("start", 0.0),
                "end": word_info.get("end", 0.0),
                "confidence": 1.0,  # Whisper doesn't provide word confidence
            })
            total_confidence += 1.0
            word_count += 1

    avg_confidence = total_confidence / word_count if word_count > 0 else 0.95

    return {
        "text": text.strip(),
        "confidence": avg_confidence,
        "words": words,
        "provider": "whisper",
        "model": "whisper-1",
        "language": result.get("language", language),
    }


# Streaming STT (for real-time calls)
class DeepgramStreamSTT:
    """Real-time streaming STT using Deepgram WebSocket.
    
    Use this for live phone calls where you need immediate transcription.
    
    Example:
        stream = DeepgramStreamSTT()
        await stream.connect()
        
        # Send audio chunks as they arrive
        await stream.send_audio(audio_chunk_1)
        await stream.send_audio(audio_chunk_2)
        
        # Get transcripts via callback
        def on_transcript(transcript):
            print(f"Caller said: {transcript}")
        
        stream.on_transcript = on_transcript
        await stream.close()
    """
    
    def __init__(self, language: str = "en", model: str = "nova-2"):
        self.language = language
        self.model = model
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        self.ws = None
        self.on_transcript = None  # Callback function
        
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY not set in environment")
    
    async def connect(self):
        """Connect to Deepgram WebSocket for streaming."""
        # This would use websockets library in practice
        # For now, just document the interface
        logger.info("DeepgramStreamSTT.connect() — requires websockets library")
        raise NotImplementedError(
            "Streaming STT requires websockets library. "
            "Install with: pip install websockets deepgram-sdk"
        )
    
    async def send_audio(self, audio_chunk: bytes):
        """Send audio chunk to Deepgram for real-time transcription."""
        raise NotImplementedError("Use deepgram-sdk for streaming")
    
    async def close(self):
        """Close the WebSocket connection."""
        raise NotImplementedError("Use deepgram-sdk for streaming")


# Helper: transcribe from file path
async def transcribe_file(
    file_path: str,
    provider: Literal["deepgram", "whisper", "auto"] = "auto",
    language: str = "en",
) -> dict:
    """Transcribe audio file to text.

    Args:
        file_path: Path to audio file (WAV, MP3, etc.)
        provider: STT provider to use
        language: Language code

    Returns:
        Transcription dict (same as transcribe())
    """
    with open(file_path, "rb") as f:
        audio_bytes = f.read()
    
    return await transcribe(audio_bytes, provider=provider, language=language)
