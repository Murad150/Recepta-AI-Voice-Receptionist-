"""
Tests for LLM Service (Ollama).
"""

import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.llm_service import LLMService


@pytest.fixture
def llm_service():
    """Create LLM service instance."""
    return LLMService()


@pytest.mark.asyncio
async def test_llm_initialization(llm_service):
    """Test that LLM service initializes correctly."""
    assert llm_service is not None
    assert llm_service.model is not None
    assert "llama" in llm_service.model


@pytest.mark.asyncio
async def test_llm_conversation_management(llm_service):
    """Test conversation create, add, get."""
    session_id = "test_session_1"
    llm_service.create_conversation(session_id, "You are a helpful assistant.")

    messages = llm_service.get_conversation(session_id)
    assert len(messages) == 1
    assert messages[0]["role"] == "system"

    llm_service.add_message(session_id, "user", "Hello!")
    messages = llm_service.get_conversation(session_id)
    assert len(messages) == 2
    assert messages[1]["content"] == "Hello!"


@pytest.mark.asyncio
async def test_llm_conversation_clear(llm_service):
    """Test clearing conversation preserves system prompt."""
    session_id = "test_session_2"
    llm_service.create_conversation(session_id, "System prompt here.")
    llm_service.add_message(session_id, "user", "Message")
    llm_service.add_message(session_id, "assistant", "Response")

    llm_service.clear_conversation(session_id)
    messages = llm_service.get_conversation(session_id)
    assert len(messages) == 1
    assert messages[0]["role"] == "system"


@pytest.mark.asyncio
async def test_llm_health_check(llm_service):
    """Test health check endpoint."""
    healthy = await llm_service.health_check()
    if not healthy:
        pytest.skip("Ollama server not running")
    assert healthy


@pytest.mark.asyncio
async def test_llm_basic_chat(llm_service):
    """Test basic chat completion (requires Ollama running)."""
    healthy = await llm_service.health_check()
    if not healthy:
        pytest.skip("Ollama server not available")

    response = await llm_service.chat(
        messages=[{"role": "user", "content": "Say 'Hello, world!' and nothing else."}],
    )
    assert response is not None
    assert len(response) > 0


@pytest.mark.asyncio
async def test_llm_streaming(llm_service):
    """Test streaming chat completion."""
    healthy = await llm_service.health_check()
    if not healthy:
        pytest.skip("Ollama server not available")

    chunks = []
    async for chunk in llm_service.chat_stream(
        messages=[{"role": "user", "content": "Count from 1 to 3."}],
    ):
        if isinstance(chunk, dict) and chunk.get("type") == "text":
            chunks.append(chunk["content"])

    full_response = "".join(chunks)
    assert len(full_response) > 0


@pytest.mark.asyncio
async def test_llm_embedding(llm_service):
    """Test embedding generation."""
    healthy = await llm_service.health_check()
    if not healthy:
        pytest.skip("Ollama server not available")

    embedding = await llm_service.get_embedding("Test text for embedding")
    assert len(embedding) > 0
    assert all(isinstance(v, float) for v in embedding)


@pytest.mark.asyncio
async def test_llm_function_registration(llm_service):
    """Test function/tool registration and execution."""
    async def get_weather(city: str) -> str:
        return f"Weather in {city}: Sunny, 72°F"

    llm_service.register_function("get_weather", get_weather)

    result = await llm_service.execute_function("get_weather", {"city": "New York"})
    assert "Sunny" in result
    assert "New York" in result

    # Test unknown function
    error_result = await llm_service.execute_function("unknown_func", {})
    assert "error" in error_result


@pytest.mark.asyncio
async def test_llm_cleanup(llm_service):
    """Test proper cleanup."""
    await llm_service.close()
    assert llm_service._session is None or llm_service._session.closed
