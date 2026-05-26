"""
Recepta - Helper Utilities
General-purpose functions used across the system.
"""

import re
import json
import asyncio
import unicodedata
from datetime import datetime, timedelta
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


# ─── Text Processing ─────────────────────────────────────────────────────────

def extract_name(text: str) -> Optional[str]:
    """
    Simple rule-based name extraction from conversation text.
    Looks for "my name is X", "I'm X", "this is X" patterns.

    Args:
        text: Raw transcription text

    Returns:
        Extracted name or None
    """
    patterns = [
        r"(?:my name is|my name's)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:i'm|i am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:call me)\s+([A-Z][a-z]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            name = match.group(1).strip().title()
            logger.debug(f"Extracted name: {name}")
            return name
    return None


def extract_phone(text: str) -> Optional[str]:
    """
    Extract phone number from text. Handles US/UK formats.

    Args:
        text: Raw transcription text

    Returns:
        Normalized phone number or None
    """
    # Remove common filler words around numbers
    cleaned = re.sub(r'(?:my number is|my phone|reach me at|call me at|at)\s*', '', text, flags=re.IGNORECASE)

    patterns = [
        r'(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}',
        r'\+\d{1,3}[\s.-]?\d{3}[\s.-]?\d{3}[\s.-]?\d{4}',
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            phone = re.sub(r'[\s\(\)\-\.]', '', match.group())
            logger.debug(f"Extracted phone: {phone}")
            return phone
    return None


def extract_time_reference(text: str) -> Optional[str]:
    """
    Extract time references from text (e.g., "tomorrow at 2pm", "next Monday").

    Args:
        text: Raw transcription text

    Returns:
        Extracted time reference string or None
    """
    patterns = [
        r'(?:this|next|coming)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
        r'(?:tomorrow|today|day after tomorrow)',
        r'(?:\d{1,2})(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)',
        r'(?:at\s+)\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return match.group()
    return None


def extract_intent(text: str) -> tuple:
    """
    Detect caller intent from transcribed text.

    Args:
        text: Raw transcription text

    Returns:
        Tuple of (intent: str, confidence: float)
    """
    text_lower = text.lower()

    # Intent classifications with keyword matching
    intents = {
        "booking": [
            r"(?:schedule|book|appointment|set up|meeting|consultation|visit|see the)",
            r"(?:i(?:'d| would) like to (?:schedule|book|make|set up))",
            r"(?:need to see|want to come in|looking for)",
        ],
        "emergency": [
            r"(?:emergency|urgent|asap|right away|immediately|cannot wait|can't wait)",
            r"(?:severe|terrible|horrible)\s+(?:pain|bleeding|leak|flood|no (?:heat|cooling))",
            r"(?:burst pipe|gas smell|flooding|broken)",
        ],
        "faq": [
            r"(?:question|wondering|how much|what time|do you|are you)",
            r"(?:hours|open|close|location|address|cost|price|fee)",
            r"(?:insurance|accept|covered)",
        ],
        "complaint": [
            r"(?:complaint|unhappy|dissatisfied|disappointed|terrible service)",
            r"(?:wrong|incorrect|mistake|error|issue with|problem with)",
            r"(?:want to speak to (?:a manager|supervisor|someone else))",
        ],
        "cancel": [
            r"(?:cancel|reschedule|change|move|postpone)",
            r"(?:can't make it|can not make it|need to change)",
        ],
        "information": [
            r"(?:tell me about|what is|how does|do you offer|information about)",
            r"(?:services|products|offer|provide)",
        ],
    }

    best_intent = "general"
    best_score = 0.0

    for intent, patterns in intents.items():
        score = 0.0
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            score += len(matches) * 0.3
        if score > best_score:
            best_score = score
            best_intent = intent

    # Normalize confidence
    confidence = min(best_score, 1.0)
    if best_score == 0:
        confidence = 0.3  # Default for "general"

    logger.debug(f"Detected intent: {best_intent} (confidence: {confidence:.2f})")
    return best_intent, confidence


# ─── Time Helpers ────────────────────────────────────────────────────────────

def generate_time_slots(
    start_hour: int = 9,
    end_hour: int = 17,
    interval_minutes: int = 30,
    num_slots: int = 2,
) -> list:
    """
    Generate available time slots for booking.

    Args:
        start_hour: Hour to start (24h format)
        end_hour: Hour to end
        interval_minutes: Minutes between slots
        num_slots: Number of slots to return

    Returns:
        List of formatted time slot strings like ["10:00 AM", "10:30 AM"]
    """
    now = datetime.now()
    # Start from tomorrow if past end_hour
    base_date = now + timedelta(days=1) if now.hour >= end_hour else now

    start = base_date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    end = base_date.replace(hour=end_hour, minute=0, second=0, microsecond=0)

    slots = []
    current = start
    while current <= end and len(slots) < 20:  # Generate pool
        if current > now:
            slots.append(current.strftime("%I:%M %p").lstrip("0"))
        current += timedelta(minutes=interval_minutes)

    # Return requested number
    return slots[:num_slots]


def format_appointment_time(dt: datetime) -> str:
    """Format a datetime object for natural speech."""
    day = dt.strftime("%A")  # Monday, Tuesday, etc.
    time = dt.strftime("%I:%M %p").lstrip("0")
    return f"{day} at {time}"


# ─── Audio Helpers ───────────────────────────────────────────────────────────

def convert_audio_bytes_to_text(audio_bytes: bytes, sample_rate: int = 16000) -> bytes:
    """
    Ensure audio bytes are in the correct format for processing.
    Placeholder — actual conversion depends on audio format from transport.

    Args:
        audio_bytes: Raw audio bytes
        sample_rate: Target sample rate

    Returns:
        Processed audio bytes
    """
    # In production, use librosa or pydub for conversion
    return audio_bytes


# ─── General Helpers ─────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def safe_json_loads(text: str, default: any = None) -> any:
    """Safely parse JSON, returning default on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def truncate_text(text: str, max_words: int = 100) -> str:
    """Truncate text to a maximum number of words."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."
