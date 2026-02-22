"""Tests for Speech-to-Text service."""

import pytest
from unittest.mock import patch, AsyncMock
from app.voice.stt import transcribe, transcribe_file


@pytest.fixture
def fake_audio_bytes():
    """Fake audio data for testing."""
    return b"fake_wav_audio_data_12345"


@pytest.fixture
def mock_deepgram_response():
    """Mock Deepgram API response."""
    return {
        "results": {
            "channels": [
                {
                    "alternatives": [
                        {
                            "transcript": "Hello, how can I help you today?",
                            "confidence": 0.95,
                            "words": [
                                {"word": "Hello", "start": 0.0, "end": 0.5, "confidence": 0.98},
                                {"word": "how", "start": 0.6, "end": 0.8, "confidence": 0.96},
                                {"word": "can", "start": 0.9, "end": 1.1, "confidence": 0.94},
                                {"word": "I", "start": 1.2, "end": 1.3, "confidence": 0.92},
                                {"word": "help", "start": 1.4, "end": 1.7, "confidence": 0.95},
                                {"word": "you", "start": 1.8, "end": 2.0, "confidence": 0.97},
                                {"word": "today", "start": 2.1, "end": 2.5, "confidence": 0.93},
                            ]
                        }
                    ]
                }
            ]
        }
    }


@pytest.fixture
def mock_whisper_response():
    """Mock Whisper API response."""
    return {
        "text": "Hello, how can I help you today?",
        "language": "en",
        "segments": [
            {
                "words": [
                    {"word": "Hello", "start": 0.0, "end": 0.5},
                    {"word": "how", "start": 0.6, "end": 0.8},
                    {"word": "can", "start": 0.9, "end": 1.1},
                    {"word": "I", "start": 1.2, "end": 1.3},
                    {"word": "help", "start": 1.4, "end": 1.7},
                    {"word": "you", "start": 1.8, "end": 2.0},
                    {"word": "today", "start": 2.1, "end": 2.5},
                ]
            }
        ]
    }


@pytest.mark.asyncio
async def test_transcribe_deepgram_success(fake_audio_bytes, mock_deepgram_response):
    """Test STT with Deepgram (success case)."""
    with patch("app.voice.stt._deepgram_stt", new=AsyncMock(return_value={
        "text": "Hello, how can I help you today?",
        "confidence": 0.95,
        "words": mock_deepgram_response["results"]["channels"][0]["alternatives"][0]["words"],
        "provider": "deepgram",
        "model": "nova-2",
    })):
        with patch.dict("os.environ", {"DEEPGRAM_API_KEY": "test_key"}):
            result = await transcribe(fake_audio_bytes, provider="deepgram")
            
            assert result["text"] == "Hello, how can I help you today?"
            assert result["confidence"] > 0.9
            assert result["provider"] == "deepgram"
            assert len(result["words"]) == 7


@pytest.mark.asyncio
async def test_transcribe_whisper_success(fake_audio_bytes, mock_whisper_response):
    """Test STT with Whisper (success case)."""
    with patch("app.voice.stt._whisper_stt", new=AsyncMock(return_value={
        "text": "Hello, how can I help you today?",
        "confidence": 0.95,
        "words": mock_whisper_response["segments"][0]["words"],
        "provider": "whisper",
        "model": "whisper-1",
        "language": "en",
    })):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
            result = await transcribe(fake_audio_bytes, provider="whisper")
            
            assert result["text"] == "Hello, how can I help you today?"
            assert result["provider"] == "whisper"
            assert "language" in result


@pytest.mark.asyncio
async def test_transcribe_auto_fallback(fake_audio_bytes, mock_whisper_response):
    """Test auto provider with fallback from Deepgram to Whisper."""
    async def deepgram_fail(*args, **kwargs):
        raise ValueError("Deepgram API key missing")
    
    with patch("app.voice.stt._deepgram_stt", new=AsyncMock(side_effect=deepgram_fail)):
        with patch("app.voice.stt._whisper_stt", new=AsyncMock(return_value={
            "text": "Hello, how can I help you today?",
            "confidence": 0.95,
            "words": [],
            "provider": "whisper",
            "model": "whisper-1",
            "language": "en",
        })):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
                result = await transcribe(fake_audio_bytes, provider="auto")
                
                # Should fall back to Whisper
                assert result["provider"] == "whisper"


