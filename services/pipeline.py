"""
Recepta - Pipecat Pipeline Adapter
Connects the custom STT/LLM/TTS services into Pipecat's FrameProcessor pipeline.

This adapter wraps Recepta services so they can be used with Pipecat's real-time
audio pipeline for frame-based processing with proper event handling, VAD, and
low-latency streaming.

Usage:
    from services.pipeline import create_pipecat_pipeline

    pipeline = create_pipecat_pipeline(
        stt_service=my_stt,
        llm_service=my_llm,
        tts_service=my_tts,
        industry="dental",
        business_name="SmileCare Dental",
    )
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PipecatPipelineAdapter:
    """
    Adapter that wraps Recepta services for Pipecat pipeline compatibility.

    Pipecat uses a frame-based architecture where:
    - Audio comes in as AudioFrames
    - STT converts to TextFrames
    - LLM processes and generates TextFrames
    - TTS converts back to AudioFrames
    - Transport sends/receives frames

    This adapter provides a simplified pipeline that can be used with or without
    the full Pipecat framework.
    """

    def __init__(
        self,
        stt_service=None,
        llm_service=None,
        tts_service=None,
        transport_service=None,
        agent=None,
    ):
        self.stt = stt_service
        self.llm = llm_service
        self.tts = tts_service
        self.transport = transport_service
        self.agent = agent
        self._running = False
        logger.info("Pipecat Pipeline Adapter initialized")

    async def process_audio_frame(self, audio_bytes: bytes) -> Optional[bytes]:
        """
        Process a single audio frame through the full pipeline.

        This is the main pipeline loop:
        Audio In -> STT -> LLM -> TTS -> Audio Out

        Args:
            audio_bytes: Raw PCM audio from the caller

        Returns:
            Raw PCM audio response, or None if no response needed
        """
        if not self.stt or not self.llm or not self.tts:
            logger.warning("Pipeline missing required services")
            return None

        # 1. STT: Convert audio to text
        text = await self.stt.transcribe_bytes(audio_bytes)
        if not text or not text.strip():
            return None

        logger.debug(f"STT -> {text[:80]}...")

        # 2. LLM: Process through agent or direct LLM
        if self.agent and self.agent.is_active:
            response_text = ""
            async for chunk in self.agent.process_turn(text):
                response_text += chunk
        elif self.llm:
            response_text = await self.llm.chat(
                messages=[{"role": "user", "content": text}],
            )
        else:
            return None

        if not response_text:
            return None

        logger.debug(f"LLM -> {response_text[:80]}...")

        # 3. TTS: Convert response to audio
        audio = await self.tts.generate(response_text)
        return audio

    async def process_audio_stream(
        self,
        audio_chunks: asyncio.Queue,
        response_queue: asyncio.Queue,
    ):
        """
        Process a stream of audio chunks through the pipeline.

        Args:
            audio_chunks: Queue of incoming audio byte chunks
            response_queue: Queue to put response audio byte chunks
        """
        self._running = True
        logger.info("Pipeline stream processing started")

        try:
            while self._running:
                try:
                    chunk = await asyncio.wait_for(
                        audio_chunks.get(), timeout=30.0
                    )
                except asyncio.TimeoutError:
                    logger.debug("Pipeline stream timeout — no audio received")
                    continue

                response = await self.process_audio_frame(chunk)
                if response:
                    await response_queue.put(response)

        except asyncio.CancelledError:
            logger.info("Pipeline stream cancelled")
        except Exception as e:
            logger.error(f"Pipeline stream error: {e}")
        finally:
            self._running = False
            logger.info("Pipeline stream processing ended")

    async def start(self):
        """Start the pipeline."""
        self._running = True
        logger.info("Pipeline started")

    async def stop(self):
        """Stop the pipeline."""
        self._running = False
        logger.info("Pipeline stopped")

    @property
    def is_running(self) -> bool:
        return self._running


# ─── Pipecat Native Integration (uses Pipecat's FrameProcessor) ──────────────

try:
    from pipecat.frames.frames import (
        AudioRawFrame,
        TextFrame,
        StartFrame,
        EndFrame,
        Frame,
    )
    from pipecat.processors.frame_processor import FrameProcessor

    class STTFrameProcessor(FrameProcessor):
        """
        Pipecat FrameProcessor for STT.
        Converts AudioRawFrames to TextFrames.
        """

        def __init__(self, stt_service):
            super().__init__()
            self._stt = stt_service

        async def process_frame(self, frame: Frame, direction):
            await super().process_frame(frame, direction)

            if isinstance(frame, AudioRawFrame):
                text = await self._stt.transcribe_bytes(frame.audio)
                if text:
                    await self.push_frame(TextFrame(text), direction)
            elif isinstance(frame, (StartFrame, EndFrame)):
                await self.push_frame(frame, direction)

    class LLMFrameProcessor(FrameProcessor):
        """
        Pipecat FrameProcessor for LLM.
        Converts TextFrames to response TextFrames.
        """

        def __init__(self, llm_service, system_prompt: str = ""):
            super().__init__()
            self._llm = llm_service
            self._system_prompt = system_prompt
            self._session_id = None

        async def process_frame(self, frame: Frame, direction):
            await super().process_frame(frame, direction)

            if isinstance(frame, TextFrame):
                if self._session_id:
                    self._llm.add_message(self._session_id, "user", frame.text)
                    response = await self._llm.chat(
                        messages=self._llm.get_conversation(self._session_id)[1:],
                        system_prompt=self._system_prompt,
                    )
                    if response:
                        self._llm.add_message(self._session_id, "assistant", response)
                        await self.push_frame(TextFrame(response), direction)
            elif isinstance(frame, StartFrame):
                self._session_id = f"pipecat_{id(frame)}"
                if self._system_prompt:
                    self._llm.create_conversation(self._session_id, self._system_prompt)
                await self.push_frame(frame, direction)
            elif isinstance(frame, EndFrame):
                self._session_id = None
                await self.push_frame(frame, direction)

    class TTSFrameProcessor(FrameProcessor):
        """
        Pipecat FrameProcessor for TTS.
        Converts TextFrames to AudioRawFrames.
        """

        def __init__(self, tts_service):
            super().__init__()
            self._tts = tts_service

        async def process_frame(self, frame: Frame, direction):
            await super().process_frame(frame, direction)

            if isinstance(frame, TextFrame):
                audio = await self._tts.generate(frame.text)
                if audio:
                    # Extract raw PCM from WAV (skip 44-byte WAV header)
                    pcm_data = audio[44:] if len(audio) > 44 else audio
                    await self.push_frame(
                        AudioRawFrame(audio=pcm_data, sample_rate=16000, num_channels=1),
                        direction,
                    )
            elif isinstance(frame, (StartFrame, EndFrame)):
                await self.push_frame(frame, direction)

    PIPECAT_AVAILABLE = True
    logger.info("Pipecat native integration available")

except ImportError:
    PIPECAT_AVAILABLE = False
    logger.info("Pipecat not installed — using standalone pipeline adapter")
    # Placeholder classes so imports don't fail
    class FrameProcessor:
        pass
    class STTFrameProcessor:
        pass
    class LLMFrameProcessor:
        pass
    class TTSFrameProcessor:
        pass


def create_pipecat_pipeline(
    stt_service=None,
    llm_service=None,
    tts_service=None,
    transport_service=None,
    industry: str = "dental",
    business_name: str = "Your Business",
):
    """
    Create a Pipecat-compatible pipeline from Recepta services.

    If Pipecat is installed, returns native Pipecat FrameProcessors.
    Otherwise, returns the adapter-based pipeline.

    Args:
        stt_service: STTService instance
        llm_service: LLMService instance
        tts_service: TTSService instance
        transport_service: TransportService instance
        industry: Agent industry (dental, legal, hvac, real_estate)
        business_name: Name of the client business

    Returns:
        PipecatPipelineAdapter or native Pipecat pipeline components
    """
    if PIPECAT_AVAILABLE:
        from config.prompts import get_agent_config

        agent_config = get_agent_config(industry, business_name)

        stt_processor = STTFrameProcessor(stt_service)
        llm_processor = LLMFrameProcessor(llm_service, system_prompt=agent_config["system_prompt"])
        tts_processor = TTSFrameProcessor(tts_service)

        from pipecat.pipeline.pipeline import Pipeline

        pipeline = Pipeline([
            stt_processor,
            llm_processor,
            tts_processor,
        ])

        return {
            "pipeline": pipeline,
            "processors": {
                "stt": stt_processor,
                "llm": llm_processor,
                "tts": tts_processor,
            },
            "type": "native",
        }
    else:
        # Fallback to adapter-based pipeline
        return {
            "pipeline": PipecatPipelineAdapter(
                stt_service=stt_service,
                llm_service=llm_service,
                tts_service=tts_service,
                transport_service=transport_service,
            ),
            "type": "adapter",
        }
