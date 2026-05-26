# Recepta — 7-Day Launch Plan

> **From zero to first client demo in 7 days.**
> Dedicate 4-6 hours per day. Total: ~35 hours.

---

## Day 1: Environment Setup (5-6 hours)

### Goal: Install everything, verify it works

**Morning (2 hours):**
- [ ] Install Python 3.11+ (if not already)
  ```bash
  python --version  # Should be 3.10 or higher
  ```
- [ ] Create project directory and clone/setup Recepta
  ```bash
  cd ~ && mkdir recepta && cd recepta
  python -m venv venv
  source venv/bin/activate  # On Windows: venv\Scripts\activate
  pip install -r requirements.txt
  ```

- [ ] Install Ollama
  ```bash
  # Download from https://ollama.com/download
  # macOS: curl -fsSL https://ollama.com/install.sh | sh
  # Windows: Download installer from website
  ```

**Afternoon (3 hours):**
- [ ] Pull Llama 3.2 (runs on 8GB RAM)
  ```bash
  ollama pull llama3.2:3b
  ollama pull nomic-embed-text
  ```

- [ ] Install Docker + start Speaches
  ```bash
  # Install Docker Desktop from https://docker.com
  docker compose -f docker/docker-compose.yml up -d speaches
  ```

- [ ] Verify everything
  ```bash
  python main.py --check
  ```

- [ ] Copy and edit .env
  ```bash
  cp .env.example .env
  # Fill in your LiveKit credentials (sign up at livekit.io/cloud)
  ```

**End of Day 1 Check:**
```bash
python main.py --check
# ✓ Ollama (llama3.2:3b)
# ✓ Speaches STT (http://localhost:8000)
# ⚠ LiveKit - can be set up later
```

---

## Day 2: STT + TTS Integration (5-6 hours)

### Goal: Test speech recognition and voice generation

**Morning (2 hours):**
- [ ] Test Speaches STT
  ```bash
  # Record a short audio file or use an existing one
  # Test transcription:
  curl -X POST http://localhost:8000/v1/audio/transcriptions \
    -H "Authorization: Bearer recepta-local" \
    -F "file=@test.wav" \
    -F "model=whisper-1"
  ```

- [ ] Run the STT unit tests
  ```bash
  pytest tests/test_stt.py -v -k "test_initialization"
  ```

**Afternoon (3 hours):**
- [ ] Test Kokoro TTS
  ```bash
  python -c "
  import asyncio
  from services.tts_service import TTSService
  
  async def test():
      tts = TTSService()
      audio = await tts.generate('Hello, this is a test of Recepta.', voice='af_bella')
      if audio:
          with open('test_output.wav', 'wb') as f:
              f.write(audio)
          print('✓ Audio saved to test_output.wav')
      else:
          print('✗ TTS generation failed (Kokoro not installed)')
      
  asyncio.run(test())
  "
  ```

- [ ] Test the full pipeline in CLI mode
  ```bash
  python main.py --industry dental --business "Test Clinic"
  # Type: "Hi, I'd like to book an appointment"
  # Type: "quit" to exit
  ```

**End of Day 2 Check:**
- You can transcribe audio → text ✓
- You can generate audio from text ✓
- The CLI agent responds to text input ✓

---

## Day 3: LLM + Prompts + Knowledge Base (5-6 hours)

### Goal: Customize agent behavior and set up RAG

**Morning (2 hours):**
- [ ] Test Ollama responses
  ```bash
  python -c "
  import asyncio
  from services.llm_service import LLMService
  
  async def test():
      llm = LLMService()
      response = await llm.chat([{'role': 'user', 'content': 'What services do you offer?'}])
      print(f'Response: {response}')
  
  asyncio.run(test())
  "
  ```

- [ ] Run LLM tests
  ```bash
  pytest tests/test_llm.py -v -k "test_llm_conversation"
  ```

**Afternoon (3 hours):**
- [ ] Customize your first industry prompt
  ```bash
  # Edit config/prompts.py
  # Pick ONE industry to start (recommended: dental)
  # Change the default business name in your testing
  ```

