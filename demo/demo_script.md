# Recepta — Live Demo Script

Use this script to run a structured demo for potential clients.

## Pre-Demo Checklist

- [ ] Terminal open with `python main.py --industry [industry] --business "[Client Name]"`
- [ ] Google Calendar open (fresh, showing available slots)
- [ ] CRM dashboard/analytics open
- [ ] Knowledge base loaded (if client provided documents)
- [ ] Phone ready for any audio issues

## Demo Flow

### 1. Introduction (1 min)
> "I'm going to show you an AI receptionist that answers your calls 24/7, books appointments, and costs less than a single missed appointment."

### 2. Live Call Scenario (2 min)
Run the CLI agent and type these scenarios:

**Scenario A: Standard Booking**
```
👤 Caller: Hi, I'd like to book an appointment
🤖 Agent: Greets and offers 2 specific times
👤 Caller: Tuesday at 10 AM works
🤖 Agent: Confirms and ends the call
```

**Scenario B: Emergency Call**
```
👤 Caller: I have a terrible toothache, can I come in today?
🤖 Agent: Handles with urgency, offers priority slot
👤 Caller: Yes please, ASAP
🤖 Agent: Books emergency slot
```

**Scenario C: FAQ**
```
👤 Caller: What are your hours?
🤖 Agent: Provides hours from knowledge base
👤 Caller: Do you accept Delta Dental insurance?
🤖 Agent: Answers from knowledge base
```

### 3. Show The Proof (1 min)
Switch to:
- **Google Calendar**: Show the newly created appointments
- **CRM**: Show call log with details
- **Terminal**: Show analytics/stats with `stats` command

### 4. Close (1 min)
> "That was 3 calls in under 2 minutes. Each one was answered. Each one was handled. Each one was logged to your system."
> "The free trial starts today. I'll have it configured for YOUR business in 24 hours."
> "Shall we get started?"