@pytest.mark.asyncio
async def test_transcribe_empty_audio():
    """Test that empty audio raises ValueError."""
    with pytest.raises(ValueError, match="Audio bytes cannot be empty"):
        await transcribe(b"")


@pytest.mark.asyncio
async def test_transcribe_audio_too_large():
    """Test that audio over 25MB raises ValueError."""
    large_audio = b"x" * (26 * 1024 * 1024)  # 26MB
    
    with pytest.raises(ValueError, match="Audio file too large"):
        await transcribe(large_audio)


@pytest.mark.asyncio
async def test_transcribe_all_providers_fail(fake_audio_bytes):
    """Test that ValueError is raised when all providers fail."""
    async def fail(*args, **kwargs):
        raise ValueError("API failed")
    
    with patch("app.voice.stt._deepgram_stt", new=AsyncMock(side_effect=fail)):
        with patch("app.voice.stt._whisper_stt", new=AsyncMock(side_effect=fail)):
            with pytest.raises(ValueError, match="All STT providers failed"):
                await transcribe(fake_audio_bytes, provider="auto")


@pytest.mark.asyncio
async def test_transcribe_with_language(fake_audio_bytes):
    """Test that language parameter is passed correctly."""
    captured_language = None
    
    async def mock_deepgram(audio, language, model):
        nonlocal captured_language
        captured_language = language
        return {
            "text": "Bonjour",
            "confidence": 0.9,
            "words": [],
            "provider": "deepgram",
            "model": "nova-2",
        }
    
    with patch("app.voice.stt._deepgram_stt", new=AsyncMock(side_effect=mock_deepgram)):
        with patch.dict("os.environ", {"DEEPGRAM_API_KEY": "test_key"}):
            await transcribe(fake_audio_bytes, provider="deepgram", language="fr")
            
            assert captured_language == "fr"


@pytest.mark.asyncio
async def test_transcribe_file(tmp_path, fake_audio_bytes):
    """Test transcribe_file helper function."""
    # Create temporary audio file
    audio_file = tmp_path / "test_audio.wav"
    audio_file.write_bytes(fake_audio_bytes)
    
    with patch("app.voice.stt._deepgram_stt", new=AsyncMock(return_value={
        "text": "Test transcription",
        "confidence": 0.9,
        "words": [],
        "provider": "deepgram",
        "model": "nova-2",
    })):
        with patch.dict("os.environ", {"DEEPGRAM_API_KEY": "test_key"}):
            result = await transcribe_file(str(audio_file), provider="deepgram")
            
            assert result["text"] == "Test transcription"
            assert result["provider"] == "deepgram"


@pytest.mark.asyncio
async def test_transcribe_with_custom_model(fake_audio_bytes):
    """Test that custom model parameter works."""
    captured_model = None
    
    async def mock_deepgram(audio, language, model):
        nonlocal captured_model
        captured_model = model
        return {
            "text": "Test",
            "confidence": 0.9,
            "words": [],
            "provider": "deepgram",
            "model": model or "nova-2",
        }
    
    with patch("app.voice.stt._deepgram_stt", new=AsyncMock(side_effect=mock_deepgram)):
        with patch.dict("os.environ", {"DEEPGRAM_API_KEY": "test_key"}):
            await transcribe(fake_audio_bytes, provider="deepgram", model="nova-medical")
            
            assert captured_model == "nova-medical"


@pytest.mark.asyncio
async def test_deepgram_stream_stt_not_implemented():
    """Test that DeepgramStreamSTT raises NotImplementedError."""
    from app.voice.stt import DeepgramStreamSTT
    
    with patch.dict("os.environ", {"DEEPGRAM_API_KEY": "test_key"}):
        stream = DeepgramStreamSTT()
        
        with pytest.raises(NotImplementedError, match="websockets library"):
            await stream.connect()
        
        with pytest.raises(NotImplementedError, match="deepgram-sdk"):
            await stream.send_audio(b"audio_chunk")
        
        with pytest.raises(NotImplementedError, match="deepgram-sdk"):
            await stream.close()


def test_deepgram_stream_stt_requires_api_key():
    """Test that DeepgramStreamSTT requires API key."""
    from app.voice.stt import DeepgramStreamSTT
    
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="DEEPGRAM_API_KEY not set"):
            DeepgramStreamSTT()
