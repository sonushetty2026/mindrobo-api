# Voice Pipeline — TTS + STT

Natural, emotional voice services for MindRobo AI receptionist.

## Features

### Text-to-Speech (TTS)
- **ElevenLabs** (primary) — best naturalness, voice cloning
- **Azure Neural TTS** (fallback) — reliability, enterprise-grade
- Phrase caching for reduced latency
- Emotion/tone control
- Multiple voice options (warm, professional)

### Speech-to-Text (STT)
- **Deepgram Nova-2** (primary) — fast streaming, real-time
- **OpenAI Whisper** (secondary) — high accuracy, batch transcription
- Word-level timestamps
- Confidence scores
- Multilingual support

---

## Installation

### Environment Variables

Add to `.env` or Azure Key Vault:

```bash
# TTS providers (at least one required)
ELEVENLABS_API_KEY=sk_...
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=eastus

# STT providers (at least one required)
DEEPGRAM_API_KEY=...
OPENAI_API_KEY=sk-...
```

### Dependencies

All required dependencies are in `requirements.txt`:
```bash
pip install httpx pytest pytest-asyncio
```

For streaming STT (optional):
```bash
pip install websockets deepgram-sdk
```

---

## Usage

### Text-to-Speech

```python
from app.voice.tts import speak, cache_common_phrases, clear_cache

# Basic usage (auto-selects best provider)
audio_bytes = await speak("Hello, thanks for calling!")

# Specify voice and provider
audio = await speak(
    "Your appointment is confirmed.",
    voice="female_professional",
    provider="elevenlabs"
)

# Control emotion/tone
audio = await speak(
    "I'm so sorry to hear that!",
    voice="female_warm",
    emotion={
        "stability": 0.4,  # More expressive
        "similarity_boost": 0.8,
        "style": 0.5,  # Warmer tone
    }
)

# Pre-cache common phrases
cache_common_phrases({
    "greeting": "Hey there, thanks for calling! How can I help you today?",
    "hold": "Sure, give me just a moment.",
    "closing": "Thanks for calling! Have a great day."
})

# Clear cache
clear_cache()
```

### Speech-to-Text

```python
from app.voice.stt import transcribe, transcribe_file

# Transcribe audio bytes
audio_bytes = load_audio_from_call()
result = await transcribe(audio_bytes)

print(result["text"])        # "Hello, I need help with..."
print(result["confidence"])  # 0.95
print(result["provider"])    # "deepgram"

# Transcribe audio file
result = await transcribe_file("recording.wav")

# Specify provider and language
result = await transcribe(
    audio_bytes,
    provider="whisper",
    language="es"
)

# Get word-level timestamps
for word_info in result["words"]:
    print(f"{word_info['word']} ({word_info['start']:.2f}s - {word_info['end']:.2f}s)")
```

---

## Voice Options

### TTS Voices

| Voice ID | Description | Use Case |
|----------|-------------|----------|
| `female_warm` | Friendly, empathetic, conversational | Greetings, customer support |
| `male_professional` | Clear, authoritative, calm | Formal communications |
| `female_professional` | Professional, clear, trustworthy | Business information |

### Emotion Control (ElevenLabs only)

```python
emotion = {
    "stability": 0.5,         # 0-1: Lower = more expressive, higher = more consistent
    "similarity_boost": 0.75, # 0-1: How closely to match original voice
    "style": 0.3,             # 0-1: Amount of style/emotion exaggeration
}
```

**Presets**:
- **Warm greeting**: `{"stability": 0.4, "similarity_boost": 0.8, "style": 0.5}`
- **Professional**: `{"stability": 0.7, "similarity_boost": 0.75, "style": 0.2}`
- **Empathetic**: `{"stability": 0.3, "similarity_boost": 0.8, "style": 0.6}`

---

## Performance

### Latency Targets

| Operation | Target | Typical |
|-----------|--------|---------|
| TTS (ElevenLabs) | < 500ms | 200-400ms |
| TTS (Azure) | < 1000ms | 600-1200ms |
| STT (Deepgram) | < 500ms | 150-300ms |
| STT (Whisper) | < 5s | 2-5s |

### Caching

Repeated phrases are cached in-memory. For production:
- Use Redis for distributed caching
- Pre-cache common phrases on startup
- Clear cache daily to avoid memory bloat

```python
# Pre-cache on startup
cache_common_phrases({
    "greeting": "Hey there, thanks for calling!",
    "hold": "One moment please.",
    "transfer": "Let me transfer you.",
    "voicemail": "Please leave a message after the beep."
})
```

---

## Cost Estimates

Based on 50 calls/day per business, 2 min/call, 50% AI speaking:

### TTS
- **ElevenLabs**: $99/month (Pro plan, best quality)
- **Azure**: ~$7/month (reliable, cheaper)
- **Deepgram**: ~$11/month (good balance)

### STT
- **Deepgram**: ~$65/month (real-time streaming)
- **Whisper**: ~$18/month (batch transcription)

**Recommended**: Deepgram TTS + Deepgram STT = ~$12/business/month

---

## Testing

Run tests:
```bash
pytest tests/voice/ -v
```

Test with real APIs (requires API keys):
```bash
export ELEVENLABS_API_KEY=sk_...
export DEEPGRAM_API_KEY=...

python -c "
import asyncio
from app.voice.tts import speak
from app.voice.stt import transcribe_file

async def test():
    # TTS
    audio = await speak('Hello, this is a test.', provider='elevenlabs')
    with open('test_output.mp3', 'wb') as f:
        f.write(audio)
    print(f'Generated {len(audio)} bytes of audio')
    
    # STT
    result = await transcribe_file('test_input.wav')
    print(f'Transcription: {result[\"text\"]}')

asyncio.run(test())
"
```

---

## Integration with Retell

The voice pipeline can be used alongside Retell or as a replacement:

### With Retell (current)
- Retell handles voice layer end-to-end
- Use this pipeline for:
  - Pre-recorded messages
  - Voicemail greetings
  - SMS-to-speech for notifications

### Without Retell (future)
- Use Deepgram for real-time streaming TTS+STT
- Build custom voice agent with FastAPI WebSocket
- Lower cost at scale (~$12/mo vs Retell ~$50/mo)

---

## Future Enhancements

- [ ] Voice cloning for custom business voices
- [ ] Real-time streaming STT via WebSocket
- [ ] Emotion detection in caller speech
- [ ] Multi-speaker diarization
- [ ] Background noise reduction
- [ ] Voice activity detection (VAD)
- [ ] Conversation analytics (sentiment, keywords)

---

## Troubleshooting

### "ELEVENLABS_API_KEY not set"
```bash
export ELEVENLABS_API_KEY=sk_your_key_here
# Or add to .env file
```

### "All TTS providers failed"
- Check API keys are valid
- Verify network connectivity
- Check provider status pages
- Review error logs for specific failure reason

### Slow TTS latency
- Use `provider="elevenlabs"` for fastest results
- Pre-cache common phrases
- Consider shorter text chunks
- Check network latency to API

### Low STT accuracy
- Ensure audio quality is good (16kHz+ sample rate)
- Use Whisper for final transcripts (higher accuracy)
- Provide language hint for non-English
- Check audio format compatibility

---

## Documentation

- **Research**: See `VOICE_RESEARCH.md` for provider comparison
- **API Docs**: See inline docstrings in `tts.py` and `stt.py`
- **Tests**: See `tests/voice/` for usage examples
