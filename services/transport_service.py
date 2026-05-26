"""
Recepta - Transport Service (LiveKit)
Handles WebRTC audio transport via LiveKit for real-time voice calls.
Compatible with Pipecat's transport layer.
"""

import os
import json
import asyncio
from typing import Callable, Optional

from config.settings import (
    LIVEKIT_URL,
    LIVEKIT_API_KEY,
    LIVEKIT_API_SECRET,
    LIVEKIT_ROOM_NAME,
    LIVEKIT_IDENTITY,
    SAMPLE_RATE,
    VAD_THRESHOLD,
    SILENCE_TIMEOUT_SECONDS,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class TransportService:
    """
    Audio transport service using LiveKit for WebRTC communication.

    Manages:
    - Room connection/disconnection
    - Audio input/output streaming
    - Participant tracking
    - Audio encoding/decoding
    """

    def __init__(self):
        self.url = LIVEKIT_URL
        self.api_key = LIVEKIT_API_KEY
        self.api_secret = LIVEKIT_API_SECRET
        self.room_name = LIVEKIT_ROOM_NAME
        self.identity = LIVEKIT_IDENTITY
        self.sample_rate = SAMPLE_RATE

        # LiveKit components (lazy loaded)
        self._room = None
        self._audio_source = None
        self._audio_sink = None
        self._participant = None

        # Callbacks
        self.on_audio_input: Optional[Callable] = None
        self.on_participant_joined: Optional[Callable] = None
        self.on_participant_left: Optional[Callable] = None
        self.on_connection_state_changed: Optional[Callable] = None

        # State
        self._is_connected = False
        self._output_queue: asyncio.Queue = asyncio.Queue()
        self._input_task: Optional[asyncio.Task] = None
        self._output_task: Optional[asyncio.Task] = None

        logger.info(f"Transport Service initialized (url={self.url})")

    # ─── Connection Management ──────────────────────────────────────────────

    async def connect(self, room_name: Optional[str] = None) -> bool:
        """
        Connect to a LiveKit room.

        Args:
            room_name: Room to join (defaults to config)

        Returns:
            True if connected successfully
        """
        try:
            # Try importing LiveKit
            try:
                from livekit import api
                from livekit.rtc import (
                    Room,
                    RoomEvent,
                    AudioSource,
                    AudioSink,
                    AudioFrame,
                    TrackPublication,
                    TrackKind,
                )
            except ImportError:
                logger.error(
                    "livekit-api not installed. Install with: pip install livekit-api livekit-rtc"
                )
                return False

            room_name = room_name or self.room_name

            # Create room instance
            self._room = Room()

            # Register event handlers
            @self._room.on(RoomEvent.ParticipantConnected)
            def on_participant_connected(participant):
                logger.info(f"Participant joined: {participant.identity}")
                if self.on_participant_joined:
                    asyncio.create_task(self.on_participant_joined(participant))

            @self._room.on(RoomEvent.ParticipantDisconnected)
            def on_participant_disconnected(participant):
                logger.info(f"Participant left: {participant.identity}")
                if self.on_participant_left:
                    asyncio.create_task(self.on_participant_left(participant))

            @self._room.on(RoomEvent.TrackSubscribed)
            def on_track_subscribed(track, publication, participant):
                logger.info(f"Track subscribed: {track.kind}")
                if track.kind == TrackKind.KIND_AUDIO:
                    self._audio_sink = AudioSink(track)
                    self._audio_sink.on_data = self._handle_audio_data

            @self._room.on(RoomEvent.Disconnected)
            def on_disconnected():
                logger.info("Room disconnected")
                self._is_connected = False
                if self.on_connection_state_changed:
                    asyncio.create_task(self.on_connection_state_changed(False))

            # Connect to the room
            token = self._generate_token(room_name)
            await self._room.connect(self.url, token)
            self._is_connected = True

            # Create audio source for output
            self._audio_source = AudioSource(self.sample_rate, 1)
            await self._room.local_participant.publish_track(self._audio_source)

            logger.info(f"Connected to LiveKit room: {room_name}")

            # Start background tasks
            self._output_task = asyncio.create_task(self._output_worker())
            return True

        except Exception as e:
            logger.error(f"LiveKit connection failed: {e}")
            self._is_connected = False
            return False

    def _generate_token(self, room_name: str) -> str:
        """Generate a LiveKit access token."""
        try:
            from livekit.api import AccessToken

            token = AccessToken(self.api_key, self.api_secret)
            token.identity = self.identity
            token.add_grant(room_join=True, room=room_name)
            return token.to_jwt()
        except ImportError:
            logger.warning("livekit-api not available for token generation")
            # Return a placeholder — in production, use the LiveKit server's token API
            return ""

    async def disconnect(self):
        """Disconnect from the LiveKit room."""
        if self._input_task:
            self._input_task.cancel()
            self._input_task = None
        if self._output_task:
            self._output_task.cancel()
            self._output_task = None

        if self._room:
            await self._room.disconnect()
            self._room = None

        self._is_connected = False
        logger.info("Disconnected from LiveKit")

    # ─── Audio Handling ────────────────────────────────────────────────────

    def _handle_audio_data(self, frame: "AudioFrame"):
        """
        Handle incoming audio frame from participant.

        Args:
            frame: LiveKit AudioFrame with PCM data
        """
        if self.on_audio_input:
            try:
                # Convert AudioFrame to raw PCM bytes
                audio_bytes = frame.data.tobytes()
                asyncio.create_task(self.on_audio_input(audio_bytes))
            except Exception as e:
                logger.error(f"Audio input handler error: {e}")

    async def send_audio(self, audio_bytes: bytes):
        """
        Queue audio for output to the room.

        Args:
            audio_bytes: PCM audio data to send
        """
        await self._output_queue.put(audio_bytes)

    async def _output_worker(self):
        """Background task that sends queued audio to LiveKit."""
        while self._is_connected:
            try:
                audio_bytes = await asyncio.wait_for(
                    self._output_queue.get(), timeout=1.0
                )

                if self._audio_source and audio_bytes:
                    try:
                        from livekit.rtc import AudioFrame
                        import numpy as np

                        # Convert bytes to numpy int16 array
                        audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
                        frame = AudioFrame(
                            data=audio_data.tobytes(),
                            sample_rate=self.sample_rate,
                            num_channels=1,
                            samples_per_channel=len(audio_data),
                        )
                        await self._audio_source.capture_frame(frame)
                    except Exception as e:
                        logger.error(f"Audio output error: {e}")

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Output worker error: {e}")

    # ─── State ──────────────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        """Check if connected to a room."""
        return self._is_connected

    async def list_participants(self) -> list:
        """List participants in the current room."""
        if self._room:
            return list(self._room.participants.values())
        return []

    async def mute_agent(self):
        """Mute the agent's audio output."""
        if self._audio_source:
            # Clear output queue
            while not self._output_queue.empty():
                try:
                    self._output_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

    async def close(self):
        """Full cleanup."""
        await self.disconnect()
        logger.info("Transport Service shut down")


# ─── Pipecat Transport Factory ──────────────────────────────────────────────

async def create_livekit_transport() -> dict:
    """
    Create LiveKit transport configuration for Pipecat pipeline.

    Returns:
        Dict with transport setup
    """
    transport = TransportService()
    return {
        "service": transport,
        "name": "livekit",
        "type": "transport",
    }
