# Recepta — Monitoring & Scaling Guide

## Part 1: Call Analytics System

### What to Track Per Call

Every call generates these data points automatically via the CRM:

```sql
-- Key metrics stored in analytics.db
call_logs:
  - session_id (unique call identifier)
  - client_id (which business)
  - caller_name
  - caller_phone
  - intent (booking, emergency, faq, etc.)
  - duration_seconds
  - outcome (answered, missed, completed)
  - booking_made (boolean)
  - sentiment (positive, neutral, negative)
  - transcript (full conversation text)
```

### Analytics Dashboard Queries

```python
"""
Recepta - Analytics Queries
Run these to generate client reports.
"""
import sqlite3
from datetime import datetime, timedelta


def monthly_report(db_path: str, client_id: int, year: int, month: int):
    """Generate a monthly performance report for a client."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    month_start = f"{year:04d}-{month:02d}-01"
    if month == 12:
        month_end = f"{year+1:04d}-01-01"
    else:
        month_end = f"{year:04d}-{month+1:02d}-01"

    # Total calls
    cursor = conn.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN outcome = 'answered' THEN 1 ELSE 0 END) as answered,
               SUM(CASE WHEN outcome = 'missed' THEN 1 ELSE 0 END) as missed,
               SUM(booking_made) as bookings,
               AVG(duration_seconds) as avg_duration
        FROM call_logs
        WHERE client_id = ? AND created_at >= ? AND created_at < ?
    """, (client_id, month_start, month_end))

    stats = dict(cursor.fetchone())

    # Intent breakdown
    cursor = conn.execute("""
        SELECT intent, COUNT(*) as count
        FROM call_logs
        WHERE client_id = ? AND created_at >= ? AND created_at < ?
        GROUP BY intent
        ORDER BY count DESC
    """, (client_id, month_start, month_end))

    intents = [dict(r) for r in cursor.fetchall()]

    # Daily trend
    cursor = conn.execute("""
        SELECT date(created_at) as day, COUNT(*) as calls
        FROM call_logs
        WHERE client_id = ? AND created_at >= ? AND created_at < ?
        GROUP BY day
        ORDER BY day
    """, (client_id, month_start, month_end))

    daily = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "total_calls": stats["total"] or 0,
        "answered": stats["answered"] or 0,
        "missed": stats["missed"] or 0,
        "bookings": stats["bookings"] or 0,
        "avg_duration_seconds": round(stats["avg_duration"] or 0),
        "answer_rate": f"{(stats['answered'] or 0) / max(stats['total'], 1) * 100:.0f}%",
        "top_intents": intents,
        "daily_trend": daily,
    }


# Usage example for generating a report
if __name__ == "__main__":
    report = monthly_report("data/analytics.db", client_id=1, year=2025, month=6)
    print(f"Total calls: {report['total_calls']}")
    print(f"Answer rate: {report['answer_rate']}")
    print(f"Bookings: {report['bookings']}")
    print(f"Avg duration: {report['avg_duration_seconds']}s")
```

### Client Monthly Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Recepta - Monthly Performance Report
  Client: [Business Name]
  Month: June 2025
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 CALL METRICS
  Total Calls:        142
  Answered:           141 (99% answer rate)
  Missed:             1
  Avg Call Duration:  2m 34s

📅 BOOKINGS
  Appointments Booked:   38
  Revenue Recovered:     $9,500

🎯 INTENT BREAKDOWN
  Booking:       52 (37%)
  FAQ:           38 (27%)
  Emergency:     21 (15%)
  Cancel/Reschedule:  18 (13%)
  General:      13 (9%)

📈 TREND (vs last month)
  Calls:       +22%   (+26 calls)
  Bookings:    +31%   (+9 bookings)
  Answer Rate: 99%    (+2%)

📋 RECOMMENDATIONS
  • Busiest day: Tuesdays (avg 28 calls)
  • Peak hours: 11 AM - 1 PM (lunch coverage needed)
  • Top FAQ: "Do you accept [insurance]?" — consider updating knowledge base
```

---

## Part 2: Multi-Tenant Architecture

### How Multiple Clients Share the System

```
┌─────────────────────────────────────────────────────────┐
│                     Recepta Server                      │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Core Services (shared)               │   │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌───────────┐   │   │
│  │  │ STT  │  │ LLM  │  │ TTS  │  │ ChromaDB  │   │   │
│  │  └──────┘  └──────┘  └──────┘  └───────────┘   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐       │
│  │ Client │  │ Client │  │ Client │  │ Client │       │
│  │    A    │  │    B    │  │    C    │  │    D    │       │
│  │ Dental │  │ Legal  │  │ HVAC   │  │ RealEst │       │
│  └────────┘  └────────┘  └────────┘  └────────┘       │
│                                                         │
│  Data Isolation (per client):                           │
│  • Separate ChromaDB collections (client_id filter)     │
│  • Separate CRM records (client_id foreign key)         │
│  • Separate agent instances                             │
│  • Separate phone numbers (via LiveKit)                 │
└─────────────────────────────────────────────────────────┘
```

### Scaling Configuration

```python
# config/settings.py (multi-tenant mode)
RECEPTA_MULTI_TENANT = True

