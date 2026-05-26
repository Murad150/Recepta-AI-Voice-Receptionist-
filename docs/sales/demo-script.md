# Recepta — Demo & Sales System

## 5-Minute Demo Script That Guarantees "YES"

### THE SETUP (30 seconds)

> "Hi [Client Name], thank you for taking the time to see this. I'm going to show you something most businesses don't realize exists yet — an AI receptionist that sounds completely human, works 24/7, and costs less than what you're paying for missed calls."

### THE PROBLEM (60 seconds)

> "Let me ask you a question: How many calls did your business get yesterday?"
>
> *(Wait for answer)*
>
> "And how many went to voicemail?"
>
> *(Pause for acknowledgment)*
>
> "Here's the math that keeps me up at night. If you get [X] missed calls per day, and each call is worth an average of [$Y] in revenue, that's [~$500-$2000] per day in lost revenue. Every single day."
>
> "And the worst part? Most of those people don't call back. They call your competitor."

### THE SOLUTION (90 seconds)

> "This is Recepta. Watch what happens when a patient calls your practice after hours."

**→ CALL the agent on speakerphone or play recording**

*Caller*: "Hi, my tooth has been hurting for two days. Can I come in?"
*Sarah*: "I'm sorry to hear you're in pain, [Name]. Let me check our schedule. We have tomorrow at 10 AM or 2 PM. Which works better?"
*Caller*: "10 AM works."
*Sarah*: "Perfect, you're booked for tomorrow at 10 AM with Dr. [Name]. You'll get a confirmation text right away. Is there anything else I can help with?"

> *(Hang up)*

> "That call took 45 seconds. The patient is booked. You didn't lift a finger. And here's the best part — it was after 8 PM on a Sunday."

### THE PROOF (45 seconds)

> "Let me show you what just happened behind the scenes:"

- **→ Show Google Calendar** with the new appointment
- **→ Show CRM log** with the call details
- **→ Show the call transcript**

> "This is not a demo. This is production. Every call is logged. Every appointment is on your calendar. Every patient gets a confirmation text."

### THE ROI (45 seconds)

> "Let's do the math together:"

| Item | Value |
|------|-------|
| Missed calls/day | 10 |
| Average appointment value | $250 |
| Lost revenue/day | $2,500 |
| Lost revenue/month | **$55,000** |
| **Our price/month** | **$300-$500** |

> "You're losing 100x more than what I'm charging. The question isn't 'Can I afford this?' — it's 'Can I afford NOT to have this?'"

### THE OFFER (30 seconds)

> "Here's what I'm proposing: I'll set up a FREE 7-day trial for your practice. No credit card. No commitment. I'll configure it with your business name, your services, your calendar. You just sit back and watch the calls come in."
>
> "If you like what you see, we'll talk about a plan that fits your budget. If not — no hard feelings, and you keep the data."
>
> **"When can we get started?"**

---

## ROI Calculator

Share this with every potential client:

### Missed Call Revenue Calculator

```python
# Quick ROI calculation for client calls

def calculate_roi(
    daily_calls: int,
    answer_rate: float,  # e.g., 0.6 = answer 60% of calls
    avg_appointment_value: float,
    working_days_per_month: int = 22,
):
    missed = daily_calls * (1 - answer_rate)
    monthly_loss = missed * avg_appointment_value * working_days_per_month
    yearly_loss = monthly_loss * 12

    print(f"Daily missed calls: {missed:.0f}")
    print(f"Monthly revenue lost: ${monthly_loss:,.0f}")
    print(f"Yearly revenue lost: ${yearly_loss:,.0f}")
    print(f"Our monthly price: ${'300-800 depending on plan'}")

# Example for a dental clinic:
calculate_roi(
    daily_calls=30,
    answer_rate=0.6,  # Answer 60% of calls
    avg_appointment_value=250,
)
```

### Before/After Comparison Template

