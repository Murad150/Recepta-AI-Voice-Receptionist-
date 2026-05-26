"""
Recepta - Law Firm Agent "Michael"
Voice agent for law firms: intake, consultation scheduling, case triage.
"""

from typing import AsyncGenerator, Optional
from agents.base_agent import BaseVoiceAgent
from utils.logger import get_logger

logger = get_logger(__name__)


class LegalAgent(BaseVoiceAgent):
    """
    Michael — Professional, formal legal intake specialist.

    Handles:
    - Initial client intake and case type determination
    - Consultation scheduling with appropriate attorney
    - Urgency/deadline assessment
    - Client information collection
    """

    def __init__(self, business_name: str, **services):
        super().__init__("legal", business_name, **services)
        self.case_type: Optional[str] = None
        self.has_deadline: bool = False
        self.consultation_type: Optional[str] = None  # phone, video, in-person
        logger.info(f"Legal Agent '{self.agent_name}' ready for {business_name}")

    async def handle_greeting(self) -> str:
        return (
            f"Thank you for reaching out to {self.business_name}. "
            f"This is Michael speaking — I'll be handling your initial intake today. "
            f"Could you tell me a bit about what brings you to our firm?"
        )

    async def process_turn(self, user_text: str) -> AsyncGenerator[str, None]:
        text_lower = user_text.lower()

        # Detect case type
        case_types = {
            "personal injury": ["car accident", "slip and fall", "injury", "accident"],
            "family law": ["divorce", "custody", "child support", "prenup", "separation"],
            "criminal defense": ["charged", "arrested", "criminal", "dui", "misdemeanor"],
            "real estate": ["closing", "property", "title", "landlord", "eviction"],
            "business law": ["contract", "llc", "incorporation", "partnership"],
            "estate planning": ["will", "trust", "probate", "estate", "inheritance"],
            "immigration": ["visa", "green card", "citizenship", "deportation"],
            "employment law": ["fired", "terminated", "discrimination", "wrongful"],
            "bankruptcy": ["bankruptcy", "debt", "chapter 7", "chapter 11"],
        }

        for case_type, keywords in case_types.items():
            if any(kw in text_lower for kw in keywords):
                self.case_type = case_type
                logger.info(f"Detected case type: {case_type}")
                break

        # Detect urgency/deadlines
        deadline_keywords = [
            "deadline", "statute", "expiring", "court date", "hearing",
            "served", "summons", "rush", "emergency", "time sensitive",
        ]
        if any(kw in text_lower for kw in deadline_keywords):
            self.has_deadline = True
            logger.info("Time-sensitive legal matter detected")

        async for chunk in super().process_turn(user_text):
            yield chunk
