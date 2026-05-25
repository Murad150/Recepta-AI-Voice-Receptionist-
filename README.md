# Recepta — 24/7 AI Receptionist for Small Businesses

> **Build a complete AI Voice Agent business. Zero API costs. Runs on your laptop.**

## 🚀 What is Recepta?

Recepta is a production-ready, open-source voice agent system that provides **24/7 AI receptionists** for small businesses. It handles calls, books appointments, answers FAQs, and integrates with Google Calendar — all running locally with **zero ongoing API costs**.

### Industries Supported
| Industry | Agent Name | Handles |
|----------|------------|---------|
| 🦷 **Dental Clinics** | Sarah | Appointments, emergency triage, insurance |
| ⚖️ **Law Firms** | Michael | Intake, consultation scheduling, case triage |
| 🔧 **HVAC Companies** | Mike | Service dispatch, emergency, maintenance |
| 🏠 **Real Estate** | Jessica | Property showings, buyer/seller intake |

## 📋 Prerequisites

- **Hardware**: Laptop with 8GB RAM, no GPU needed
- **OS**: Windows, macOS, or Linux
- **Skills**: Basic terminal usage, intermediate Python
- **Time**: 2-3 hours for initial setup

## 🛠️ Tech Stack (100% Free / Open Source)

| Component | Tool | Cost |
|-----------|------|------|
| **Orchestrator** | Pipecat | Free |
| **Speech-to-Text** | Speaches (faster-whisper) | Free (local) |
| **LLM Brain** | Ollama + Llama 3.2 (3B) | Free (local) |
| **Text-to-Speech** | Kokoro (82M params) | Free (local) |
| **Transport** | LiveKit Cloud (free tier) | Free (10h/month) |
| **Calendar** | Google Calendar API | Free |
| **Vector DB** | ChromaDB | Free |
| **Automation** | n8n | Free (self-hosted) |
| **CRM** | SQLite (built-in) | Free |

## 📦 Installation

### Step 1: Clone & Setup

```bash
# Clone the repository
git clone <your-repo-url> recepta
cd recepta

# Create Python virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Install Ollama (LLM)

```bash
# Download from https://ollama.com/download or use:
# macOS/Linux:
curl -fsSL https://ollama.com/install.sh | sh

# Pull Llama 3.2 (3B params - runs on 8GB RAM)
ollama pull llama3.2:3b

# Pull embedding model (for RAG)
ollama pull nomic-embed-text

# Test it
ollama run llama3.2:3b "Hello, how are you?"
```

### Step 3: Start Speaches (STT/TTS)

```bash
# Start the Docker container
docker compose -f docker/docker-compose.yml up -d speaches

# Verify it's running
curl http://localhost:8000/v1/models

# You should see a JSON response listing available models
```

### Step 4: Configure Environment

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your settings:
# - LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET (get from livekit.io/cloud)
# - Other defaults work for local development
```

### Step 5: Verify Installation

```bash
# Run health check
python main.py --check

# Expected output:
# ✓ Ollama (llama3.2:3b)
# ✓ Speaches STT (http://localhost:8000)
# ✗ LiveKit API Key configured (if you haven't set it up yet)
```

## 🎯 Quick Start: Test the Agent

```bash
# Run the dental agent in interactive CLI mode
python main.py --industry dental --business "SmileCare Dental"

# Try these test conversations:
#   "Hi, I'd like to book a cleaning appointment"
#   "I have a toothache, can I come in today?"
#   "What are your hours?"
#   Type 'quit' to exit
```

### Test All Industries

```bash
python main.py --industry legal --business "Smith & Associates Law"
python main.py --industry hvac --business "Quick Cool HVAC"
python main.py --industry real_estate --business "Premier Properties"
```

## 📞 Running with LiveKit (Real Voice Calls)

1. **Sign up for free LiveKit Cloud**: https://livekit.io/cloud
2. **Get your credentials** from the LiveKit dashboard
3. **Update `.env`**:
   ```
   LIVEKIT_URL=wss://your-project.livekit.cloud
   LIVEKIT_API_KEY=your_api_key
   LIVEKIT_API_SECRET=your_api_secret
   ```
4. **Run the agent**:
   ```bash
   python main.py --industry dental --business "SmileCare Dental" --livekit
   ```