- [ ] Set up knowledge base with sample data
  ```bash
  mkdir -p data/knowledge/sample
  # Create a sample FAQ file
  echo 'What are your hours? We are open Monday-Friday 9am-5pm.' > data/knowledge/sample/faq.txt
  echo 'Do you accept insurance? Yes, we accept most major insurance plans.' >> data/knowledge/sample/faq.txt
  
  # Ingest it
  python docs/onboarding/knowledge-base-ingestion.py --client "Test Business" --directory data/knowledge/sample/

  # (The ingestion script is at docs/onboarding/knowledge-base-ingestion.py, not scripts/)
  ```

- [ ] Test RAG search
  ```bash
  python -c "
  import asyncio
  from integrations.knowledge_base import KnowledgeBase
  
  async def test():
      kb = KnowledgeBase()
      await kb.initialize()
      results = await kb.search('What are your hours?')
      for r in results:
          print(f'  [{r[\"relevance_score\"]:.2f}] {r[\"text\"][:100]}')
  
  asyncio.run(test())
  "
  ```

**End of Day 3 Check:**
- LLM responds naturally ✓
- Agent follows the industry-specific prompt ✓
- Knowledge base returns relevant info ✓

---

## Day 4: Calendar + CRM + Testing (5-6 hours)

### Goal: Make the system actually book appointments and log calls

**Morning (2 hours):**
- [ ] Set up Google Calendar API
  ```bash
  # 1. Go to https://console.cloud.google.com/
  # 2. Create project → Enable Calendar API
  # 3. Create OAuth credentials → Download JSON
  # 4. Save as config/google_credentials.json
  ```

- [ ] Authenticate and test calendar
  ```bash
  python -c "
  import asyncio
  from integrations.calendar import CalendarIntegration
  
  async def test():
      cal = CalendarIntegration()
      success = await cal.authenticate()
      print(f'Calendar auth: {\"✓\" if success else \"✗\"}')
      if success:
          slots = await cal.check_availability('2025-06-16')
          print(f'Available slots on June 16: {len(slots)}')
  
  asyncio.run(test())
  "
  ```

**Afternoon (3 hours):**
- [ ] Test CRM
  ```bash
  pytest tests/test_pipeline.py -v -k "test_crm_database_operations"
  ```

- [ ] Run FULL test suite
  ```bash
  pytest tests/ -v  # Expect some skips for services not running
  ```

- [ ] Integration test: Book an appointment end-to-end
  ```bash
  python main.py --industry dental --business "SmileCare Dental"
  # Test: "Hi, I'd like to book a cleaning for tomorrow"
  # Check that the agent offers times and confirms booking
  ```

**End of Day 4 Check:**
- Calendar integration works ✓
- CRM logs calls ✓
- Complete pipeline test passes ✓
- Tests all pass (or have acceptable skips) ✓

---

## Day 5: Demo Prep + Portfolio (5-6 hours)

### Goal: Prepare to sell to your first client

**Morning (2 hours):**
- [ ] Record a 60-second demo video
  ```bash
  # Use OBS Studio (free) to record:
  # 1. Terminal showing python main.py
  # 2. Type in a realistic caller scenario
  # 3. Show the agent responding naturally
  ```

- [ ] Create a simple landing page (use Carrd.co - free)
  - Page sections:
    1. Hero: "Never Miss Another Call"
    2. How it works (3 simple steps)
    3. Industries served
    4. Pricing
    5. "Get Free Trial" CTA

**Afternoon (3 hours):**
- [ ] Prepare your demo flow
  ```bash
  # Practice this 5-minute demo flow:
  # 1. Show the problem: "Most businesses miss 30-50% of calls"
  # 2. Show the solution: Run python main.py --industry dental
  # 3. Show a real booking: Caller books appointment
  # 4. Show the proof: Calendar has the booking, CRM has the log
  # 5. ROI calculation: Show them the math
  ```

- [ ] Set up your freelance profiles
  - Upwork: Create profile targeting US/UK dental clinics
  - Fiverr: Create gig "AI Receptionist Setup"
  - LinkedIn: Update headline to "AI Voice Agent Specialist"

