"""
Integration tests for the full Recepta pipeline.
Tests the complete STT -> LLM -> TTS flow with agent logic.
"""

import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.prompts import get_agent_config, AGENT_PROMPTS
from config.settings import OLLAMA_MODEL
from utils.helpers import (
    extract_name,
    extract_phone,
    extract_intent,
    generate_time_slots,
    format_appointment_time,
)


class TestAgentPrompts:
    """Test that all agent prompts are valid."""

    def test_all_industries_have_prompts(self):
        assert "dental" in AGENT_PROMPTS
        assert "legal" in AGENT_PROMPTS
        assert "hvac" in AGENT_PROMPTS
        assert "real_estate" in AGENT_PROMPTS

    def test_prompts_contain_required_elements(self):
        required_elements = [
            "PERSONALITY", "GREETING", "CONVERSATION RULES",
            "BOOKING", "CLOSING",
        ]
        for industry, config in AGENT_PROMPTS.items():
            prompt = config["system_prompt"]
            for element in required_elements:
                assert element in prompt, f"{industry} prompt missing: {element}"

    def test_prompts_have_no_todo_placeholders(self):
        for industry, config in AGENT_PROMPTS.items():
            assert "TODO" not in config["system_prompt"]
            assert "FIXME" not in config["system_prompt"]

    def test_get_agent_config_valid(self):
        config = get_agent_config("dental", "SmileCare Dental")
        assert config["name"] == "Sarah"
        assert "SmileCare Dental" in config["system_prompt"]

    def test_get_agent_config_invalid(self):
        with pytest.raises(ValueError):
            get_agent_config("invalid_industry", "Test")


class TestContextExtraction:
    """Test helper functions for extracting caller information."""

    def test_extract_name_standard(self):
        assert extract_name("My name is John Smith") == "John Smith"
        assert extract_name("I'm Sarah Johnson") == "Sarah Johnson"
        assert extract_name("This is Mike") == "Mike"

    def test_extract_name_variations(self):
        assert extract_name("my name is alice") == "Alice"
        assert extract_name("i am dr brown") == "Dr Brown"
        assert extract_name("call me sam") == "Sam"

    def test_extract_name_none(self):
        assert extract_name("I need to make an appointment") is None
        assert extract_name("Hello, how are you?") is None

    def test_extract_phone_us(self):
        phone = extract_phone("My number is 555-123-4567")
        assert phone == "5551234567"

        phone = extract_phone("Call me at (212) 555-0199")
        assert phone == "2125550199"

    def test_extract_phone_none(self):
        assert extract_phone("I don't have a phone") is None

    def test_extract_intent_booking(self):
        intent, confidence = extract_intent("I'd like to schedule an appointment")
        assert intent == "booking"
        assert confidence > 0.3

    def test_extract_intent_emergency(self):
        intent, confidence = extract_intent("This is an emergency, I have severe pain")
        assert intent == "emergency"
        assert confidence > 0.3

    def test_extract_intent_faq(self):
        intent, confidence = extract_intent("What are your business hours?")
        assert intent == "faq"
        assert confidence > 0.3

    def test_extract_intent_general(self):
        intent, confidence = extract_intent("Hello, how are you today?")
        assert intent == "general"
        assert confidence >= 0.0


class TestTimeHelpers:
    """Test time slot generation helpers."""

    def test_generate_time_slots(self):
        slots = generate_time_slots(9, 17, 30, 2)
        assert len(slots) == 2
        for slot in slots:
            assert "AM" in slot or "PM" in slot

    def test_format_appointment_time(self):
        from datetime import datetime, timedelta
        dt = datetime(2025, 6, 15, 10, 30)
        formatted = format_appointment_time(dt)
        assert "Sunday" in formatted
        assert "10:30" in formatted


class TestKnowledgeBase:
    """Test knowledge base text chunking."""

    def test_chunk_size(self):
        """Simple test for chunking logic."""
        from integrations.knowledge_base import KnowledgeBase
        kb = KnowledgeBase()

        text = "This is a test document. " * 100
        chunks = kb.chunk_text(text, chunk_size=200, overlap=50)
        assert len(chunks) > 1
        assert all(c["start_char"] <= c["end_char"] for c in chunks)

        # Check no chunk is empty
        for chunk in chunks:
            assert chunk["text"].strip(), f"Empty chunk found: {chunk}"
            assert len(chunk["id"]) == 12


class TestPipelineIntegration:
    """Integration tests that require running services."""

    @pytest.mark.asyncio
    async def test_llm_agent_conversation_flow(self):
        """Test a full conversation flow with LLM (if available)."""
        from services.llm_service import LLMService

        llm = LLMService()
        healthy = await llm.health_check()
        if not healthy:
            pytest.skip("Ollama not running")

        session = "test_integration"
        system_prompt = (
            "You are a friendly receptionist. Keep responses under 2 sentences. "
            "Ask for their name and offer 2 appointment times."
        )
        llm.create_conversation(session, system_prompt)
        llm.add_message(session, "user", "Hi, I'd like to book an appointment.")

        response = ""
        async for chunk in llm.chat_stream(
            messages=llm.get_conversation(session)[1:],  # Skip system for this test
            system_prompt=system_prompt,
        ):
            if isinstance(chunk, dict) and chunk.get("type") == "text":
                response += chunk["content"]

        assert len(response) > 10
        await llm.close()

    @pytest.mark.asyncio
    async def test_crm_database_operations(self):
        """Test CRM database operations."""
        import tempfile
        from integrations.crm import CRMIntegration

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        crm = CRMIntegration(db_path)
        crm.connect()

        # Add a client
        client_id = crm.add_client(
            business_name="Test Dental",
            industry="dental",
            contact_name="Dr. Smith",
        )
        assert client_id > 0

        # Get client
        client = crm.get_client(client_id)
        assert client["business_name"] == "Test Dental"
        assert client["industry"] == "dental"

        # Log a call
        call_id = crm.log_call(
            client_id=client_id,
            session_id="test_call_1",
            caller_name="John Doe",
            intent="booking",
            duration_seconds=120,
            outcome="answered",
            booking_made=1,
        )
        assert call_id > 0

        # Get calls
        calls = crm.get_calls(client_id)
        assert len(calls) == 1

        # Add lead
        lead_id = crm.add_lead(
            business_name="Potential Client HVAC",
            industry="hvac",
            source="cold_email",
        )
        assert lead_id > 0

        # Update lead
        crm.update_lead_status(lead_id, "contacted")
        leads = crm.list_leads(status="contacted")
        assert len(leads) >= 1

        crm.close()
        import os
        os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_full_main_imports(self):
        """Test that all modules can be imported without errors."""
        from services.stt_service import STTService
        from services.llm_service import LLMService
        from services.tts_service import TTSService
        from services.transport_service import TransportService
        from integrations.calendar import CalendarIntegration
        from integrations.crm import CRMIntegration
        from integrations.knowledge_base import KnowledgeBase
        from agents.dental_agent import DentalAgent
        from agents.legal_agent import LegalAgent
        from agents.hvac_agent import HVACAgent
        from agents.real_estate_agent import RealEstateAgent
        from config.prompts import get_agent_config

        assert True
