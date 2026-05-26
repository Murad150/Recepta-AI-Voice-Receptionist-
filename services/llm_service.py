"""
Recepta - LLM Service (Ollama)
Connects to local Ollama server with streaming support.
Compatible with Pipecat FrameProcessor pattern and function calling.
"""

import json
import asyncio
from typing import AsyncGenerator, Callable, Optional

import aiohttp

from config.settings import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_EMBEDDING_MODEL,
    OLLAMA_STREAM,
    OLLAMA_TIMEOUT,
    OLLAMA_TEMPERATURE,
    OLLAMA_MAX_TOKENS,
    OLLAMA_CONTEXT_LENGTH,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class LLMService:
    """
    LLM Service using Ollama (local Llama 3.2).

    Provides:
    - Streaming chat completions
    - Function/tool calling support
    - Text embeddings for RAG
    - Conversation history management
    """

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL.rstrip("/")
        self.model = OLLAMA_MODEL
        self.embedding_model = OLLAMA_EMBEDDING_MODEL
        self.temperature = OLLAMA_TEMPERATURE
        self.max_tokens = OLLAMA_MAX_TOKENS
        self.context_length = OLLAMA_CONTEXT_LENGTH
        self.stream = OLLAMA_STREAM

        # Registered function tools
        self._functions: dict[str, Callable] = {}
        # Conversation history store: {session_id: [messages]}
        self._conversations: dict[str, list] = {}

        self._session: Optional[aiohttp.ClientSession] = None
        logger.info(f"LLM Service initialized (model={self.model})")

    async def ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

    # ─── Basic Chat Completion ──────────────────────────────────────────────

    async def chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        tools: Optional[list[dict]] = None,
    ) -> str:
        """
        Send a chat message to Ollama and get a full response.

        Args:
            messages: List of {"role": "...", "content": "..."} messages
            system_prompt: Optional system prompt override
            tools: Optional list of tool definitions for function calling

        Returns:
            Response text from the model
        """
        await self.ensure_session()

        full_messages = list(messages)
        if system_prompt:
            full_messages.insert(0, {"role": "system", "content": system_prompt})

        payload = {
            "model": self.model,
            "messages": full_messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }

        if tools:
            payload["tools"] = tools

        try:
            async with self._session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=OLLAMA_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Ollama chat error ({resp.status}): {error_text}")
                    return "I'm sorry, I'm having trouble processing your request right now."

                result = await resp.json()
                return result.get("message", {}).get("content", "")

        except asyncio.TimeoutError:
            logger.error("Ollama chat timed out")
            return "I apologize, but I need a moment longer to think. Could you please repeat that?"
        except aiohttp.ClientError as e:
            logger.error(f"Ollama connection error: {e}")
            return "I'm having trouble connecting to my brain. Please bear with me."

    # ─── Streaming Chat ─────────────────────────────────────────────────────

    async def chat_stream(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        tools: Optional[list[dict]] = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream chat completion from Ollama token by token.

        Args:
            messages: Conversation messages
            system_prompt: Optional system prompt
            tools: Optional tool definitions

        Yields:
            Dicts with type "text" or "tool_call".
            - {"type": "text", "content": "generated text"}
            - {"type": "tool_call", "name": "...", "arguments": {...}}
        """
        await self.ensure_session()

        full_messages = list(messages)
        if system_prompt:
            full_messages.insert(0, {"role": "system", "content": system_prompt})

        payload = {
            "model": self.model,
            "messages": full_messages,
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }

        if tools:
            payload["tools"] = tools

        try:
            async with self._session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=OLLAMA_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Ollama stream error ({resp.status}): {error_text}")
                    yield {"type": "text", "content": "I'm sorry, I encountered an error."}
                    return

                # Process SSE stream
                async for line in resp.content:
                    if line:
                        line = line.decode("utf-8").strip()
                        if line.startswith("data: "):
                            line = line[6:]
                        try:
                            chunk = json.loads(line)
                            if "message" in chunk:
                                content = chunk["message"].get("content", "")
                                if content:
                                    yield {"type": "text", "content": content}
                                # Check for tool calls
                                if "tool_calls" in chunk["message"]:
                                    for tc in chunk["message"]["tool_calls"]:
                                        yield {
                                            "type": "tool_call",
                                            "name": tc.get("function", {}).get("name", ""),
                                            "arguments": tc.get("function", {}).get("arguments", {}),
                                        }
                        except json.JSONDecodeError:
                            continue

        except asyncio.TimeoutError:
            logger.error("Ollama stream timed out")
            yield {"type": "text", "content": "I apologize for the delay. Could you repeat that?"}
        except aiohttp.ClientError as e:
            logger.error(f"Ollama stream connection error: {e}")
            yield {"type": "text", "content": "I'm experiencing technical difficulties."}

    # ─── Conversation Management ────────────────────────────────────────────

    def create_conversation(self, session_id: str, system_prompt: str = ""):
        """Create a new conversation session."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        self._conversations[session_id] = messages
        logger.debug(f"Created conversation: {session_id}")

    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to conversation history."""
        if session_id not in self._conversations:
            self._conversations[session_id] = []
        self._conversations[session_id].append({"role": role, "content": content})
        # Trim context window if too long (rough token estimation)
        self._trim_conversation(session_id)

    def _trim_conversation(self, session_id: str):
        """Trim conversation to stay within context window."""
        messages = self._conversations.get(session_id, [])
        total_chars = sum(len(m.get("content", "")) for m in messages)
        # Rough: 1 token ≈ 4 chars, leave room for response
        max_chars = self.context_length * 3
        while total_chars > max_chars and len(messages) > 2:
            removed = messages.pop(1) if len(messages) > 2 else messages.pop(0)  # Keep system prompt
            total_chars -= len(removed.get("content", ""))

    def get_conversation(self, session_id: str) -> list[dict]:
        """Get conversation history for a session."""
        return self._conversations.get(session_id, [])

    def clear_conversation(self, session_id: str):
        """Clear conversation history."""
        if session_id in self._conversations:
            messages = self._conversations[session_id]
            system_msg = messages[0] if messages and messages[0]["role"] == "system" else None
            self._conversations[session_id] = [system_msg] if system_msg else []
            logger.debug(f"Cleared conversation: {session_id}")

    # ─── Function/Tool Calling Registration ────────────────────────────────

    def register_function(self, name: str, func: Callable):
        """
        Register a function that the LLM can call.

        Args:
            name: Function name the LLM will use
            func: Async callable to execute
        """
        self._functions[name] = func
        logger.debug(f"Registered function: {name}")

    async def execute_function(self, name: str, arguments: dict) -> str:
        """
        Execute a registered function call from the LLM.

        Args:
            name: Function name
            arguments: Dict of arguments

        Returns:
            Function result as string
        """
        func = self._functions.get(name)
        if not func:
            logger.warning(f"Unknown function called: {name}")
            return json.dumps({"error": f"Unknown function: {name}"})

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)
            logger.info(f"Function '{name}' executed successfully")
            return json.dumps({"result": result})
        except Exception as e:
            logger.error(f"Function '{name}' failed: {e}")
            return json.dumps({"error": str(e)})

    # ─── Embeddings for RAG ─────────────────────────────────────────────────

    async def get_embedding(self, text: str) -> list[float]:
        """
        Get embedding vector for text using Ollama.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding
        """
        await self.ensure_session()

        payload = {
            "model": self.embedding_model,
            "prompt": text,
        }

        try:
            async with self._session.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    logger.error(f"Embedding error ({resp.status})")
                    return []
                result = await resp.json()
                return result.get("embedding", [])
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return []

    async def health_check(self) -> bool:
        """Check if Ollama is running and the model is loaded."""
        try:
            await self.ensure_session()
            async with self._session.get(
                f"{self.base_url}/api/tags",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    return False
                data = await resp.json()
                models = [m["name"] for m in data.get("models", [])]
                # Check if our model is available
                for m in models:
                    if self.model in m:
                        logger.info(f"Ollama health check passed - {self.model} available")
                        return True
                logger.warning(f"Model {self.model} not found in {models}")
                return False
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def close(self):
        """Cleanup resources."""
        if self._session and not self._session.closed:
            await self._session.close()
        logger.info("LLM Service shut down")
