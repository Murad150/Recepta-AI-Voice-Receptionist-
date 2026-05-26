"""
Recepta - Speech-to-Text Service
Connects to Speaches (local faster-whisper server) via REST and WebSocket.
Compatible with Pipecat's FrameProcessor pattern.
"""

import asyncio
import json
import aiohttp
import websockets
from typing import AsyncGenerator, Optional

from config.settings import (
    SPEACHES_BASE_URL,
    SPEACHES_API_KEY,
    SPEACHES_MODEL,
    SPEACHES_USE_WEBSOCKET,
    SAMPLE_RATE,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class STTService:
    """
    Speech-to-Text service using Speaches (faster-whisper via Docker).

    Supports both:
    - REST API: send full audio, get full transcription
    - WebSocket: stream audio chunks, get incremental transcriptions
    """

    def __init__(self):
        self.base_url = SPEACHES_BASE_URL.rstrip("/")
        self.api_key = SPEACHES_API_KEY
        self.model = SPEACHES_MODEL
        self.use_websocket = SPEACHES_USE_WEBSOCKET
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        logger.info(f"STT Service initialized (model={self.model}, ws={self.use_websocket})")

    async def ensure_session(self):
        """Ensure aiohttp session exists."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )

    # ─── REST API: Full Audio Transcription ─────────────────────────────────

    async def transcribe_file(self, audio_path: str, language: str = "en") -> str:
        """
        Transcribe an audio file using the REST API.

        Args:
            audio_path: Path to audio file (wav, mp3, etc.)
            language: Language code (default: "en")

        Returns:
            Transcribed text
        """
        await self.ensure_session()
        url = f"{self.base_url}/v1/audio/transcriptions"

        try:
            with open(audio_path, "rb") as f:
                files = {"file": (audio_path, f, "audio/wav")}
                data = {"model": self.model, "language": language}

                async with self._session.post(url, data=data, files=files) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"STT API error ({resp.status}): {error_text}")
                        return ""

                    result = await resp.json()
                    text = result.get("text", "")
                    logger.debug(f"Transcribed: {text[:100]}...")
                    return text

        except aiohttp.ClientError as e:
            logger.error(f"STT connection error: {e}")
            return ""
        except FileNotFoundError:
            logger.error(f"Audio file not found: {audio_path}")
            return ""

    async def transcribe_bytes(self, audio_bytes: bytes, language: str = "en") -> str:
        """
        Transcribe raw audio bytes using the REST API.

        Args:
            audio_bytes: Raw audio data (WAV format)
            language: Language code

        Returns:
            Transcribed text
        """
        await self.ensure_session()
        url = f"{self.base_url}/v1/audio/transcriptions"

        try:
            form = aiohttp.FormData()
            form.add_field("file", audio_bytes, filename="audio.wav", content_type="audio/wav")
            form.add_field("model", self.model)
            form.add_field("language", language)

            async with self._session.post(url, data=form) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"STT bytes error ({resp.status}): {error_text}")
                    return ""

                result = await resp.json()
                return result.get("text", "")

        except aiohttp.ClientError as e:
            logger.error(f"STT bytes connection error: {e}")
            return ""

    # ─── WebSocket: Streaming Transcription ─────────────────────────────────

    async def connect_ws(self) -> bool:
        """
        Connect to Speaches WebSocket for streaming transcription.

        Returns:
            True if connected successfully
        """
        ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/v1/audio/transcriptions?model={self.model}&language=en"

        try:
            self._ws = await websockets.connect(
                ws_url,
                extra_headers={"Authorization": f"Bearer {self.api_key}"},
            )
            logger.info("STT WebSocket connected")
            return True
        except Exception as e:
            logger.error(f"STT WebSocket connection failed: {e}")
            return False

    async def stream_audio(self, audio_chunk: bytes) -> None:
        """
        Send an audio chunk to the WebSocket for streaming transcription.

        Args:
            audio_chunk: Raw audio bytes to transcribe
        """
        if self._ws is None or self._ws.closed:
            if not await self.connect_ws():
                return

        try:
            await self._ws.send(audio_chunk)
        except Exception as e:
            logger.error(f"STT stream send error: {e}")
            self._ws = None

    async def receive_transcript(self) -> Optional[str]:
        """
        Receive the next transcription from the WebSocket stream.

        Returns:
            Transcribed text segment, or None if disconnected
        """
        if self._ws is None or self._ws.closed:
            return None

        try:
            message = await asyncio.wait_for(self._ws.recv(), timeout=5.0)
            if isinstance(message, bytes):
                message = message.decode("utf-8")

            data = json.loads(message)
            text = data.get("text", "")

            if text.strip():
                logger.debug(f"Streaming transcript: {text}")
            return text

        except asyncio.TimeoutError:
            return ""
        except websockets.ConnectionClosed:
            logger.warning("STT WebSocket closed")
            self._ws = None
            return None
        except Exception as e:
            logger.error(f"STT receive error: {e}")
            return None

    async def close_ws(self):
        """Close the WebSocket connection."""
        if self._ws and not self._ws.closed:
            await self._ws.close()
            logger.info("STT WebSocket closed")

    async def close(self):
        """Cleanup all connections."""
        await self.close_ws()
        if self._session and not self._session.closed:
            await self._session.close()
        logger.info("STT Service shut down")


# ─── Factory function for Pipecat compatibility ──────────────────────────────

async def create_stt_pipeline() -> dict:
    """
    Create STT pipeline configuration for Pipecat integration.

    Returns:
        Dict with processor setup for Pipecat pipeline
    """
    stt = STTService()
    return {
        "service": stt,
        "name": "stt",
        "type": "transcription",
    }