| Metric | Before (Without AI) | After (With Recepta) |
|--------|-------------------|----------------------|
| Call Answer Rate | 40-60% | 99%+ |
| After-Hours Coverage | ❌ Voicemail | ✅ Live agent |
| New Appointments/Day | Losing 5-10 | Capturing +Booked |
| Staff Time on Phone | 3-4 hours/day | Zero hours |
| Patient Satisfaction | Missed calls = angry | Always answered |
| Monthly Lost Revenue | $10,000-$50,000 | $0 |

---

## Objection Handling Guide

### 10 Common Objections & Responses

**1. "It sounds robotic / My patients won't like it"**
> "I totally understand that concern. Most people can't tell it's AI — in fact, several of my clients' patients have asked to speak to 'Sarah' specifically because she's so friendly. Would you be open to a blind test where I play a recording and you try to guess if it's human or AI?"

**2. "It's too expensive"**
> "I hear you. Let me ask — how much does ONE missed appointment cost you in lost revenue? For most practices, our service pays for itself after booking just 2-3 appointments per month. We're not an expense — we're a revenue generator."

**3. "I need to think about it / talk to my partner"**
> "Absolutely, I respect that. Would it help if I set up a free 7-day trial so you can both see it in action? That way you'll have real data to make your decision, not just a sales pitch."

**4. "What if it makes mistakes?"**
> "Fair question. The system is designed with safety guardrails — if it doesn't know something, it politely says it'll have a human follow up. Plus, every single call is transcribed and logged so you can review them. You have full visibility."

**5. "My current receptionist handles everything fine"**
> "That's great to hear. Does your receptionist answer calls during lunch? After hours? On weekends? While they're with patients? Recepta isn't a replacement — it's a backup that ensures no call ever goes unanswered."

**6. "How is this different from a voicemail system?"**
> "Great question. Voicemail is passive — it waits for people to leave a message. Recepta is active — it books appointments, answers questions, triages emergencies, and logs everything to your CRM. It's an active member of your team."

**7. "I'm worried about HIPAA compliance"**
> "HIPAA compliance is a priority. Our system runs entirely on your local hardware, no data leaves your network. All conversations are encrypted. We can also sign a BAA if needed."

**8. "I want to see it work for MY business specifically"**
> "Perfect — that's exactly what our free trial is for. I'll configure it for YOUR business, YOUR services, and YOUR calendar. You'll see it handle YOUR actual calls."

**9. "What if I want to cancel?"**
> "No contracts. Month-to-month. Cancel anytime with 30 days notice. You keep all your data — call logs, booked appointments, everything. We make it risk-free."

**10. "I need references from similar businesses"**
> "Absolutely, I have [X] clients in your exact industry who saw [Y] results. Let me share their contact info and you can hear directly from them."

---

## Live Demo Flow

### Step-by-Step Demo Process

1. **Pre-Demo Setup** (10 min before call)
   - Open terminal with `python main.py --industry dental --business "Client Name"` ready
   - Have Google Calendar tab open showing empty tomorrow
   - Have a sample knowledge base loaded
   - Open CRM dashboard showing 0 calls today

2. **During Demo** (5 min)
   - Run the interactive CLI demo
   - Let them type in caller scenarios
   - Show real-time responses
   - After booking, show calendar populated
   - After ending, show CRM with call logged

3. **Post-Demo** (5 min)
   - Walk through ROI calculator
   - Address objections
   - Propose next step (free trial)

---

## Pricing Packages

| Feature | Starter | Pro | Enterprise |
|---------|---------|-----|------------|
| **Setup Fee** | $1,500 | $3,000 | $5,000 |
| **Monthly** | $300/mo | $500/mo | $800/mo |
| **Minutes/Month** | 500 | 2,000 | Unlimited |
| **Agents** | 1 industry | 3 industries | Unlimited |
| **Voice Options** | Default voice | 5 voice options | Custom clone |
| **Calendar Integration** | Manual | Google Calendar | Google + Outlook |
| **CRM & Analytics** | Basic | Full dashboard | White-label |
| **Knowledge Base** | FAQ only | Full KB upload | Custom KB builder |
| **Support** | Email | Email + Chat | Priority + Slack |
| **Phone Number** | Bring your own | We set up | We manage all |
| **Ideal For** | Solo practitioners | Small practices | Multi-location |