5. **Connect via LiveKit's web interface** or your SIP trunk provider

## 📂 Project Structure

```
recepta/
├── config/               # Configuration files
│   ├── settings.py       # All settings from .env
│   ├── prompts.py        # Industry-specific system prompts
│   └── google_credentials.json  # Google Calendar OAuth (you provide)
├── services/             # Core AI services
│   ├── stt_service.py    # Speaches STT integration
│   ├── llm_service.py    # Ollama LLM integration
│   ├── tts_service.py    # Kokoro TTS integration
│   └── transport_service.py  # LiveKit WebRTC transport
├── integrations/         # External integrations
│   ├── calendar.py       # Google Calendar booking
│   ├── crm.py            # SQLite CRM/analytics
│   └── knowledge_base.py # ChromaDB RAG system
├── agents/               # Voice agents by industry
│   ├── base_agent.py     # Shared agent logic
│   ├── dental_agent.py   # Dental: Sarah
│   ├── legal_agent.py    # Legal: Michael
│   ├── hvac_agent.py     # HVAC: Mike
│   └── real_estate_agent.py  # Real Estate: Jessica
├── tests/                # Test suite
├── utils/                # Utilities
│   ├── logger.py         # Logging with rotation
│   └── helpers.py        # Context extraction, time helpers
├── docker/               # Docker configuration
│   ├── docker-compose.yml  # Speaches + n8n
│   └── Dockerfile
├── docs/                 # Business documentation
│   ├── onboarding/       # Client onboarding system
│   ├── sales/            # Demo scripts & sales materials
│   ├── outreach/         # Client acquisition templates
│   └── monitoring/       # Scaling & monitoring
├── data/                 # Runtime data (gitignored)
│   ├── logs/
│   ├── chroma_db/
│   ├── voices/
│   └── knowledge/
├── main.py               # Entry point
├── requirements.txt      # Python dependencies
├── .env.example          # Environment template
└── README.md             # You are here
```

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_pipeline.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term
```

## 💼 Business Model

### Pricing Tiers

| Tier | Setup Fee | Monthly | Features |
|------|-----------|---------|----------|
| **Starter** | $1,500 | $300/mo | 1 agent, 500 min/mo, basic CRM |
| **Pro** | $3,000 | $500/mo | 3 agents, 2000 min/mo, Calendar + CRM |
| **Enterprise** | $5,000 | $800/mo | Unlimited agents, custom voice, priority |

### Target Clients
- 🦷 **Dental Clinics**: 10+ staff, high call volume
- ⚖️ **Law Firms**: Intake-heavy practices
- 🔧 **HVAC Companies**: Seasonally busy
- 🏠 **Real Estate Agencies**: Multiple agents

## 📈 7-Day Launch Plan

| Day | Focus | Tasks |
|-----|-------|-------|
| **1** | 🏗️ Setup | Install Python, Ollama, Docker, clone repo |
| **2** | 🎙️ STT+TTS | Start Speaches, test transcription & speech |
| **3** | 🧠 LLM+Prompts | Test Ollama, customize agent prompts |
| **4** | 📅 Calendar+CRM | Set up Google Calendar, test booking |
| **5** | 🎪 Demo Prep | Create demo script, test all industries |
| **6** | 📢 Outreach | Set up Upwork/Fiverr profiles, send emails |
| **7** | 🚀 First Demo | Run live demo for potential client |

## 🔧 Troubleshooting

### "Ollama not reachable"
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags
# If not, start it: ollama serve
```

### "Speaches connection refused"
```bash
# Check Docker container
docker ps | grep speaches
# If not running: docker compose -f docker/docker-compose.yml up -d speaches
```

### "Model not found"
```bash
# Pull the model
ollama pull llama3.2:3b
```

### "No module named 'kokoro'"
```bash
pip install kokoro soundfile numpy
```

### "Audio quality is robotic"
- Try different Kokoro voices: `af_bella`, `af_nicole`, `am_michael`
- Adjust speech speed: `KOKORO_SPEED=1.0` in `.env`

## 🌍 Expansion Roadmap

1. **US Market** → 2. **UK/Canada** → 3. **UAE** → 4. **Pakistan/India**

## 📄 License

MIT License — free to use, modify, and sell.

---

Built with ❤️ for bootstrappers and indie entrepreneurs.
