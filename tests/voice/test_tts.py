"""Tests for Text-to-Speech service."""

import pytest
from unittest.mock import patch, AsyncMock
from app.voice.tts import speak, clear_cache, _cache_key


@pytest.fixture
def mock_elevenlabs_response():
    """Mock successful ElevenLabs API response."""
    return b"fake_mp3_audio_data_elevenlabs"


@pytest.fixture
def mock_azure_response():
    """Mock successful Azure TTS API response."""
    return b"fake_mp3_audio_data_azure"


@pytest.mark.asyncio
async def test_speak_elevenlabs_success(mock_elevenlabs_response):
    """Test TTS with ElevenLabs (success case)."""
    with patch("app.voice.tts._elevenlabs_tts", new=AsyncMock(return_value=mock_elevenlabs_response)):
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test_key"}):
            audio = await speak("Hello world", provider="elevenlabs")
            
            assert audio == mock_elevenlabs_response
            assert len(audio) > 0


@pytest.mark.asyncio
async def test_speak_azure_success(mock_azure_response):
    """Test TTS with Azure (success case)."""
    with patch("app.voice.tts._azure_tts", new=AsyncMock(return_value=mock_azure_response)):
        with patch.dict("os.environ", {"AZURE_SPEECH_KEY": "test_key", "AZURE_SPEECH_REGION": "eastus"}):
            audio = await speak("Hello world", provider="azure")
            
            assert audio == mock_azure_response
            assert len(audio) > 0


@pytest.mark.asyncio
async def test_speak_auto_fallback(mock_elevenlabs_response, mock_azure_response):
    """Test auto provider with fallback from ElevenLabs to Azure."""
    async def elevenlabs_fail(*args, **kwargs):
        raise ValueError("ElevenLabs API key missing")
    
    with patch("app.voice.tts._elevenlabs_tts", new=AsyncMock(side_effect=elevenlabs_fail)):
        with patch("app.voice.tts._azure_tts", new=AsyncMock(return_value=mock_azure_response)):
            with patch.dict("os.environ", {"AZURE_SPEECH_KEY": "test_key"}):
                audio = await speak("Hello world", provider="auto")
                
                # Should fall back to Azure
                assert audio == mock_azure_response


@pytest.mark.asyncio
async def test_speak_cache_hit(mock_elevenlabs_response):
    """Test that repeated phrases return cached audio."""
    clear_cache()  # Start fresh
    
    call_count = 0
    
    async def mock_tts(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_elevenlabs_response
    
    with patch("app.voice.tts._elevenlabs_tts", new=AsyncMock(side_effect=mock_tts)):
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test_key"}):
            # First call — should hit API
            audio1 = await speak("Hello world", provider="elevenlabs", cache=True)
            assert call_count == 1
            
            # Second call — should hit cache
            audio2 = await speak("Hello world", provider="elevenlabs", cache=True)
            assert call_count == 1  # No additional API call
            
            assert audio1 == audio2


@pytest.mark.asyncio
async def test_speak_cache_disabled(mock_elevenlabs_response):
    """Test that cache=False always calls API."""
    clear_cache()
    
    call_count = 0
    
    async def mock_tts(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_elevenlabs_response
    
    with patch("app.voice.tts._elevenlabs_tts", new=AsyncMock(side_effect=mock_tts)):
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test_key"}):
            # First call
            await speak("Hello world", provider="elevenlabs", cache=False)
            assert call_count == 1
            
            # Second call — should NOT use cache
            await speak("Hello world", provider="elevenlabs", cache=False)
            assert call_count == 2


@pytest.mark.asyncio
async def test_speak_empty_text():
    """Test that empty text raises ValueError."""
    with pytest.raises(ValueError, match="Text cannot be empty"):
        await speak("")


@pytest.mark.asyncio
async def test_speak_different_voices(mock_elevenlabs_response):
    """Test that different voices are handled correctly."""
    with patch("app.voice.tts._elevenlabs_tts", new=AsyncMock(return_value=mock_elevenlabs_response)):
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test_key"}):
            audio1 = await speak("Hello", voice="female_warm", provider="elevenlabs")
            audio2 = await speak("Hello", voice="male_professional", provider="elevenlabs")
            
            # Both should succeed
            assert len(audio1) > 0
            assert len(audio2) > 0


@pytest.mark.asyncio
async def test_speak_emotion_control(mock_elevenlabs_response):
    """Test that emotion parameters are passed correctly."""
    captured_emotion = None
    
    async def mock_tts(text, voice_id, emotion):
        nonlocal captured_emotion
        captured_emotion = emotion
        return mock_elevenlabs_response
    
    with patch("app.voice.tts._elevenlabs_tts", new=AsyncMock(side_effect=mock_tts)):
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test_key"}):
            custom_emotion = {
                "stability": 0.8,
                "similarity_boost": 0.9,
                "style": 0.5,
            }
            await speak("Hello", provider="elevenlabs", emotion=custom_emotion)
            
            # Check that custom emotion was passed through
            assert captured_emotion == custom_emotion


@pytest.mark.asyncio
async def test_speak_all_providers_fail():
    """Test that ValueError is raised when all providers fail."""
    async def fail(*args, **kwargs):
        raise ValueError("API failed")
    
    with patch("app.voice.tts._elevenlabs_tts", new=AsyncMock(side_effect=fail)):
        with patch("app.voice.tts._azure_tts", new=AsyncMock(side_effect=fail)):
            with pytest.raises(ValueError, match="All TTS providers failed"):
                await speak("Hello", provider="auto")


def test_cache_key_generation():
    """Test that cache keys are generated correctly."""
    key1 = _cache_key("Hello world", "voice_123", "elevenlabs")
    key2 = _cache_key("Hello world", "voice_123", "elevenlabs")
    key3 = _cache_key("Hello world", "voice_456", "elevenlabs")
    key4 = _cache_key("Goodbye", "voice_123", "elevenlabs")
    
    # Same inputs should produce same key
    assert key1 == key2
    
    # Different inputs should produce different keys
    assert key1 != key3
    assert key1 != key4


def test_clear_cache():
    """Test that clear_cache removes all cached items."""
    from app.voice.tts import _audio_cache
    
    # Add some fake cache entries
    _audio_cache["key1"] = b"audio1"
    _audio_cache["key2"] = b"audio2"
    
    assert len(_audio_cache) == 2
    
    clear_cache()
    
    assert len(_audio_cache) == 0
