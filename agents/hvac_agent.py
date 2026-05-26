"""
Recepta - HVAC Company Agent "Mike"
Voice agent for HVAC companies: service dispatch, emergency triage, scheduling.
"""

from typing import AsyncGenerator, Optional
from agents.base_agent import BaseVoiceAgent
from utils.logger import get_logger

logger = get_logger(__name__)


class HVACAgent(BaseVoiceAgent):
    """
    Mike — Friendly, reliable HVAC dispatcher.

    Handles:
    - Service call intake and triage
    - Emergency dispatch (no heat/AC, gas smell)
    - Routine maintenance scheduling
    - Address and contact collection
    - Technician dispatch coordination
    """

    def __init__(self, business_name: str, **services):
        super().__init__("hvac", business_name, **services)
        self.is_emergency: bool = False
        self.system_type: Optional[str] = None  # "heating", "cooling", "both"
        self.service_address: Optional[str] = None
        self.is_existing_customer: Optional[bool] = None
        logger.info(f"HVAC Agent '{self.agent_name}' ready for {business_name}")

    async def handle_greeting(self) -> str:
        return (
            f"Thanks for calling {self.business_name}, this is Mike. "
            f"Are you having an issue with your heating or cooling system today?"
        )

    async def process_turn(self, user_text: str) -> AsyncGenerator[str, None]:
        text_lower = user_text.lower()

        # Detect system type
        if any(kw in text_lower for kw in ["heat", "furnace", "boiler", "cold", "heating"]):
            self.system_type = "heating"
        elif any(kw in text_lower for kw in ["ac", "cooling", "air conditioner", "a/c", "cold air"]):
            self.system_type = "cooling"

        # Detect emergency
        emergency_keywords = [
            "no heat", "no cooling", "gas smell", "carbon monoxide",
            "flood", "burst pipe", "emergency", "freezing", "90 degrees",
            "can't breathe", "smoke", "burning smell",
        ]
        if any(kw in text_lower for kw in emergency_keywords):
            self.is_emergency = True
            logger.info("Emergency detected in HVAC call")

        async for chunk in super().process_turn(user_text):
            yield chunk