# Each client gets their own room/agent
# When a call comes in, the system:
# 1. Identifies which client based on the phone number called
# 2. Loads their specific agent, knowledge base, and prompts
# 3. Routes the call to the correct handler
```

---

## Part 3: Pricing for Scale

| Client Count | Monthly Rev | Infrastructure | Notes |
|-------------|-------------|----------------|-------|
| 1-10 clients | $300-$8,000/mo | Single laptop | Manual setup per client |
| 10-50 clients | $5,000-$40,000/mo | VPS/Cloud server | Automated onboarding needed |
| 50-100 clients | $25,000-$80,000/mo | Multi-server | Full team required |

### Infrastructure Costs at Scale

| Scale | Infrastructure | Monthly Cost | Tools |
|-------|---------------|-------------|-------|
| 1-10 clients | Your laptop | $0 | Everything local |
| 10-30 clients | $50/mo VPS | ~$50 | Hetzner/Contabo for Ollama |
| 30-100 clients | $200-500/mo servers | ~$300 | Dedicated GPU server for STT |

---

## Part 4: Team Hiring Plan

### When to Hire

| Revenue | Team Size | Hires |
|---------|-----------|-------|
| $0-$3K/mo | 1 (You) | — |
| $3K-$10K/mo | 2 | Virtual assistant (Pakistan: $300-500/mo) |
| $10K-$25K/mo | 3-4 | Salesperson + Developer + VA |
| $25K-$50K/mo | 5-8 | Full team (see below) |
| $50K+/mo | 10+ | Scale operations |

### Roles & Salaries (Pakistan Market)

| Role | Monthly Salary (PKR) | Monthly Salary (USD) | When |
|------|--------------------|---------------------|------|
| **Virtual Assistant** | 40,000-80,000 | $150-300 | $3K+ revenue |
| **Python Developer** | 100,000-200,000 | $350-700 | $5K+ revenue |
| **Sales / Business Dev** | 80,000-150,000 | $300-500 | $5K+ revenue |
| **Customer Success** | 60,000-100,000 | $200-350 | $10K+ revenue |
| **DevOps Engineer** | 150,000-250,000 | $500-900 | $15K+ revenue |
| **CTO / Technical Lead** | 200,000-400,000 | $700-1,400 | $25K+ revenue |

### Remote Team Setup (Pakistan)

```
Platforms for hiring:
- Rozee.pk (largest Pakistani job board)
- LinkedIn Pakistan
- Fiverr (find Pakistani freelancers)
- Upwork (filter by Pakistan)
- Facebook Groups: "Python Developers Pakistan"

Tools for team management:
- Slack or Discord (communication)
- GitHub (code)
- Notion or Google Docs (docs/processes)
- Clockify (time tracking)
```

---

## Part 5: Expansion Roadmap

### Phase 1: US Market (Months 1-6)
**Target:** Dental clinics, law firms, HVAC companies
**Strategy:** Cold email + Upwork + LinkedIn outreach
**Pricing:** $1,500-$5,000 setup, $300-$800/mo

### Phase 2: UK/Canada (Months 6-9)
**Target:** Same industries, UK-specific accents/timezones
**Changes needed:**
- Adjust prompts for UK English (e.g., "lift" instead of "elevator")
- UK phone number format support
- Timezone handling (GMT/BST)

### Phase 3: UAE (Months 9-12)
**Target:** Dubai healthcare, real estate, law firms
**Changes needed:**
- Arabic language support (use MeloTTS for multilingual)
- Friday-Saturday weekend handling
- Local payment processing

### Phase 4: Pakistan/India (Months 12-18)
**Target:** Local businesses in major cities
**Pricing adjust:** Lower pricing (e.g., $200-$500 setup)
**Changes needed:**
- Urdu/Hindi language support
- Local phone number integration
- Local payment methods (JazzCash, EasyPaisa, UPI)

---

## Part 6: System Health Monitoring

### Daily Health Check Script

```bash
#!/bin/bash
# /recepta-healthcheck.sh - Run this daily via cron

echo "=== Recepta Health Check $(date) ==="

# 1. Service health
echo "Ollama: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:11434/api/tags)"
echo "Speaches: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/v1/models)"

# 2. Disk usage
echo "Disk: $(df -h / | tail -1 | awk '{print $5}')"

# 3. Memory usage
echo "RAM: $(free -h | grep Mem | awk '{print $3 "/" $2}')"

# 4. Process check
echo "Ollama process: $(ps aux | grep ollama | grep -v grep | wc -l) running"
echo "Python agents: $(ps aux | grep 'python main.py' | grep -v grep | wc -l) running"

# 5. Recent errors
echo "Recent errors:"
tail -3 data/logs/recepta_error.log 2>/dev/null || echo "  No error log found"

echo "=== Health Check Complete ==="
```

### Alerting Setup

```python
"""
Simple SMS/Email alerting when things go wrong.
"""
import smtplib
from email.message import EmailMessage


def send_alert(subject: str, body: str):
    """Send an alert email when a service goes down."""
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = f"[Recepta Alert] {subject}"
    msg["From"] = "alerts@recepta.ai"
    msg["To"] = "you@email.com"

    # Configure your SMTP server
    # with smtplib.SMTP("smtp.gmail.com", 587) as server:
    #     server.starttls()
    #     server.login("you@gmail.com", "password")
    #     server.send_message(msg)
    print(f"Alert sent: {subject}")
