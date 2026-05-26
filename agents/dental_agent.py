"""
Recepta - Dental Clinic Agent "Sarah"
Voice agent for dental practices: booking, insurance, emergency triage.
"""

from typing import AsyncGenerator, Optional
from agents.base_agent import BaseVoiceAgent
from utils.logger import get_logger

logger = get_logger(__name__)


class DentalAgent(BaseVoiceAgent):
    """
    Sarah — Warm, professional dental receptionist.

    Handles:
    - Appointment booking (checkups, cleanings, procedures)
    - New patient intake
    - Emergency triage (pain, swelling, trauma)
    - Insurance information collection
    - FAQ (hours, services, location)
    """

    def __init__(self, business_name: str, **services):
        super().__init__("dental", business_name, **services)
        self.patient_type: Optional[str] = None  # "new" or "existing"
        self.preferred_dentist: Optional[str] = None
        self.reason_for_visit: Optional[str] = None
        self.is_emergency: bool = False
        logger.info(f"Dental Agent '{self.agent_name}' ready for {business_name}")

    async def handle_greeting(self) -> str:
        return (
            f"Hi, thank you for calling {self.business_name}. "
            f"This is Sarah — are you calling to schedule an appointment, "
            f"or is there something specific we can help you with?"
        )

    async def process_turn(self, user_text: str) -> AsyncGenerator[str, None]:
        # Detect emergency keywords early
        emergency_keywords = [
            "severe pain", "emergency", "bleeding", "swelling",
            "knocked out", "broken tooth", "abscess", "can't stop",
            "urgent", "right now", "asap",
        ]
        text_lower = user_text.lower()
        if any(kw in text_lower for kw in emergency_keywords):
            self.is_emergency = True
            logger.info("Emergency detected in dental call")

        # Detect new vs existing patient
        if any(phrase in text_lower for phrase in ["first time", "new patient", "never been"]):
            self.patient_type = "new"
        elif any(phrase in text_lower for phrase in ["i'm a patient", "i've been"]):
            self.patient_type = "existing"

        # Detect reason
        visit_reasons = [
            "checkup", "cleaning", "exam", "toothache", "pain",
            "filling", "crown", "extraction", "whitening", "implant",
            "root canal", "x-ray", "consultation",
        ]
        for reason in visit_reasons:
            if reason in text_lower:
                self.reason_for_visit = reason
                break

        async for chunk in super().process_turn(user_text):
            yield chunk
