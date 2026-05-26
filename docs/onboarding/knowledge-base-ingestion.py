"""
Recepta - Knowledge Base Ingestion Script
Run this for each new client to ingest their business documents into ChromaDB.

Usage:
    python docs/onboarding/knowledge-base-ingestion.py --client "SmileCare Dental" --directory "data/knowledge/smiledental/"
    python docs/onboarding/knowledge-base-ingestion.py --client "Smith Law" --file "data/knowledge/smithlaw/faq.pdf"
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrations.knowledge_base import KnowledgeBase
from services.llm_service import LLMService
from utils.logger import setup_logger

logger = setup_logger("ingestion")


async def ingest_directory(client_name: str, directory: str):
    """Ingest all documents in a directory for a client."""
    kb = KnowledgeBase()
    llm = LLMService()

    # Check if Ollama is running
    healthy = await llm.health_check()
    if not healthy:
        logger.warning("Ollama not running. ChromaDB will use default embeddings.")

    # Initialize knowledge base
    await kb.initialize(ollama_service=llm)

    dir_path = Path(directory)
    if not dir_path.exists():
        logger.error(f"Directory not found: {directory}")
        return

    total_chunks = 0
    files_found = list(dir_path.glob("*"))

    if not files_found:
        logger.warning(f"No files found in {directory}")
        print(f"\n  ⚠ No files found in {directory}")
        print(f"  Place PDF, .txt, or .md files in this directory and try again.\n")
        return

    print(f"\n  Ingesting documents for: {client_name}")
    print(f"  Source: {directory}\n")

    for file_path in sorted(files_found):
        if file_path.is_dir():
            continue

        metadata = {"client": client_name}

        try:
            if file_path.suffix.lower() == ".pdf":
                chunks = await kb.add_pdf(str(file_path), metadata=metadata)
                print(f"  ✓ PDF   {file_path.name}: {chunks} chunks")

            elif file_path.suffix.lower() in [".txt", ".md", ".csv"]:
                chunks = await kb.add_text_file(str(file_path), metadata=metadata)
                print(f"  ✓ TEXT  {file_path.name}: {chunks} chunks")

            else:
                print(f"  - Skip {file_path.name} (unsupported format)")
                continue

            total_chunks += chunks

        except Exception as e:
            logger.error(f"Failed to ingest {file_path.name}: {e}")
            print(f"  ✗ FAIL  {file_path.name}: {e}")

    print(f"\n  ─────────────────────────────────────")
    print(f"  Total chunks ingested: {total_chunks}")

    stats = kb.get_stats()
    print(f"  KB size: {stats.get('total_chunks', '?')} total items")

    # Quick test search
    print(f"\n  Testing with sample query...")
    results = await kb.search("What services do you offer?", n_results=2)
    if results:
        print(f"  ✓ Search working ({len(results)} results)")
    else:
        print(f"  ⚠ No search results (may need content)")

    await kb.close()
    await llm.close()
    print()


async def ingest_single_file(client_name: str, file_path: str):
    """Ingest a single file for a client."""
    path = Path(file_path)
    if not path.exists():
        logger.error(f"File not found: {file_path}")
        return

    directory = path.parent
    await ingest_directory(client_name, str(directory))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Recepta - Knowledge Base Ingestion")
    parser.add_argument("--client", "-c", required=True, help="Client/business name")
    parser.add_argument("--directory", "-d", help="Directory containing documents")
    parser.add_argument("--file", "-f", help="Single file to ingest")

    args = parser.parse_args()

    if args.file:
        asyncio.run(ingest_single_file(args.client, args.file))
    elif args.directory:
        asyncio.run(ingest_directory(args.client, args.directory))
    else:
        print("Please provide --directory or --file")
        print("Examples:")
        print('  python docs/onboarding/knowledge-base-ingestion.py --client "SmileCare" --directory data/knowledge/smiledental/')
        print('  python docs/onboarding/knowledge-base-ingestion.py --client "Smith Law" --file data/knowledge/smithlaw/faq.pdf')
