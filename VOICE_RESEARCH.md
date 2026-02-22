# Voice Pipeline Research — TTS + STT

**Date**: 2026-02-22  
**Author**: Ingestion Agent  
**Purpose**: Evaluate TTS and STT providers for MindRobo voice pipeline

---

## Executive Summary

**Recommended Stack**:
- **TTS**: ElevenLabs (primary) + Azure Neural TTS (fallback)
- **STT**: Deepgram Nova-2 (streaming) + Whisper (batch transcription)

**Why**: Best balance of naturalness, latency, cost, and reliability.

---

## Requirements

From Issue #39 and product context:

1. **Naturalness**: Must sound human, not robotic (Giga.AI quality standard)
2. **Latency**: TTS response under 500ms for real-time conversation
3. **Emotion/Tone**: Warm, friendly greetings; professional service responses
4. **Cost**: Affordable for small business use case ($49/month subscription model)
5. **Reliability**: High uptime, fallback options
6. **Use Cases**:
   - Real-time phone calls (Retell replacement/alternative)
   - Webchat voice messages
   - WhatsApp voice notes
   - Internal demos and testing

---

## TTS (Text-to-Speech) Comparison

### 1. ElevenLabs
**Website**: https://elevenlabs.io

**Pros**:
- ✅ **Best naturalness** — industry-leading voice quality with emotion
- ✅ **Low latency** — 200-400ms for short phrases (streaming mode)
- ✅ **Voice cloning** — can create custom voices from samples
- ✅ **Emotion control** — stability, similarity, style sliders
- ✅ **Multilingual** — 29+ languages
- ✅ **Voice library** — pre-made professional voices

**Cons**:
- ❌ **Cost** — $0.30/1K chars ($5-$22/month plans, $99/month for commercial)
- ❌ **Rate limits** — 20 requests/sec on Starter plan
- ❌ **Quota limits** — 30K chars/month on free tier

**Pricing**:
- Free: 10K chars/month
- Starter: $5/month — 30K chars (~15 minutes)
- Creator: $22/month — 100K chars (~50 minutes)
- Pro: $99/month — 500K chars (~250 minutes)

**Latency**: 200-400ms (streaming), 800ms-1.5s (full audio)

**API Example**:
```python
import requests

def elevenlabs_tts(text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> bytes:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": API_KEY}
    data = {
        "text": text,
        "model_id": "eleven_turbo_v2",  # Fastest model
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    resp = requests.post(url, json=data, headers=headers)
    return resp.content
```

**Score**: 9/10 — Best quality, but expensive for high volume

---

### 2. Deepgram Aura
**Website**: https://deepgram.com/product/text-to-speech

**Pros**:
- ✅ **Very low latency** — 150-300ms (optimized for real-time)
- ✅ **Good naturalness** — better than Azure, not quite ElevenLabs
- ✅ **Cost-effective** — $0.015/minute ($0.90/hour vs ElevenLabs $18/hour)
- ✅ **Streaming** — word-by-word audio chunks for ultra-low latency
- ✅ **No character limits** — pay per minute of audio
- ✅ **Same provider as STT** — single integration

**Cons**:
- ❌ **Smaller voice library** — ~12 voices vs ElevenLabs 100+
- ❌ **Less emotion control** — no fine-grained sliders
- ❌ **Newer product** — less battle-tested than competitors

**Pricing**:
- Pay-as-you-go: $0.015/minute of audio
- Growth: $150/month — 12,000 minutes included (~$0.0125/min overage)

**Latency**: 150-300ms (streaming)

**API Example**:
```python
from deepgram import DeepgramClient

def deepgram_tts(text: str, voice: str = "aura-asteria-en") -> bytes:
    dg = DeepgramClient(api_key=API_KEY)
    response = dg.speak.v1.save(
        filename="output.mp3",
        source={"text": text},
        options={"model": voice}
    )
    return response
```

**Score**: 8/10 — Best cost/performance ratio for real-time

---

### 3. Azure Neural TTS
**Website**: https://azure.microsoft.com/en-us/products/ai-services/text-to-speech

**Pros**:
- ✅ **Solid reliability** — enterprise-grade uptime (99.9% SLA)
- ✅ **Good pricing** — $15/1M chars (~$1/hour of audio)
- ✅ **Multilingual** — 100+ languages, 400+ voices
- ✅ **SSML support** — fine-grained prosody, emphasis, pauses
- ✅ **Already using Azure** — easy integration (Key Vault, blob storage)
- ✅ **Custom neural voice** — train on your own data

