"""
Recepta - Main Entry Point
Orchestrates the voice agent pipeline: STT -> LLM -> TTS with LiveKit transport.
Supports multiple industry agents in a multi-tenant architecture.

Usage:
    python main.py                          # Interactive CLI test
    python main.py --industry dental        # Run dental agent
    python main.py --livekit                # Connect via LiveKit
"""

import os
import sys
import asyncio
import argparse
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    DEBUG,
    MULTI_TENANT,
    OLLAMA_MODEL,
    KOKORO_VOICE,
    SPEACHES_BASE_URL,
)
from utils.logger import get_logger, setup_logger

logger = setup_logger("recepta")


async def initialize_services():
    """
    Initialize all AI services.

    Returns:
        Dict of initialized service instances
    """
    from services.stt_service import STTService
    from services.llm_service import LLMService
    from services.tts_service import TTSService
    from services.transport_service import TransportService
    from integrations.calendar import CalendarIntegration
    from integrations.crm import CRMIntegration
    from integrations.knowledge_base import KnowledgeBase

    # ── STT Service ────────────────────────────────────────────────────
    logger.info("Initializing STT Service (Speaches)...")
    stt_service = STTService()

    # ── LLM Service ────────────────────────────────────────────────────
    logger.info(f"Initializing LLM Service (Ollama: {OLLAMA_MODEL})...")
    llm_service = LLMService()

    # ── TTS Service ────────────────────────────────────────────────────
    logger.info(f"Initializing TTS Service (Kokoro: {KOKORO_VOICE})...")
    tts_service = TTSService()

    # ── Transport Service ──────────────────────────────────────────────
    logger.info("Initializing Transport Service (LiveKit)...")
    transport_service = TransportService()

    # ── Calendar Integration ──────────────────────────────────────────
    logger.info("Initializing Calendar Integration...")
    calendar_service = CalendarIntegration()
    try:
        await calendar_service.authenticate()
    except Exception as e:
        logger.warning(f"Calendar auth failed (non-fatal): {e}")

    # ── CRM Integration ───────────────────────────────────────────────
    logger.info("Initializing CRM Integration...")
    crm_service = CRMIntegration()
    try:
        crm_service.connect()
    except Exception as e:
        logger.warning(f"CRM connection failed (non-fatal): {e}")

    # ── Knowledge Base ────────────────────────────────────────────────
    logger.info("Initializing Knowledge Base (ChromaDB)...")
    kb_service = KnowledgeBase()
    try:
        await kb_service.initialize(ollama_service=llm_service)
    except Exception as e:
        logger.warning(f"Knowledge Base init failed (non-fatal): {e}")

    # Build services dict with param names matching BaseVoiceAgent.__init__
    services = {
        "stt_service": stt_service,
        "llm_service": llm_service,
        "tts_service": tts_service,
        "transport_service": transport_service,
        "calendar": calendar_service,
        "crm": crm_service,
        "knowledge_base": kb_service,
    }

    logger.info("All services initialized")

    return services


def create_agent(industry: str, business_name: str, services: dict):
    """
    Create the appropriate agent for a given industry.

    Args:
        industry: One of "dental", "legal", "hvac", "real_estate"
        business_name: Name of the client business
        services: Dict of initialized services

    Returns:
        Agent instance
    """
    if industry == "dental":
        from agents.dental_agent import DentalAgent
        return DentalAgent(business_name, **services)
    elif industry == "legal":
        from agents.legal_agent import LegalAgent
        return LegalAgent(business_name, **services)
    elif industry == "hvac":
        from agents.hvac_agent import HVACAgent
        return HVACAgent(business_name, **services)
    elif industry == "real_estate":
        from agents.real_estate_agent import RealEstateAgent
        return RealEstateAgent(business_name, **services)
    else:
        from agents.base_agent import BaseVoiceAgent
        logger.warning(f"Unknown industry '{industry}', using base agent")
        return BaseVoiceAgent(industry, business_name, **services)


# ─── Interactive CLI Mode ─────────────────────────────────────────────────


