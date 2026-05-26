"""
Recepta - Google Calendar Integration
Handles appointment booking, checking availability, and event management.
"""

import os
import json
import pickle
from datetime import datetime, timedelta
from typing import Optional

from config.settings import (
    GOOGLE_CALENDAR_CREDENTIALS_FILE,
    GOOGLE_CALENDAR_TOKEN_FILE,
    GOOGLE_CALENDAR_SCOPES,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class CalendarIntegration:
    """
    Google Calendar integration for booking appointments.

    Uses OAuth 2.0 for authentication (free tier, no API costs).
    Supports:
    - Check availability
    - Create appointments
    - Cancel/reschedule
    - List upcoming events
    """

    def __init__(self):
        self.credentials_file = GOOGLE_CALENDAR_CREDENTIALS_FILE
        self.token_file = GOOGLE_CALENDAR_TOKEN_FILE
        self.scopes = GOOGLE_CALENDAR_SCOPES
        self._service = None
        logger.info("Calendar Integration initialized")

    async def authenticate(self) -> bool:
        """
        Authenticate with Google Calendar API using OAuth 2.0.

        Returns:
            True if authentication succeeded
        """
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            creds = None

            # Try loading existing token
            if os.path.exists(self.token_file):
                try:
                    with open(self.token_file, "rb") as token:
                        creds = pickle.load(token)
                except Exception as e:
                    logger.warning(f"Could not load token file: {e}")

            # If no valid credentials, run OAuth flow
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_file):
                        logger.error(
                            f"Google credentials file not found: {self.credentials_file}\n"
                            "See .env.example for setup instructions."
                        )
                        return False

                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.scopes
                    )
                    creds = flow.run_local_server(port=0)

                # Save token for future use
                with open(self.token_file, "wb") as token:
                    pickle.dump(creds, token)
                logger.info("OAuth token saved")

            # Build the service
            self._service = build("calendar", "v3", credentials=creds)
            logger.info("Google Calendar authenticated successfully")
            return True

        except ImportError:
            logger.error(
                "Google API client not installed. "
                "Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )
            return False
        except Exception as e:
            logger.error(f"Google Calendar authentication failed: {e}")
            return False

    def _ensure_service(self):
        """Ensure the calendar service is initialized."""
        if self._service is None:
            raise RuntimeError(
                "Calendar not authenticated. Call authenticate() first."
            )

    # ─── Availability ─────────────────────────────────────────────────────

    async def check_availability(
        self,
        date: str,
        duration_minutes: int = 30,
        timezone: str = "America/New_York",
    ) -> list[dict]:
        """
        Check available time slots for a given date.

        Args:
            date: Date string in YYYY-MM-DD format
            duration_minutes: Length of appointment in minutes
            timezone: IANA timezone string

        Returns:
            List of available {start, end} time dicts
        """
        self._ensure_service()

        try:
            # Define business hours (9 AM to 5 PM)
            start_of_day = f"{date}T09:00:00-05:00"
            end_of_day = f"{date}T17:00:00-05:00"

            # Get existing events
            events_result = (
                self._service.events()
                .list(
                    calendarId="primary",
                    timeMin=start_of_day,
                    timeMax=end_of_day,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])

            # Calculate available slots
            available_slots = []
            current_time = datetime.fromisoformat(start_of_day)
            end_time = datetime.fromisoformat(end_of_day)

            while current_time + timedelta(minutes=duration_minutes) <= end_time:
                slot_end = current_time + timedelta(minutes=duration_minutes)

                # Check if slot conflicts with existing events
                is_available = True
                for event in events:
                    event_start = datetime.fromisoformat(
                        event["start"].get("dateTime", event["start"].get("date"))
                    )
                    event_end = datetime.fromisoformat(
                        event["end"].get("dateTime", event["end"].get("date"))
                    )

                    # Check overlap
                    if current_time < event_end and slot_end > event_start:
                        is_available = False
                        break

                if is_available:
                    available_slots.append({
                        "start": current_time.isoformat(),
                        "end": slot_end.isoformat(),
                    })

                current_time += timedelta(minutes=30)  # 30-min increments

            logger.info(f"Found {len(available_slots)} available slots on {date}")
            return available_slots

        except Exception as e:
            logger.error(f"Availability check failed: {e}")
            return []

    # ─── Booking ─────────────────────────────────────────────────────────

    async def book_appointment(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
        attendee_email: str = "",
        timezone: str = "America/New_York",
    ) -> Optional[str]:
        """
        Create a new calendar event (appointment).

        Args:
            summary: Event title (e.g., "Dental Checkup - John Doe")
            start_time: ISO 8601 start time
            end_time: ISO 8601 end time
            description: Event description/notes
            attendee_email: Optional attendee email for invitation
            timezone: IANA timezone

        Returns:
            Event ID if successful, None otherwise
        """
        self._ensure_service()

        event = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_time,
                "timeZone": timezone,
            },
            "end": {
                "dateTime": end_time,
                "timeZone": timezone,
            },
        }

        if attendee_email:
            event["attendees"] = [{"email": attendee_email}]
            event["reminders"] = {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},
                    {"method": "popup", "minutes": 30},
                ],
            }

        try:
            created_event = (
                self._service.events()
                .insert(calendarId="primary", body=event, sendUpdates="all")
                .execute()
            )
            event_id = created_event.get("id")
            logger.info(f"Appointment booked: {summary} (ID: {event_id})")
            return event_id

        except Exception as e:
            logger.error(f"Appointment booking failed: {e}")
            return None

    # ─── Reschedule ─────────────────────────────────────────────────────

    async def reschedule_appointment(
        self,
        event_id: str,
        new_start_time: str,
        new_end_time: str,
    ) -> bool:
        """
        Reschedule an existing appointment.

        Args:
            event_id: Google Calendar event ID
            new_start_time: New ISO 8601 start time
            new_end_time: New ISO 8601 end time

        Returns:
            True if rescheduled successfully
        """
        self._ensure_service()

        try:
            event = (
                self._service.events()
                .get(calendarId="primary", eventId=event_id)
                .execute()
            )

            event["start"]["dateTime"] = new_start_time
            event["end"]["dateTime"] = new_end_time

            updated = (
                self._service.events()
                .update(calendarId="primary", eventId=event_id, body=event)
                .execute()
            )

            logger.info(f"Appointment rescheduled: {event_id}")
            return True

        except Exception as e:
            logger.error(f"Reschedule failed: {e}")
            return False

    # ─── Cancel ─────────────────────────────────────────────────────────

    async def cancel_appointment(self, event_id: str) -> bool:
        """
        Cancel/delete an appointment.

        Args:
            event_id: Google Calendar event ID

        Returns:
            True if cancelled successfully
        """
        self._ensure_service()

        try:
            await self._service.events().delete(
                calendarId="primary", eventId=event_id
            ).execute()
            logger.info(f"Appointment cancelled: {event_id}")
            return True

        except Exception as e:
            logger.error(f"Cancellation failed: {e}")
            return False

    # ─── List Upcoming ──────────────────────────────────────────────────

    async def list_upcoming(self, max_results: int = 10) -> list[dict]:
        """
        List upcoming appointments.

        Args:
            max_results: Maximum number of events to return

        Returns:
            List of event dicts
        """
        self._ensure_service()

        try:
            now = datetime.utcnow().isoformat() + "Z"

            events_result = (
                self._service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])
            logger.info(f"Found {len(events)} upcoming events")
            return events

        except Exception as e:
            logger.error(f"List upcoming failed: {e}")
            return []

    async def close(self):
        """Cleanup."""
        self._service = None
        logger.info("Calendar Integration shut down")