**Cons**:
- ❌ **Latency** — 600-1200ms (slower than ElevenLabs/Deepgram)
- ❌ **Less natural** — better than old TTS, but behind ElevenLabs
- ❌ **Quota limits** — 20 requests/sec, 200 concurrent

**Pricing**:
- Neural: $15/1M chars
- Custom Neural: $6/hour training + $15.50/1M chars
- Free tier: 500K chars/month

**Latency**: 600-1200ms

**API Example**:
```python
import azure.cognitiveservices.speech as speechsdk

def azure_tts(text: str, voice: str = "en-US-JennyNeural") -> bytes:
    speech_config = speechsdk.SpeechConfig(subscription=KEY, region=REGION)
    speech_config.speech_synthesis_voice_name = voice
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
    result = synthesizer.speak_text_async(text).get()
    return result.audio_data
```

**Score**: 7/10 — Good fallback, but not first choice for naturalness

---

### 4. OpenAI TTS
**Website**: https://platform.openai.com/docs/guides/text-to-speech

**Pros**:
- ✅ **Simple API** — easy to integrate
- ✅ **Good quality** — natural-sounding voices
- ✅ **Affordable** — $15/1M chars (same as Azure)
- ✅ **6 voices** — alloy, echo, fable, onyx, nova, shimmer
- ✅ **HD model** — tts-1-hd for higher quality

**Cons**:
- ❌ **Latency** — 800-1500ms (not optimized for real-time)
- ❌ **No emotion control** — can't adjust tone/stability
- ❌ **Limited voices** — only 6 options
- ❌ **No streaming** — full audio only

**Pricing**:
- TTS: $15/1M chars
- TTS-HD: $30/1M chars

**Latency**: 800-1500ms

**API Example**:
```python
from openai import OpenAI

def openai_tts(text: str, voice: str = "nova") -> bytes:
    client = OpenAI(api_key=API_KEY)
    response = client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text
    )
    return response.content
```

**Score**: 6.5/10 — Simple but slow, not ideal for real-time

---

## TTS Recommendation

**Primary**: **ElevenLabs** (best naturalness)  
**Fallback**: **Azure Neural TTS** (reliability, already using Azure)  
**Future consideration**: **Deepgram Aura** (when latency is critical)

### Why ElevenLabs as Primary?
- Naturalness is the #1 requirement (Giga.AI quality standard)
- Voice cloning allows business-specific custom voices
- Emotion control for warm/professional tone switching
- 200-400ms latency meets our 500ms target

### Cost Analysis (50 calls/day scenario)
- Avg call duration: 2 minutes
- Avg AI speech per call: 30 seconds (rest is caller talking)
- 50 calls/day × 30 sec = 1500 seconds = 25 minutes/day
- 25 min/day × 30 days = 750 minutes/month = 450K chars

**ElevenLabs cost**: $99/month (Pro plan — 500K chars)  
**Azure cost**: ~$7/month (450K chars)  
**Deepgram cost**: ~$11/month (750 minutes)

**Decision**: Start with ElevenLabs for demo/beta. Consider Deepgram for production scale.

---

## STT (Speech-to-Text) Comparison

### 1. Deepgram Nova-2
**Website**: https://deepgram.com/product/speech-to-text

**Pros**:
- ✅ **Fastest** — 150-300ms latency (real-time streaming)
- ✅ **Best accuracy** — 90%+ WER on conversational speech
- ✅ **Cost-effective** — $0.0043/minute ($0.26/hour)
- ✅ **Streaming** — word-by-word transcription for live calls
- ✅ **Multichannel** — separate caller/agent tracks
- ✅ **Emotion detection** — built-in sentiment analysis
- ✅ **Punctuation** — automatic capitalization and punctuation

**Cons**:
- ❌ **Requires streaming infra** — WebSocket handling
- ❌ **Not free** — no generous free tier

**Pricing**:
- Pay-as-you-go: $0.0043/minute
- Growth: $99/month — 27,000 minutes included

**Latency**: 150-300ms (streaming)

**API Example**:
```python
from deepgram import DeepgramClient

def deepgram_stt(audio_bytes: bytes) -> str:
    dg = DeepgramClient(api_key=API_KEY)
    response = dg.listen.prerecorded.v1.transcribe_file(
        {"buffer": audio_bytes},
        {"model": "nova-2", "punctuate": True, "language": "en"}
    )
    return response["results"]["channels"][0]["alternatives"][0]["transcript"]
```

**Score**: 9/10 — Best for real-time phone calls

---

