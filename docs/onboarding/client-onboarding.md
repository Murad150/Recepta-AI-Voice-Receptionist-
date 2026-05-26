# Recepta — Client Onboarding System

## Part 1: Discovery Questionnaire (20 Questions)

Ask these questions during your discovery call with potential clients.

### Business Overview
1. What is your business name and website URL?
2. What industry are you in? (Dental / Legal / HVAC / Real Estate / Other)
3. How many phone calls do you estimate you receive per day?
4. How many of those calls go to voicemail or are missed?
5. What is the average value of a booked appointment/call?

### Current Pain Points
6. How do you currently handle phone calls? (Receptionist / Voicemail / Rotating staff)
7. What happens when no one answers the phone?
8. How many appointments/leads do you estimate you lose per week from missed calls?
9. What is the #1 frustration with your current phone system?

### Hours & Availability
10. What are your business hours?
11. Do you have weekend or after-hours calls you're missing?
12. Do you close for lunch breaks?

### Call Types
13. What are the most common reasons people call? (Book appointments / Ask questions / Emergencies / Complaints)
14. What percentage of calls are emergencies or urgent?
15. What are the top 3 questions you get asked repeatedly?

### Booking & Calendar
16. What calendar system do you use? (Google Calendar / Outlook / Other / None)
17. How far in advance do you book appointments?
18. Do you have multiple locations or practitioners?

### Decision Criteria
19. What would need to happen for you to say "YES" to this service today?
20. What's your budget for an AI receptionist solution?

---

## Part 2: Knowledge Base Upload System

### What to Collect from Each Client

Ask the client to provide these documents:
1. **Services/Pricing PDF** — List of services offered with descriptions
2. **FAQ Document** — Top 20+ questions they get asked
3. **Hours & Policies** — Business hours, cancellation policy, late policy
4. **Insurance/ Payment Info** — Which insurance plans accepted, payment options
5. **Staff Directory** — Names and roles of key staff/practitioners
6. **Location Info** — Address, directions, parking info

### Upload Command

```bash
# 1. Place PDF files in data/knowledge/<client_name>/
mkdir -p data/knowledge/smiledental

# 2. Run the ingestion script
python scripts/ingest_knowledge.py --client "SmileCare Dental" --directory data/knowledge/smiledental/
```

### Ingestion Script

Create this as `scripts/ingest_knowledge.py`:

```python
"""
Recepta - Knowledge Base Ingestion Script
Usage: python scripts/ingest_knowledge.py --client "Client Name" --directory path/to/docs/
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrations.knowledge_base import KnowledgeBase
from services.llm_service import LLMService


async def ingest(client_name: str, directory: str):
    kb = KnowledgeBase()
    llm = LLMService()

    await kb.initialize(ollama_service=llm)
    await llm.health_check()

    dir_path = Path(directory)
    total_chunks = 0

    for file_path in dir_path.glob("*"):
        if file_path.suffix.lower() == ".pdf":
            chunks = await kb.add_pdf(
                str(file_path),
                metadata={"client": client_name, "source": file_path.name},
            )
            total_chunks += chunks
            print(f"  ✓ {file_path.name}: {chunks} chunks")
        elif file_path.suffix.lower() in [".txt", ".md"]:
            chunks = await kb.add_text_file(
                str(file_path),
                metadata={"client": client_name, "source": file_path.name},
            )
            total_chunks += chunks
            print(f"  ✓ {file_path.name}: {chunks} chunks")

    print(f"\nIngested {total_chunks} total chunks for {client_name}")
    stats = kb.get_stats()
    print(f"Knowledge Base stats: {stats}")

    await kb.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", required=True)
    parser.add_argument("--directory", required=True)
    args = parser.parse_args()
    asyncio.run(ingest(args.client, args.directory))
```

---

## Part 3: Voice Cloning Workflow

### Using Kokoro's Built-in Voices

Kokoro comes with 100+ pre-built voices. Default recommended:

| Voice | Gender | Style | Best For |
|-------|--------|-------|----------|
| `af_bella` | Female | Warm, friendly | Dental, Healthcare |
| `am_michael` | Male | Professional, deep | Legal, Consulting |
| `af_nicole` | Female | Energetic, bright | Real Estate |
| `am_adam` | Male | Friendly, casual | HVAC, Home Services |

### Voice Cloning (Advanced)

For custom voice cloning, you'll need a 6+ second high-quality audio sample:

```python
# In your Python environment:
from services.tts_service import TTSService

tts = TTSService()
await tts.clone_voice("client_voice_sample.wav", "dr_smith_voice")
```