- [ ] Prepare cold email list
  ```bash
  # Find 20 dental clinics in US cities
  # Use Google Maps to find names + phone numbers
  # Find emails via their websites or Hunter.io (free tier)
  ```

**End of Day 5 Check:**
- Demo script memorized ✓
- Profiles live on 2+ platforms ✓
- 20 potential client emails ready ✓

---

## Day 6: Platform Applications + Outreach (5-6 hours)

### Goal: Get your first leads in the pipeline

**Morning (2 hours):**
- [ ] Apply to freelance platforms
  - [ ] Upwork: Complete profile, send 5 proposals
  - [ ] Fiverr: Publish gig
  - [ ] Contra: Create portfolio
  
- [ ] Send 10 cold emails (US timezone)
  ```bash
  # Use templates from docs/outreach/client-acquisition.md
  # Track opens with HubSpot Sales (free CRM)
  ```

**Afternoon (3 hours):**
- [ ] LinkedIn outreach
  - [ ] Connect with 15 dental practice owners/managers
  - [ ] Send connection requests with custom note
  - [ ] Follow up with message after accepted

- [ ] Join 3 relevant Facebook groups
  - "Dental Practice Management & Marketing"
  - "Small Business Owners United"
  - "HVAC Business Owners"

- [ ] Offer 3 "Free Phone System Audits"
  - DM or email: "I'll analyze your missed call rate for free"
  - This is your lead magnet

**End of Day 6 Check:**
- [ ] 10 cold emails sent
- [ ] 5 Upwork proposals sent
- [ ] LinkedIn connections: 15+
- [ ] At least 1 free audit scheduled

---

## Day 7: First Client Demo (4-6 hours)

### Goal: Close your first client

**Before the demo (2 hours):**
- [ ] Prepare the client's custom setup
  ```bash
  # Even for a demo, configure it with THEIR business name
  python main.py --industry dental --business "Their Practice Name"
  ```

- [ ] Test everything one more time
  ```bash
  python main.py --check
  pytest tests/test_pipeline.py -v -k "test_crm"
  ```

- [ ] Open all windows:
  - Terminal with their agent pre-loaded
  - Google Calendar (showing empty slots)
  - CRM dashboard

**During the demo (30 min):**
1. **Problem (5 min):** "You're losing X calls per day"
2. **Solution (10 min):** Run live demo with realistic scenarios
3. **Proof (5 min):** Show calendar populated, CRM updated
4. **ROI (5 min):** Show the math
5. **Offer (5 min):** Free 7-day trial

**After the demo (1-2 hours):**
- [ ] Send follow-up email with:
  - Link to demo recording
  - ROI calculation specific to their numbers
  - Free trial offer
  - Calendar link to book next call

- [ ] If YES:
  - [ ] Send contract (use Bonsai or PandaDoc)
  - [ ] Start onboarding (collect knowledge base docs)
  - [ ] Set up their full system
  - [ ] Collect payment (Stripe, Wise, or Payoneer)

- [ ] If "Think about it":
  - [ ] Schedule 3-day follow-up
  - [ ] Send one additional case study
  - [ ] Add to nurture sequence

### What to do if no demo closes on Day 7

Don't panic. This is normal. Reflect and iterate:

1. **Improve your targeting** — Are you talking to the right person?
2. **Improve your demo** — Record yourself and see where you lose them
3. **Lower the barrier** — Offer a 14-day free trial instead of 7
4. **Get testimonials** — Offer a steep discount to first 3 clients in exchange for review
5. **Keep going** — Sales is a numbers game. Send 100 emails, get 10 replies, close 2-3.

---

## Quick Reference: Daily Progress Tracker

| Day | Focus | Hours | Complete? |
|-----|-------|-------|-----------|
| 1 | Environment Setup | 5-6 | ☐ |
| 2 | STT + TTS | 5-6 | ☐ |
| 3 | LLM + Knowledge Base | 5-6 | ☐ |
| 4 | Calendar + Testing | 5-6 | ☐ |
| 5 | Demo Prep | 5-6 | ☐ |
| 6 | Outreach | 5-6 | ☐ |
| 7 | First Demo | 4-6 | ☐ |

**Total:** ~35 hours to first client demo.
