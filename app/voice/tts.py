"""Text-to-Speech service with multiple provider support.

Supports:
- ElevenLabs (primary) — best naturalness
- Azure Neural TTS (fallback) — reliability
- Deepgram Aura (future) — cost-effective

Includes phrase caching to reduce latency for repeated phrases.
"""

import hashlib
import logging
import os
from typing import Optional, Literal
from functools import lru_cache

import httpx

logger = logging.getLogger(__name__)

# Voice IDs
VOICES = {
    "elevenlabs": {
        "female_warm": "21m00Tcm4TlvDq8ikWAM",  # Rachel — warm, friendly
        "male_professional": "pNInz6obpgDQGcFmaJgB",  # Adam — professional
        "female_professional": "EXAVITQu4vr4xnSDxMaL",  # Bella — clear, professional
    },
    "azure": {
        "female_warm": "en-US-JennyNeural",
        "male_professional": "en-US-GuyNeural",
        "female_professional": "en-US-AriaNeural",
    }
}

# Cache for repeated phrases (in-memory for now, could be Redis later)
_audio_cache: dict[str, bytes] = {}


def _cache_key(text: str, voice_id: str, provider: str) -> str:
    """Generate cache key for a phrase."""
    content = f"{provider}:{voice_id}:{text}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


async def speak(
    text: str,
    voice: Literal["female_warm", "male_professional", "female_professional"] = "female_warm",
    provider: Literal["elevenlabs", "azure", "auto"] = "auto",
    cache: bool = True,
    emotion: Optional[dict] = None,
) -> bytes:
    """Convert text to speech audio.

    Args:
        text: Text to convert to speech
        voice: Voice type (female_warm, male_professional, female_professional)
        provider: TTS provider to use (auto tries elevenlabs then azure)
        cache: Whether to use cached audio for repeated phrases
        emotion: Emotion settings (stability, similarity for elevenlabs)

    Returns:
        Audio bytes (MP3 format)

    Raises:
        ValueError: If all providers fail
    """
    if not text.strip():
        raise ValueError("Text cannot be empty")

    # Default emotion settings (warm and friendly)
    if emotion is None:
        emotion = {
            "stability": 0.5,  # Medium stability (not too robotic, not too varied)
            "similarity_boost": 0.75,  # High similarity to original voice
            "style": 0.3,  # Slight style exaggeration for warmth
        }

    # Check cache first
    if cache:
        providers_to_try = ["elevenlabs", "azure"] if provider == "auto" else [provider]
        for p in providers_to_try:
            voice_id = VOICES[p][voice]
            key = _cache_key(text, voice_id, p)
            if key in _audio_cache:
                logger.info("Cache hit for '%s' (%s)", text[:50], p)
                return _audio_cache[key]

    # Try providers
    if provider == "auto":
        # Try elevenlabs first, fall back to azure
        try:
            audio = await _elevenlabs_tts(text, VOICES["elevenlabs"][voice], emotion)
            logger.info("ElevenLabs TTS success: %d bytes", len(audio))
            if cache:
                _audio_cache[_cache_key(text, VOICES["elevenlabs"][voice], "elevenlabs")] = audio
            return audio
        except Exception as e:
            logger.warning("ElevenLabs TTS failed: %s, falling back to Azure", e)
            try:
                audio = await _azure_tts(text, VOICES["azure"][voice])
                logger.info("Azure TTS success (fallback): %d bytes", len(audio))
                if cache:
                    _audio_cache[_cache_key(text, VOICES["azure"][voice], "azure")] = audio
                return audio
            except Exception as e2:
                logger.error("Azure TTS also failed: %s", e2)
                raise ValueError(f"All TTS providers failed. ElevenLabs: {e}, Azure: {e2}")

    elif provider == "elevenlabs":
        audio = await _elevenlabs_tts(text, VOICES["elevenlabs"][voice], emotion)
        if cache:
            _audio_cache[_cache_key(text, VOICES["elevenlabs"][voice], "elevenlabs")] = audio
        return audio

    elif provider == "azure":
        audio = await _azure_tts(text, VOICES["azure"][voice])
        if cache:
            _audio_cache[_cache_key(text, VOICES["azure"][voice], "azure")] = audio
        return audio

    else:
        raise ValueError(f"Unknown provider: {provider}")


async def _elevenlabs_tts(text: str, voice_id: str, emotion: dict) -> bytes:
    """ElevenLabs TTS implementation."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not set in environment")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2",  # Fastest model (200-400ms latency)
        "voice_settings": {
            "stability": emotion.get("stability", 0.5),
            "similarity_boost": emotion.get("similarity_boost", 0.75),
            "style": emotion.get("style", 0.0),
            "use_speaker_boost": True,
        }
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.content


async def _azure_tts(text: str, voice_name: str) -> bytes:
    """Azure Neural TTS implementation."""
    # Azure TTS uses SSML for better control
    ssml = f"""
    <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>
        <voice name='{voice_name}'>
            <prosody rate='1.0' pitch='0%'>
                {text}
            </prosody>
        </voice>
    </speak>
    """

    api_key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION", "eastus")
    
    if not api_key:
        raise ValueError("AZURE_SPEECH_KEY not set in environment")

    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": api_key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, content=ssml, headers=headers)
        resp.raise_for_status()
        return resp.content


def clear_cache():
    """Clear the audio cache."""
    _audio_cache.clear()
    logger.info("Audio cache cleared")


def cache_common_phrases(phrases: dict[str, str]):
    """Pre-cache common phrases to reduce latency.

    Args:
        phrases: Dict of {phrase_name: text} to cache
    
    Example:
        cache_common_phrases({
            "greeting": "Hey there, thanks for calling! How can I help you today?",
            "hold": "Sure, give me just a moment.",
            "closing": "Thanks for calling! Have a great day."
        })
    """
    import asyncio
    
    async def _cache_all():
        for name, text in phrases.items():
            try:
                # Cache with default voice
                audio = await speak(text, voice="female_warm", provider="auto", cache=True)
                logger.info("Cached phrase '%s': %d bytes", name, len(audio))
            except Exception as e:
                logger.error("Failed to cache phrase '%s': %s", name, e)
    
    asyncio.run(_cache_all())
