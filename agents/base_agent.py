"""
Recepta - Base Agent
Shared logic for all industry-specific voice agents.
Handles conversation flow, context extraction, and pipeline orchestration.
"""

import asyncio
import json
import time
from typing import AsyncGenerator, Optional

from config.settings import (
    DEBUG,
    INTERRUPTIBLE,
    SILENCE_TIMEOUT_SECONDS,
    ENABLE_BAIL_WORDS,
    BAIL_WORDS,
)
from config.prompts import AGENT_PROMPTS, get_agent_config
from utils.logger import get_logger
from utils.helpers import extract_name, extract_phone, extract_intent

logger = get_logger(__name__)


class BaseVoiceAgent:
    """
    Base class for all voice agents.

    Provides shared functionality:
    - Conversation flow management
    - Intent detection and routing
    - Context extraction (name, phone, etc.)
    - Pipeline event handling
    - Graceful error handling
    """

    def __init__(
        self,
        industry: str,
        business_name: str,
        stt_service=None,
        llm_service=None,
        tts_service=None,
        transport_service=None,
        calendar=None,
        crm=None,
        knowledge_base=None,
    ):
        # Agent identity
        self.industry = industry
        self.business_name = business_name
        agent_config = get_agent_config(industry, business_name)
        self.agent_name = agent_config["name"]
        self.system_prompt = agent_config["system_prompt"]

        # Services (injected, not created here)
        self.stt = stt_service
        self.llm = llm_service
        self.tts = tts_service
        self.transport = transport_service
        self.calendar = calendar
        self.crm = crm
        self.knowledge_base = knowledge_base

        # Session state
        self.session_id: Optional[str] = None
        self.conversation_start: Optional[float] = None
        self.caller_name: Optional[str] = None
        self.caller_phone: Optional[str] = None
        self.extracted_intent: Optional[str] = None
        self.call_transcript: list[dict] = []
        self.is_active: bool = False

        # Pipeline components
        self._pipeline = None
        self._running = False

        logger.info(f"Agent '{self.agent_name}' initialized for {business_name} ({industry})")

    # ─── Lifecycle ─────────────────────────────────────────────────────

    async def start(self, session_id: str):
        """
        Start a new conversation session.

        Args:
            session_id: Unique ID for this call session
        """
        self.session_id = session_id
        self.conversation_start = time.time()
        self.is_active = True
        self.call_transcript = []
        self.caller_name = None
        self.caller_phone = None
        self.extracted_intent = None

        # Create LLM conversation
        if self.llm:
            self.llm.create_conversation(session_id, self.system_prompt)

        logger.info(f"Session started: {session_id}")

    async def handle_greeting(self) -> str:
        """
        Generate the initial greeting for the caller.

        Returns:
            Greeting text to speak
        """
        return (
            f"Hi, thank you for calling {self.business_name}. "
            f"This is {self.agent_name} — how can I help you today?"
        )

    async def process_turn(self, user_text: str) -> AsyncGenerator[str, None]:
        """
        Process a single conversational turn.

        Args:
            user_text: Transcribed user speech

        Yields:
            Response text chunks (for streaming TTS)
        """
        if not user_text.strip():
            return

        # Log the user turn
        self.call_transcript.append({"role": "user", "content": user_text})
        logger.debug(f"User: {user_text[:100]}...")

        # Extract context
        self._extract_context(user_text)

        # Detect intent
        self._detect_intent(user_text)

        # Check for bail words
        if ENABLE_BAIL_WORDS and self._check_bail(user_text):
            farewell = await self._generate_farewell()
            self.call_transcript.append({"role": "assistant", "content": farewell})
            yield farewell
            self.is_active = False
            return

        # Search knowledge base for relevant context (RAG)
        context = ""
        if self.knowledge_base:
            kb_results = await self.knowledge_base.search(
                user_text,
                n_results=3,
                client_id=self.session_id,
            )
            if kb_results:
                context = "\n\nRelevant information:\n" + "\n".join(
                    f"- {r['text']}" for r in kb_results[:2]
                )

        # Add user message to LLM conversation
        if self.llm:
            self.llm.add_message(self.session_id, "user", user_text)

            # Build augmented prompt with context
            augmented_prompt = user_text
            if context:
                augmented_prompt += f"\n\n{context}"

            # Add extracted context hints
            context_hints = []
            if self.caller_name:
                context_hints.append(f"Caller name: {self.caller_name}")
            if self.caller_phone:
                context_hints.append(f"Caller phone: {self.caller_phone}")
            if self.extracted_intent:
                context_hints.append(f"Detected intent: {self.extracted_intent}")

            if context_hints:
                augmented_prompt += "\n\n" + "\n".join(context_hints)

            # Get streaming response
            response_text = ""
            async for chunk in self.llm.chat_stream(
                messages=[{"role": "user", "content": augmented_prompt}],
            ):
                if chunk["type"] == "tool_call":
                    await self._handle_tool_call(chunk)
                elif chunk["type"] == "text":
                    content = chunk["content"]
                    response_text += content
                    yield content

            if response_text:
                self.call_transcript.append({"role": "assistant", "content": response_text})
                logger.debug(f"Agent: {response_text[:100]}...")
        else:
            yield "I'm sorry, I'm having trouble processing your request right now."

    # ─── Context Extraction ────────────────────────────────────────────

    def _extract_context(self, text: str):
        """Extract caller information from text."""
        name = extract_name(text)
        if name:
            self.caller_name = name
            logger.info(f"Detected caller name: {name}")

        phone = extract_phone(text)
        if phone:
            self.caller_phone = phone
            logger.info(f"Detected caller phone: {phone}")

    def _detect_intent(self, text: str):
        """Detect caller intent."""
        intent, confidence = extract_intent(text)
        if confidence > 0.5:
            self.extracted_intent = intent
            logger.info(f"Detected intent: {intent} ({confidence:.2f})")

    def _check_bail(self, text: str) -> bool:
        """Check if the user is indicating they want to end the call."""
        text_lower = text.lower().strip()
        for word in BAIL_WORDS:
            if text_lower == word or text_lower.startswith(word):
                logger.info(f"Bail word detected: '{word}'")
                return True
        return False

    async def _generate_farewell(self) -> str:
        """Generate farewell message."""
        if self.caller_name:
            return f"Thank you for calling, {self.caller_name}. Have a great day!"
        return "Thank you for calling. Have a great day!"

    async def _handle_tool_call(self, tool_call: dict):
        """
        Handle a tool/function call from the LLM.

        Args:
            tool_call: Dict with "name" and "arguments" keys
        """
        try:
            function_name = tool_call.get("name", "")
            arguments = tool_call.get("arguments", {})

            # Arguments might come as a JSON string from Ollama
            if isinstance(arguments, str):
                arguments = json.loads(arguments)

            if self.llm and function_name:
                result = await self.llm.execute_function(function_name, arguments)
                self.llm.add_message(
                    self.session_id,
                    "tool",
                    f"Function '{function_name}' result: {result}",
                )
                logger.info(f"Tool call '{function_name}' completed")
        except Exception as e:
            logger.error(f"Tool call handling failed: {e}")

    # ─── Pipeline Integration ──────────────────────────────────────────

    async def process_audio(self, audio_chunk: bytes) -> Optional[bytes]:
        """
        Process an incoming audio chunk through the full pipeline.

        Args:
            audio_chunk: PCM audio data from the caller

        Returns:
            Response audio bytes, or None if no response yet
        """
        if not self.stt:
            logger.warning("STT service not available")
            return None

        # STT: transcribe
        text = await self.stt.transcribe_bytes(audio_chunk)
        if not text:
            return None

        # LLM + TTS: process and generate response
        response_text = ""
        async for chunk in self.process_turn(text):
            response_text += chunk

        if not response_text:
            return None

        # TTS: generate audio
        if self.tts:
            audio = await self.tts.generate(response_text)
            return audio

        return None

    async def end(self):
        """End the conversation session."""
        self.is_active = False
        self._running = False

        # Log to CRM
        if self.crm and self.session_id:
            duration = time.time() - self.conversation_start if self.conversation_start else 0
            try:
                self.crm.log_call(
                    session_id=self.session_id,
                    caller_name=self.caller_name or "",
                    caller_phone=self.caller_phone or "",
                    intent=self.extracted_intent or "",
                    duration_seconds=int(duration),
                    outcome="completed" if self.call_transcript else "no_response",
                    booking_made=self.extracted_intent == "booking",
                    sentiment="",
                )
            except Exception as e:
                logger.error(f"CRM logging failed: {e}")

        logger.info(f"Session ended: {self.session_id} (duration: {duration:.1f}s)")

    # ─── Health ────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get current session statistics."""
        return {
            "agent": self.agent_name,
            "industry": self.industry,
            "business": self.business_name,
            "session_id": self.session_id,
            "active": self.is_active,
            "caller_name": self.caller_name,
            "caller_phone": self.caller_phone,
            "intent": self.extracted_intent,
            "turns": len(self.call_transcript) // 2,
        }