async def run_cli_mode(industry: str, business_name: str, services: dict):
    """
    Run the voice agent in interactive CLI mode for testing.

    This simulates a phone call in the terminal:
    - You type what the "caller" says
    - The agent processes it and prints the response
    """
    import colorama
    colorama.init()

    print(f"\n{'='*60}")
    print(f"  Recepta - Interactive Test Mode")
    print(f"  Agent: {industry.upper()} | Business: {business_name}")
    print(f"{'='*60}\n")
    print(f"  {colorama.Style.DIM}Type 'quit' to exit, 'restart' to reset{colorama.Style.RESET_ALL}\n")

    agent = create_agent(industry, business_name, services)
    session_id = f"test_{asyncio.get_event_loop().time():.0f}"
    await agent.start(session_id)

    # Agent greeting
    greeting = await agent.handle_greeting()
    print(f"\n{colorama.Fore.GREEN}🤖 {agent.agent_name}:{colorama.Style.RESET_ALL} {greeting}\n")

    conversation_active = True
    while conversation_active:
        try:
            # Get user input (simulating caller speech)
            user_input = input(f"{colorama.Fore.CYAN}👤 Caller:{colorama.Style.RESET_ALL} ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print(f"\n{colorama.Fore.GREEN}🤖 {agent.agent_name}: Thank you for testing!{colorama.Style.RESET_ALL}")
                break
            elif user_input.lower() in ["restart", "reset"]:
                await agent.end()
                session_id = f"test_{asyncio.get_event_loop().time():.0f}"
                await agent.start(session_id)
                greeting = await agent.handle_greeting()
                print(f"\n{colorama.Fore.GREEN}🤖 {agent.agent_name}:{colorama.Style.RESET_ALL} {greeting}\n")
                continue
            elif not user_input:
                continue

            # Process through agent
            agent_response = ""
            async for chunk in agent.process_turn(user_input):
                agent_response += chunk
                print(f"{colorama.Fore.GREEN}🤖 {agent.agent_name}:{colorama.Style.RESET_ALL} {chunk}", end="", flush=True)

            if agent_response:
                print()  # Newline after response

            # Check if agent ended the conversation
            if not agent.is_active:
                print(f"\n{colorama.Fore.YELLOW}📞 Call ended.{colorama.Style.RESET_ALL}")
                conversation_active = False

        except KeyboardInterrupt:
            print(f"\n\n{colorama.Fore.YELLOW}📞 Call interrupted.{colorama.Style.RESET_ALL}")
            break
        except Exception as e:
            logger.error(f"CLI mode error: {e}")
            print(f"\n{colorama.Fore.RED}⚠️ Error: {e}{colorama.Style.RESET_ALL}")

    await agent.end()

    # Print session summary
    print(f"\n{'='*60}")
    print(f"  Session Summary")
    print(f"{'='*60}")
    stats = agent.get_stats()
    for key, value in stats.items():
        if value:
            print(f"  {key}: {value}")
    print(f"  turns: {len(agent.call_transcript)} messages")
    print()


# ─── LiveKit Mode ──────────────────────────────────────────────────────────


async def run_livekit_mode(industry: str, business_name: str, services: dict):
    """
    Run the voice agent connected via LiveKit WebRTC for real calls.
    """
    from services.transport_service import create_livekit_transport

    print(f"\n{'='*60}")
    print(f"  Recepta - LiveKit Mode")
    print(f"  Agent: {industry.upper()} | Business: {business_name}")
    print(f"{'='*60}\n")

    agent = create_agent(industry, business_name, services)
    transport_service = services.get("transport_service")

    if not transport_service:
        logger.error("Transport service not initialized")
        return

    # Connect to LiveKit
    connected = await transport_service.connect()
    if not connected:
        logger.error("Failed to connect to LiveKit. Check your LIVEKIT_URL and credentials.")
        return

    # Set up audio handler
    session_id = f"livekit_{asyncio.get_event_loop().time():.0f}"
    await agent.start(session_id)

    async def on_audio_input(audio_bytes: bytes):
        response_audio = await agent.process_audio(audio_bytes)
        if response_audio:
            await transport_service.send_audio(response_audio)

    transport_service.on_audio_input = on_audio_input

    # Send greeting
    tts_service = services.get("tts_service")
    greeting = await agent.handle_greeting()
    if tts_service:
        greeting_audio = await tts_service.generate(greeting)
        if greeting_audio:
            await transport_service.send_audio(greeting_audio)

    print(f"  🤖 {agent.agent_name} is waiting for calls on LiveKit room: {transport_service.room_name}")
    print(f"  Press Ctrl+C to stop\n")

    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await agent.end()
        await transport_service.disconnect()
        print("Disconnected from LiveKit")


# ─── Health Check ─────────────────────────────────────────────────────────


async def run_health_check():
    """Run a health check on all services."""
    from services.llm_service import LLMService
    from services.stt_service import STTService

    print("\n🔍 Recepta - Health Check\n")

    # Check Ollama
    llm = LLMService()
    ollama_ok = await llm.health_check()
    print(f"  {'✓' if ollama_ok else '✗'} Ollama ({OLLAMA_MODEL})")
    await llm.close()

    # Check Speaches
    stt = STTService()
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SPEACHES_BASE_URL}/v1/models") as resp:
                speaches_ok = resp.status == 200
                print(f"  {'✓' if speaches_ok else '✗'} Speaches STT ({SPEACHES_BASE_URL})")
    except Exception:
        print(f"  ✗ Speaches STT ({SPEACHES_BASE_URL}) - not reachable")

    # Check environment
    print(f"  {'✓' if os.getenv('LIVEKIT_API_KEY') else '✗'} LiveKit API Key configured")
    print(f"  {'✓' if os.path.exists('config/google_credentials.json') else '✗'} Google Calendar credentials")

    print("\n  Note: Some checks may fail if services aren't running yet.")
    print("  See README.md for setup instructions.\n")


# ─── Main ────────────────────────────────────────────────────────────────


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Recepta - 24/7 AI Receptionist for Small Businesses",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                        # Interactive CLI test (default: dental)
  python main.py --industry hvac        # Test HVAC agent
  python main.py --livekit              # Run live via LiveKit
  python main.py --check                # Health check all services
  python main.py --industry real_estate --business "Premier Properties"
        """,
    )
    parser.add_argument("--industry", "-i", default="dental",
                        choices=["dental", "legal", "hvac", "real_estate"],
                        help="Industry/agent type (default: dental)")
    parser.add_argument("--business", "-b", default="Your Practice",
                        help="Business name (default: 'Your Practice')")
    parser.add_argument("--livekit", "-l", action="store_true",
                        help="Run with LiveKit transport for real calls")
    parser.add_argument("--check", "-c", action="store_true",
                        help="Run health check only")
    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()

    print(f"""
    ╔═══════════════════════════════════════╗
    ║          Recepta v1.0              ║
    ║    24/7 AI Receptionist System      ║
    ╚═══════════════════════════════════════╝
    """)

    if args.check:
        await run_health_check()
        return

    # Initialize all services
    logger.info("Initializing services...")
    services = await initialize_services()

    if args.livekit:
        await run_livekit_mode(args.industry, args.business, services)
    else:
        await run_cli_mode(args.industry, args.business, services)

    # Cleanup
    for name, service in services.items():
        if hasattr(service, "close"):
            try:
                await service.close()
            except Exception as e:
                logger.debug(f"Cleanup error for {name}: {e}")

    logger.info("Recepta shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