### 2. OpenAI Whisper
**Website**: https://platform.openai.com/docs/guides/speech-to-text

**Pros**:
- ✅ **Best accuracy** — 95%+ WER, multilingual
- ✅ **Affordable** — $0.006/minute ($0.36/hour)
- ✅ **Multilingual** — 99 languages
- ✅ **No model selection** — one model, always improving
- ✅ **Can self-host** — open-source version available

**Cons**:
- ❌ **Latency** — 2-5 seconds (batch processing only, no streaming)
- ❌ **File size limit** — 25MB max
- ❌ **No real-time** — not suitable for live calls

**Pricing**:
- Whisper: $0.006/minute

**Latency**: 2-5 seconds (batch)

**API Example**:
```python
from openai import OpenAI

def whisper_stt(audio_file_path: str) -> str:
    client = OpenAI(api_key=API_KEY)
    with open(audio_file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    return transcript.text
```

**Score**: 8/10 — Best for post-call transcription, not real-time

---

### 3. Azure Speech-to-Text
**Website**: https://azure.microsoft.com/en-us/products/ai-services/speech-to-text

**Pros**:
- ✅ **Solid reliability** — 99.9% SLA
- ✅ **Real-time + batch** — supports both modes
- ✅ **Custom models** — train on domain-specific vocabulary
- ✅ **Already using Azure** — easy integration

**Cons**:
- ❌ **More expensive** — $1/hour (vs Deepgram $0.26/hour)
- ❌ **Slower** — 400-800ms latency
- ❌ **Complex pricing** — different tiers, hard to estimate

**Pricing**:
- Standard: $1/hour
- Custom: $1.40/hour
- Free tier: 5 hours/month

**Latency**: 400-800ms

**Score**: 6.5/10 — Overpriced for what it offers

---

## STT Recommendation

**Primary**: **Deepgram Nova-2** (real-time streaming)  
**Secondary**: **OpenAI Whisper** (post-call batch transcription)

### Why Deepgram as Primary?
- Fastest latency (150-300ms) for real-time calls
- Best cost/performance ratio
- Streaming support for immediate feedback
- Emotion detection for sentiment analysis

### Why Whisper as Secondary?
- Best accuracy for final transcripts
- Affordable for post-call processing
- Multilingual support for future expansion
- Can self-host if volume scales massively

---

## Implementation Plan

### Phase 1: Core Pipeline (This PR)
1. Create `app/voice/tts.py`:
   - ElevenLabs integration (primary)
   - Azure Neural TTS (fallback)
   - Caching for repeated phrases
   - Emotion/tone control

2. Create `app/voice/stt.py`:
   - Deepgram streaming STT (primary)
   - Whisper batch STT (secondary)

3. Add tests with mocked API responses

### Phase 2: Optimization (Future)
- Phrase caching (Redis) for greetings
- Voice cloning for custom business voices
- Emotion detection pipeline
- Latency monitoring and alerts

### Phase 3: Alternative Use Cases (Future)
- Webchat voice messages
- WhatsApp voice note transcription
- Internal demo/testing tools
- Retell replacement (if needed)

---

## Cost Projections

**Scenario**: 50 businesses × 10 calls/day × 2 min/call

- **Total calls/month**: 15,000 calls
- **AI speech time**: 7,500 minutes (50% of call time)
- **Caller speech time**: 7,500 minutes

**TTS Cost** (ElevenLabs):
- 7,500 min × 150 words/min ÷ 4.5 chars/word = 250K chars
- 15 businesses on Pro plan: $99 × 15 = $1,485/month
- **OR** Deepgram: 7,500 min × $0.015 = $112.50/month

**STT Cost** (Deepgram):
- 15,000 min × $0.0043 = $64.50/month

**Total voice cost per business/month**: 
- With ElevenLabs TTS: $103/month
- With Deepgram TTS: $12/month

**Recommendation**: Start with Deepgram for both TTS+STT to keep costs down (~$12/business/month). Offer ElevenLabs as premium add-on for $20/month extra.

---

## Conclusion

**Recommended Stack**:
- **TTS**: Deepgram Aura (cost-effective, fast) with ElevenLabs as premium option
- **STT**: Deepgram Nova-2 (streaming) + Whisper (batch)

This gives us:
- ✅ Sub-500ms latency for TTS
- ✅ Real-time STT streaming
- ✅ ~$12/business/month cost at scale
- ✅ Fallback options for reliability
- ✅ Path to premium voice quality (ElevenLabs)

Implementation starts now with Phase 1.
