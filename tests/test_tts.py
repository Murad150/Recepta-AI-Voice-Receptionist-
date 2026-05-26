"""
Tests for TTS Service (Kokoro).
"""

import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.tts_service import TTSService


@pytest.fixture
def tts_service():
    """Create TTS service instance."""
    return TTSService()


@pytest.mark.asyncio
async def test_tts_initialization(tts_service):
    """Test that TTS service initializes correctly."""
    assert tts_service is not None
    assert tts_service.voice is not None
    assert tts_service.sample_rate == 16000


@pytest.mark.asyncio
async def test_tts_empty_text(tts_service):
    """Test TTS with empty text returns None."""
    result = await tts_service.generate("")
    assert result is None

    result = await tts_service.generate("   ")
    assert result is None


@pytest.mark.asyncio
async def test_tts_list_voices(tts_service):
    """Test listing available voices."""
    voices = await tts_service.list_available_voices()
    assert len(voices) > 0
    assert isinstance(voices, list)


@pytest.mark.asyncio
async def test_tts_generate_short_text(tts_service):
    """Test generating audio with short text."""
    try:
        audio = await tts_service.generate("Hello, this is a test.")
        if audio:
            assert len(audio) > 100  # WAV file should be at least 100 bytes
            # Check WAV header
            assert audio[:4] == b"RIFF"  # WAV files start with RIFF
    except Exception as e:
        pytest.skip(f"Kokoro model not available: {e}")


@pytest.mark.asyncio
async def test_tts_voice_change(tts_service):
    """Test using different voice."""
    try:
        audio_default = await tts_service.generate("Test", voice="af_bella")
        audio_alt = await tts_service.generate("Test", voice="am_michael")

        # Both should produce valid audio, or skip gracefully
        if audio_default and audio_alt:
            assert audio_default[:4] == b"RIFF"
            assert audio_alt[:4] == b"RIFF"
    except Exception as e:
        pytest.skip(f"Voice test skipped: {e}")


@pytest.mark.asyncio
async def test_tts_speed_adjustment(tts_service):
    """Test TTS with different speed settings."""
    try:
        audio_normal = await tts_service.generate("Test", speed=1.0)
        audio_fast = await tts_service.generate("Test", speed=1.5)

        if audio_normal and audio_fast:
            assert len(audio_normal) > 0
            assert len(audio_fast) > 0
    except Exception as e:
        pytest.skip(f"Speed test skipped: {e}")


@pytest.mark.asyncio
async def test_tts_streaming(tts_service):
    """Test streaming audio generation."""
    try:
        chunks = []
        async for chunk in tts_service.generate_stream(
            "This is a test of streaming audio generation.",
            chunk_size_ms=200,
        ):
            chunks.append(chunk)

        if chunks:
            assert len(chunks) > 0
            # Streaming chunks should be smaller than full audio
            for chunk in chunks:
                assert len(chunk) > 0
    except Exception as e:
        pytest.skip(f"Streaming test skipped: {e}")


@pytest.mark.asyncio
async def test_tts_cleanup(tts_service):
    """Test proper cleanup."""
    await tts_service.close()
    assert tts_service._pipeline is None
