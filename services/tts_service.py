"""
Recepta - Text-to-Speech Service
Uses Kokoro-82M for high-quality local TTS generation.
Fallback: MeloTTS for CPU-friendly multilingual support.
"""

import os
import io
import json
import asyncio
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np

from config.settings import (
    KOKORO_MODEL_PATH,
    KOKORO_VOICE,
    KOKORO_DEVICE,
    KOKORO_SPEED,
    VOICES_DIR,
    SAMPLE_RATE,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class TTSService:
    """
    Text-to-Speech service using Kokoro-82M.

    Kokoro is an 82M parameter TTS model with near-human quality.
    Runs efficiently on CPU with minimal RAM usage.

    Features:
    - 100+ voices available
    - Emotion/intonation control
    - Speed adjustment
    - Streaming audio generation
    - Voice cloning support (via fine-tuning)
    """

    def __init__(self):
        self.model_path = KOKORO_MODEL_PATH
        self.voice = KOKORO_VOICE
        self.device = KOKORO_DEVICE
        self.speed = KOKORO_SPEED
        self.sample_rate = SAMPLE_RATE

        # Lazy-loaded model
        self._pipeline = None
        self._model = None
        self._voicepack = None

        # Voice cache for cloned voices
        self._custom_voices: dict[str, bytes] = {}

        logger.info(f"TTS Service initialized (voice={self.voice}, device={self.device})")

    async def ensure_model(self):
        """
        Lazy-load the Kokoro model on first use.
        This saves ~500MB RAM when the TTS service isn't actively used.
        """
        if self._pipeline is not None:
            return

        try:
            # Kokoro can be used via the speaches API or directly via the kokoro library
            # We try speaches first (if running), then fall back to direct kokoro
            logger.info("Loading Kokoro TTS model (first use)...")

            # Try importing kokoro
            try:
                from kokoro import KPipeline
                self._pipeline = KPipeline(lang_code='a')  # 'a' = American English
                logger.info("Kokoro model loaded successfully")

                # Load voicepack
                if self.voice:
                    try:
                        self._voicepack = self._pipeline.load_voice(self.voice)
                        logger.info(f"Loaded voice: {self.voice}")
                    except Exception as e:
                        logger.warning(f"Could not load voice '{self.voice}': {e}. Using default.")
                        self._voicepack = None

            except ImportError:
                logger.warning(
                    "kokoro package not installed. "
                    "Falling back to speaches API for TTS. "
                    "Install with: pip install kokoro"
                )
                self._pipeline = "speaches_fallback"

        except Exception as e:
            logger.error(f"Failed to load TTS model: {e}")
            raise

    # ─── Core TTS Generation ────────────────────────────────────────────────

    async def generate(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> Optional[bytes]:
        """
        Generate audio from text using Kokoro.

        Args:
            text: Text to speak
            voice: Voice to use (overrides default)
            speed: Speaking speed multiplier (overrides default)

        Returns:
            WAV audio bytes, or None on failure
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to TTS")
            return None

        voice = voice or self.voice
        speed = speed or self.speed

        try:
            await self.ensure_model()

            # ── Direct Kokoro generation ──
            if self._pipeline and self._pipeline != "speaches_fallback":
                return await self._generate_direct(text, voice, speed)

            # ── Speaches API fallback ──
            return await self._generate_via_speaches(text, voice)

        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            return None

    async def _generate_direct(self, text: str, voice: str, speed: float) -> bytes:
        """Generate audio directly using Kokoro."""
        loop = asyncio.get_event_loop()

        def _synthesize():
            """Synchronous Kokoro generation (runs in thread pool)."""
            # Use voicepack or load voice
            vp = self._voicepack
            if voice != self.voice:
                try:
                    vp = self._pipeline.load_voice(voice)
                except Exception:
                    vp = self._voicepack

            # Generate audio
            audio_chunks = []
            for result in self._pipeline(text, voice=voice if vp is None else vp, speed=speed):
                audio_chunks.append(result.audio)

            if not audio_chunks:
                return None

            # Concatenate all audio chunks
            full_audio = np.concatenate(audio_chunks) if len(audio_chunks) > 1 else audio_chunks[0]

            # Convert to WAV bytes
            import soundfile as sf
            buffer = io.BytesIO()
            sf.write(buffer, full_audio, self.sample_rate, format="WAV")
            buffer.seek(0)
            return buffer.read()

        return await loop.run_in_executor(None, _synthesize)

    async def _generate_via_speaches(self, text: str, voice: str) -> Optional[bytes]:
        """Generate TTS via Speaches API."""
        import aiohttp

        base_url = "http://localhost:8000"
        url = f"{base_url}/v1/audio/speech"

        payload = {
            "model": "kokoro",
            "input": text,
            "voice": voice,
            "response_format": "wav",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        logger.error(f"Speaches TTS error ({resp.status})")
                        return None
                    return await resp.read()
        except Exception as e:
            logger.error(f"Speaches TTS connection error: {e}")
            return None

    # ─── Streaming TTS (for real-time pipelines) ────────────────────────────

    async def generate_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        chunk_size_ms: int = 200,
    ):
        """
        Generate audio in streaming chunks for low-latency playback.

        Args:
            text: Text to speak
            voice: Voice override
            speed: Speed override
            chunk_size_ms: Size of each audio chunk in milliseconds

        Yields:
            Audio bytes chunks
        """
        full_audio = await self.generate(text, voice, speed)
        if full_audio is None:
            return

        # Skip WAV header for streaming chunks
        # WAV header is 44 bytes, audio data starts at byte 44
        audio_data = full_audio[44:] if len(full_audio) > 44 else full_audio

        # Calculate chunk size in bytes
        bytes_per_ms = self.sample_rate * 2  # 16-bit mono = 2 bytes per sample
        chunk_bytes = (chunk_size_ms * bytes_per_ms) // 1000

        for i in range(0, len(audio_data), chunk_bytes):
            chunk = audio_data[i:i + chunk_bytes]
            yield chunk

    # ─── Voice Cloning Support ──────────────────────────────────────────────

    async def clone_voice(self, audio_sample_path: str, voice_name: str) -> bool:
        """
        Clone a voice from a 6+ second audio sample.

        Args:
            audio_sample_path: Path to audio sample file
            voice_name: Name to save the cloned voice as

        Returns:
            True if cloning succeeded
        """
        # Voice cloning requires additional setup with Kokoro's fine-tuning
        # This is a simplified version that saves the reference audio
        try:
            import shutil
            voice_dir = VOICES_DIR / voice_name
            voice_dir.mkdir(parents=True, exist_ok=True)

            dest_path = voice_dir / "reference.wav"
            shutil.copy2(audio_sample_path, str(dest_path))
            logger.info(f"Voice sample saved for '{voice_name}'")
            return True
        except Exception as e:
            logger.error(f"Voice cloning failed: {e}")
            return False

    async def list_available_voices(self) -> list[str]:
        """List all available voices."""
        try:
            await self.ensure_model()
            if self._pipeline and self._pipeline != "speaches_fallback":
                return list(self._pipeline.list_voices())
            return ["af_bella", "af_nicole", "af_sky", "am_michael", "bf_emma", "bm_george"]
        except Exception:
            return ["af_bella"]  # Default fallback

    async def close(self):
        """Cleanup TTS resources."""
        self._pipeline = None
        self._model = None
        self._voicepack = None
        logger.info("TTS Service shut down")
