"""
Recepta - CRM Integration
Manages client data, leads, call logs, and analytics.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import DATA_DIR, ANALYTICS_DB_PATH
from utils.logger import get_logger

logger = get_logger(__name__)


class CRMIntegration:
    """
    Local CRM system for tracking clients, leads, calls, and analytics.

    Uses SQLite (no external dependencies, zero cost).
    Can be upgraded to HubSpot/Zoho/etc. via n8n integration later.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(Path(ANALYTICS_DB_PATH))
        self._conn: Optional[sqlite3.Connection] = None
        logger.info(f"CRM Integration initialized (db={self.db_path})")

    def connect(self):
        """Connect to the SQLite database."""
        if self._conn:
            return

        try:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._create_tables()
            logger.info("CRM database connected")
        except Exception as e:
            logger.error(f"CRM database connection failed: {e}")
            raise

    def _create_tables(self):
        """Create all required tables if they don't exist."""
        cursor = self._conn.cursor()

        # Clients (businesses we serve)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_name TEXT NOT NULL,
                industry TEXT NOT NULL,
                contact_name TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                    website TEXT,
                timezone TEXT DEFAULT 'America/New_York',
                notes TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Leads (potential clients)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_name TEXT,
                industry TEXT,
                contact_name TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                source TEXT,
                status TEXT DEFAULT 'new',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Call logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS call_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER REFERENCES clients(id),
                session_id TEXT,
                caller_name TEXT,
                caller_phone TEXT,
                intent TEXT,
                duration_seconds INTEGER,
                outcome TEXT,
                transcript TEXT,
                booking_made INTEGER DEFAULT 0,
                sentiment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Appointments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER REFERENCES clients(id),
                caller_name TEXT,
                caller_phone TEXT,
                caller_email TEXT,
                appointment_time TIMESTAMP,
                duration_minutes INTEGER DEFAULT 30,
                appointment_type TEXT,
                status TEXT DEFAULT 'scheduled',
                calendar_event_id TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Knowledge bases (RAG sources per client)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_bases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER REFERENCES clients(id),
                source_name TEXT,
                source_type TEXT,
                file_path TEXT,
                chunk_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Analytics summary
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER REFERENCES clients(id),
                date DATE NOT NULL,
                total_calls INTEGER DEFAULT 0,
                answered_calls INTEGER DEFAULT 0,
                bookings_made INTEGER DEFAULT 0,
                avg_duration_seconds INTEGER DEFAULT 0,
                missed_calls INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(client_id, date)
            )
        """)

        self._conn.commit()

    # ─── Client Management ──────────────────────────────────────────────

    def add_client(self, **kwargs) -> int:
        """Add a new client."""
        self.connect()
        cursor = self._conn.cursor()
        cursor.execute(
            """INSERT INTO clients (business_name, industry, contact_name, contact_email, contact_phone, website, timezone, notes)
               VALUES (:business_name, :industry, :contact_name, :contact_email, :contact_phone, :website, :timezone, :notes)""",
            kwargs,
        )
        self._conn.commit()
        client_id = cursor.lastrowid
        logger.info(f"Client added: {kwargs.get('business_name')} (ID: {client_id})")
        return client_id

    def get_client(self, client_id: int) -> Optional[dict]:
        """Get client by ID."""
        self.connect()
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_clients(self, active_only: bool = True) -> list[dict]:
        """List all clients."""
        self.connect()
        cursor = self._conn.cursor()
        if active_only:
            cursor.execute("SELECT * FROM clients WHERE is_active = 1 ORDER BY business_name")
        else:
            cursor.execute("SELECT * FROM clients ORDER BY business_name")
        return [dict(row) for row in cursor.fetchall()]

    # ─── Lead Management ────────────────────────────────────────────────

    def add_lead(self, **kwargs) -> int:
        """Add a new lead."""
        self.connect()
        cursor = self._conn.cursor()
        cursor.execute(
            """INSERT INTO leads (business_name, industry, contact_name, contact_email, contact_phone, source, status, notes)
               VALUES (:business_name, :industry, :contact_name, :contact_email, :contact_phone, :source, :status, :notes)""",
            kwargs,
        )
        self._conn.commit()
        lead_id = cursor.lastrowid
        logger.info(f"Lead added: {kwargs.get('business_name')} (ID: {lead_id})")
        return lead_id

    def update_lead_status(self, lead_id: int, status: str):
        """Update lead status."""
        self.connect()
        self._conn.execute(
            "UPDATE leads SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, lead_id),
        )
        self._conn.commit()
        logger.info(f"Lead {lead_id} status updated to: {status}")

    def list_leads(self, status: Optional[str] = None) -> list[dict]:
        """List leads, optionally filtered by status."""
        self.connect()
        cursor = self._conn.cursor()
        if status:
            cursor.execute("SELECT * FROM leads WHERE status = ? ORDER BY created_at DESC", (status,))
        else:
            cursor.execute("SELECT * FROM leads ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    # ─── Call Logging ──────────────────────────────────────────────────

    def log_call(self, **kwargs) -> int:
        """Log a completed call."""
        self.connect()
        cursor = self._conn.cursor()
        cursor.execute(
            """INSERT INTO call_logs (client_id, session_id, caller_name, caller_phone, intent, duration_seconds, outcome, transcript, booking_made, sentiment)
               VALUES (:client_id, :session_id, :caller_name, :caller_phone, :intent, :duration_seconds, :outcome, :transcript, :booking_made, :sentiment)""",
            kwargs,
        )
        self._conn.commit()
        call_id = cursor.lastrowid
        logger.info(f"Call logged (ID: {call_id})")
        return call_id

    def get_calls(self, client_id: int, limit: int = 20) -> list[dict]:
        """Get recent calls for a client."""
        self.connect()
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM call_logs WHERE client_id = ? ORDER BY created_at DESC LIMIT ?",
            (client_id, limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    # ─── Appointment Management ────────────────────────────────────────

    def add_appointment(self, **kwargs) -> int:
        """Add an appointment record."""
        self.connect()
        cursor = self._conn.cursor()
        cursor.execute(
            """INSERT INTO appointments (client_id, caller_name, caller_phone, caller_email, appointment_time, duration_minutes, appointment_type, status, calendar_event_id, notes)
               VALUES (:client_id, :caller_name, :caller_phone, :caller_email, :appointment_time, :duration_minutes, :appointment_type, :status, :calendar_event_id, :notes)""",
            kwargs,
        )
        self._conn.commit()
        apt_id = cursor.lastrowid
        logger.info(f"Appointment created (ID: {apt_id})")
        return apt_id

    def get_upcoming_appointments(self, client_id: int) -> list[dict]:
        """Get upcoming appointments for a client."""
        self.connect()
        cursor = self._conn.cursor()
        cursor.execute(
            """SELECT * FROM appointments
               WHERE client_id = ? AND status = 'scheduled' AND appointment_time > datetime('now')
               ORDER BY appointment_time ASC LIMIT 10""",
            (client_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    # ─── Analytics ─────────────────────────────────────────────────────

    def update_analytics(self, client_id: int, date: str = None):
        """Update daily analytics for a client."""
        self.connect()
        date = date or datetime.now().strftime("%Y-%m-%d")
        cursor = self._conn.cursor()

        # Calculate metrics
        cursor.execute(
            """SELECT
                   COUNT(*) as total_calls,
                   SUM(CASE WHEN outcome = 'answered' THEN 1 ELSE 0 END) as answered_calls,
                   SUM(booking_made) as bookings_made,
                   AVG(duration_seconds) as avg_duration,
                   SUM(CASE WHEN outcome = 'missed' THEN 1 ELSE 0 END) as missed_calls
               FROM call_logs
               WHERE client_id = ? AND date(created_at) = ?""",
            (client_id, date),
        )
        stats = dict(cursor.fetchone())

        cursor.execute(
            """INSERT INTO analytics
               (client_id, date, total_calls, answered_calls, bookings_made, avg_duration_seconds, missed_calls)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(client_id, date) DO UPDATE SET
                   total_calls = excluded.total_calls,
                   answered_calls = excluded.answered_calls,
                   bookings_made = excluded.bookings_made,
                   avg_duration_seconds = excluded.avg_duration_seconds,
                   missed_calls = excluded.missed_calls""",
            (
                client_id, date,
                stats.get("total_calls", 0),
                stats.get("answered_calls", 0),
                stats.get("bookings_made", 0),
                stats.get("avg_duration", 0) or 0,
                stats.get("missed_calls", 0),
            ),
        )
        self._conn.commit()
        logger.debug(f"Analytics updated for client {client_id} on {date}")

    def get_monthly_report(self, client_id: int, year: int, month: int) -> dict:
        """Get monthly analytics report for a client."""
        self.connect()
        cursor = self._conn.cursor()
        month_str = f"{year:04d}-{month:02d}%"
        cursor.execute(
            """SELECT
                   SUM(total_calls) as total_calls,
                   SUM(answered_calls) as answered_calls,
                   SUM(bookings_made) as bookings_made,
                   AVG(avg_duration_seconds) as avg_duration,
                   SUM(missed_calls) as missed_calls
               FROM analytics
               WHERE client_id = ? AND date LIKE ?""",
            (client_id, month_str),
        )
        return dict(cursor.fetchone())

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("CRM database closed")
