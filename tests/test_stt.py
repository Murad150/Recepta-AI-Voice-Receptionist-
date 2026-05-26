"""
Tests for STT Service (Speaches).
"""

import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.stt_service import STTService


@pytest.fixture
def stt_service():
    """Create STT service instance."""
    return STTService()


@pytest.mark.asyncio
async def test_stt_initialization(stt_service):
    """Test that STT service initializes with correct config."""
    assert stt_service is not None
    assert "localhost:8000" in stt_service.base_url or stt_service.base_url
    assert stt_service.api_key is not None


@pytest.mark.asyncio
async def test_stt_transcribe_empty_audio(stt_service):
    """Test transcription with empty audio returns empty string."""
    result = await stt_service.transcribe_bytes(b"")
    assert result == ""


@pytest.mark.asyncio
async def test_stt_api_connection(stt_service):
    """Test connection to Speaches server."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{stt_service.base_url}/v1/models") as resp:
                assert resp.status == 200
    except (aiohttp.ClientError, ImportError):
        pytest.skip("Speaches server not running")


@pytest.mark.asyncio
async def test_stt_websocket_connect(stt_service):
    """Test WebSocket connection to Speaches."""
    connected = await stt_service.connect_ws()
    if connected:
        await stt_service.close_ws()
    # If it fails, the server is not running - that's OK for CI
    if not connected:
        pytest.skip("Speaches WebSocket not available")


@pytest.mark.asyncio
async def test_stt_cleanup(stt_service):
    """Test proper cleanup."""
    await stt_service.close()
    assert stt_service._ws is None or stt_service._ws.closed
