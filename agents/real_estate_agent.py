"""
Recepta - Real Estate Agent "Jessica"
Voice agent for real estate agencies: buyer/showing, seller/listings, market info.
"""

from typing import AsyncGenerator, Optional
from agents.base_agent import BaseVoiceAgent
from utils.logger import get_logger

logger = get_logger(__name__)


class RealEstateAgent(BaseVoiceAgent):
    """
    Jessica — Enthusiastic, knowledgeable real estate showing coordinator.

    Handles:
    - Buyer qualification and property matching
    - Property viewing scheduling
    - Seller consultation booking
    - Market information and area questions
    - Open house scheduling
    """

    def __init__(self, business_name: str, **services):
        super().__init__("real_estate", business_name, **services)
        self.client_type: Optional[str] = None  # "buyer", "seller", "browser"
        self.preferred_area: Optional[str] = None
        self.budget_range: Optional[str] = None
        self.property_type: Optional[str] = None
        self.timeline: Optional[str] = None
        logger.info(f"Real Estate Agent '{self.agent_name}' ready for {business_name}")

    async def handle_greeting(self) -> str:
        return (
            f"Hi, thanks for reaching out to {self.business_name}! "
            f"This is Jessica — are you looking to buy, sell, or "
            f"just exploring the market today?"
        )

    async def process_turn(self, user_text: str) -> AsyncGenerator[str, None]:
        text_lower = user_text.lower()

        # Detect client type
        if any(kw in text_lower for kw in ["buy", "looking for", "purchase", "first home"]):
            self.client_type = "buyer"
        elif any(kw in text_lower for kw in ["sell", "listing", "list my", "selling"]):
            self.client_type = "seller"
        elif any(kw in text_lower for kw in ["just looking", "browsing", "exploring"]):
            self.client_type = "browser"

        # Detect areas
        # (In production, this would use a list of known areas from the agency)

        # Detect budget
        budget_patterns = [
            "under", "up to", "budget", "range", "max",
            "around", "between", "no more than",
        ]
        if any(kw in text_lower for kw in budget_patterns):
            # Budget mentioned — will be extracted by LLM
            logger.info("Budget reference detected")

        async for chunk in super().process_turn(user_text):
            yield chunk