### Recording a Good Voice Sample
1. Use a quiet room with no echo
2. Record on a good microphone (iPhone voice memos work)
3. Speak clearly at normal pace
4. Read this script:
   > "Hello, and thank you for calling. This is Dr. Smith at SmileCare Dental. We're glad you reached out. Please listen carefully as our virtual assistant helps you today."

---

## Part 4: Calendar Integration Setup

### Google Calendar Setup

1. Go to https://console.cloud.google.com/
2. Create a new project → Name: "Recepta"
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials → Desktop application
5. Download credentials → Save as `config/google_credentials.json`
6. Run the agent → It will open a browser for first-time auth
7. Token auto-saves to `config/google_token.json`

### Testing Calendar Integration

```bash
python -c "
import asyncio
from integrations.calendar import CalendarIntegration
async def test():
    cal = CalendarIntegration()
    success = await cal.authenticate()
    print(f'Auth: {\"OK\" if success else \"FAILED\"}')

    if success:
        events = await cal.list_upcoming()
        print(f'Upcoming events: {len(events)}')

        slots = await cal.check_availability('2025-06-15')
        print(f'Available slots: {len(slots)}')
    await cal.close()
asyncio.run(test())
"
```

---

## Part 5: Testing Checklist

### Per-Industry Test Scenarios (10 Each)

#### Dental Clinic ✅
- [ ] 1. Caller wants to book a routine cleaning
- [ ] 2. Caller has severe tooth pain (emergency)
- [ ] 3. New patient calling for first appointment
- [ ] 4. Caller asks about insurance acceptance
- [ ] 5. Caller wants to cancel/reschedule
- [ ] 6. Caller asks for directions to the clinic
- [ ] 7. Caller needs a specific dentist
- [ ] 8. Caller asks about pricing for a procedure
- [ ] 9. Caller is angry about wait times (complaint)
- [ ] 10. Caller hangs up mid-conversation

#### Law Firm ✅
- [ ] 1. Caller needs a personal injury consultation
- [ ] 2. Caller has an urgent court deadline
- [ ] 3. Caller asks about legal fees
- [ ] 4. Caller wants to schedule a consultation
- [ ] 5. Caller is emotional about their case
- [ ] 6. Caller asks about the attorney's experience
- [ ] 7. Caller needs to reschedule existing consultation
- [ ] 8. Caller has a simple legal question
- [ ] 9. Caller calls about a real estate closing
- [ ] 10. Caller asks for documents to be sent

#### HVAC ✅
- [ ] 1. No heat in winter (emergency)
- [ ] 2. AC not working in summer
- [ ] 3. Routine maintenance scheduling
- [ ] 4. Gas smell detected (critical emergency)
- [ ] 5. Caller asks about pricing for a new unit
- [ ] 6. Caller needs a quote
- [ ] 7. Caller wants to know when technician will arrive
- [ ] 8. Caller cancels a service appointment
- [ ] 9. Caller complains about previous service
- [ ] 10. Caller asks about service area coverage

#### Real Estate ✅
- [ ] 1. Buyer wants to see a specific property
- [ ] 2. Seller wants a market analysis
- [ ] 3. Caller asks about open houses
- [ ] 4. Buyer has a specific budget range
- [ ] 5. Caller asks about school districts
- [ ] 6. Caller wants to list their home
- [ ] 7. Caller asks about commission rates
- [ ] 8. First-time buyer calling
- [ ] 9. Caller wants rental info
- [ ] 10. Caller refers a friend

---

## Part 6: Go-Live Deployment Script

### Pre-Launch Checklist

```bash
#!/bin/bash
# recepta-go-live.sh - Complete deployment check

echo "=== Recepta - Go-Live Checklist ==="

# 1. Environment Check
echo -n "Python version: "
python --version

echo -n "Ollama running: "
curl -s -o /dev/null -w "%{http_code}" http://localhost:11434/api/tags

echo -n "Speaches running: "
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/v1/models

# 2. Models Check
echo -n "Llama 3.2 available: "
ollama list | grep -q "llama3.2" && echo "YES" || echo "NO"

echo -n "Embedding model available: "
ollama list | grep -q "nomic-embed-text" && echo "YES" || echo "NO"

# 3. Configuration
echo -n ".env exists: "
test -f .env && echo "YES" || echo "NO"

echo -n "Google credentials exist: "
test -f config/google_credentials.json && echo "YES" || echo "NO (auto-auth will trigger OAuth)"

# 4. Test Run
echo "Running test..."
python main.py --check

echo "=== Checklist Complete ==="
```
