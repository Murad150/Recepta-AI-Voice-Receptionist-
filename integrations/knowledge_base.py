"""
Recepta - Knowledge Base (ChromaDB RAG)
Vector database for storing and retrieving business-specific knowledge.
Supports PDF upload, chunking, embedding, and semantic search.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Optional

from config.settings import (
    CHROMA_DB_PATH,
    CHROMA_COLLECTION_NAME,
    CHROMA_EMBEDDING_FN,
    KNOWLEDGE_DIR,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeBase:
    """
    RAG Knowledge Base using ChromaDB for vector storage.

    Each client gets their own collection with:
    - Business information (services, hours, policies)
    - FAQ data
    - Pricing information
    - Custom scripts and protocols
    """

    def __init__(self):
        self.db_path = CHROMA_DB_PATH
        self.collection_name = CHROMA_COLLECTION_NAME
        self.embedding_fn = CHROMA_EMBEDDING_FN

        # Lazy-loaded components
        self._client = None
        self._collection = None
        self._ollama_service = None

        logger.info(f"Knowledge Base initialized (path={self.db_path})")

    async def initialize(self, ollama_service=None):
        """
        Initialize ChromaDB client and create/get collection.

        Args:
            ollama_service: LLM service for generating embeddings (optional)
        """
        try:
            import chromadb
            from chromadb.config import Settings

            self._ollama_service = ollama_service

            # Create ChromaDB client with persistent storage
            self._client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(anonymized_telemetry=False),
            )

            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )

            logger.info(f"ChromaDB initialized (collection: {self.collection_name})")
            return True

        except ImportError:
            logger.error(
                "chromadb not installed. Install with: pip install chromadb"
            )
            return False
        except Exception as e:
            logger.error(f"ChromaDB initialization failed: {e}")
            return False

    # ─── Embedding Generation ──────────────────────────────────────────────

    async def _get_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a text chunk.

        Uses Ollama's embedding model if available, otherwise uses ChromaDB's
        built-in all-MiniLM-L6-v2 (which is downloaded automatically).
        """
        if self._ollama_service:
            embedding = await self._ollama_service.get_embedding(text)
            if embedding:
                return embedding

        # Fallback: Use ChromaDB's default embedding function
        return []  # ChromaDB will handle this with its default embedding function

    # ─── Text Chunking ────────────────────────────────────────────────────

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 100,
    ) -> list[dict]:
        """
        Split text into overlapping chunks for embedding.

        Args:
            text: Source text to split
            chunk_size: Max characters per chunk
            overlap: Character overlap between chunks

        Returns:
            List of dicts with chunk text and metadata
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Find last sentence end within the chunk
                sentence_end = max(
                    text.rfind(". ", start, end),
                    text.rfind("! ", start, end),
                    text.rfind("? ", start, end),
                    text.rfind("\n\n", start, end),
                )
                if sentence_end > start + chunk_size // 2:
                    end = sentence_end + 1

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk_id = hashlib.md5(chunk_text.encode()).hexdigest()[:12]
                chunks.append({
                    "id": chunk_id,
                    "text": chunk_text,
                    "start_char": start,
                    "end_char": end,
                })

            start = end - overlap if (end - overlap) > start else end

        logger.debug(f"Text split into {len(chunks)} chunks")
        return chunks

    # ─── Document Ingestion ───────────────────────────────────────────────

    async def add_document(
        self,
        text: str,
        metadata: Optional[dict] = None,
        client_id: Optional[str] = None,
    ) -> int:
        """
        Add a document to the knowledge base.

        Args:
            text: Document text content
            metadata: Additional metadata (source, type, etc.)
            client_id: Optional client identifier for multi-tenant

        Returns:
            Number of chunks added
        """
        if not self._ensure_initialized():
            logger.error("Cannot add document — KB not initialized")
            return 0

        metadata = metadata or {}

        if client_id:
            metadata["client_id"] = client_id

        chunks = self.chunk_text(text)

        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            doc_id = f"{metadata.get('source', 'doc')}_{chunk['id']}"
            if client_id:
                doc_id = f"{client_id}_{doc_id}"

            ids.append(doc_id)
            documents.append(chunk["text"])
            metadatas.append({**metadata, "chunk_id": chunk["id"]})

        try:
            self._collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            logger.info(f"Added {len(chunks)} chunks to knowledge base")
            return len(chunks)

        except Exception as e:
            logger.error(f"Document ingestion failed: {e}")
            return 0

    async def add_pdf(self, pdf_path: str, metadata: Optional[dict] = None) -> int:
        """
        Parse and add a PDF document to the knowledge base.

        Args:
            pdf_path: Path to PDF file
            metadata: Document metadata

        Returns:
            Number of chunks added
        """
        try:
            import PyPDF2

            metadata = metadata or {}
            metadata["source"] = Path(pdf_path).name
            metadata["type"] = "pdf"

            text_parts = []
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(f"[Page {page_num + 1}]\n{text}")

            full_text = "\n\n".join(text_parts)
            return await self.add_document(full_text, metadata)

        except ImportError:
            logger.error("PyPDF2 not installed. Install with: pip install PyPDF2")
            return 0
        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            return 0

    async def add_text_file(self, file_path: str, metadata: Optional[dict] = None) -> int:
        """Add a plain text file to the knowledge base."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            metadata = metadata or {}
            metadata["source"] = Path(file_path).name
            metadata["type"] = "text"
            return await self.add_document(text, metadata)
        except Exception as e:
            logger.error(f"Text file ingestion failed: {e}")
            return 0

    # ─── Semantic Search (RAG) ───────────────────────────────────────────

    async def search(
        self,
        query: str,
        n_results: int = 5,
        client_id: Optional[str] = None,
    ) -> list[dict]:
        """
        Search the knowledge base for relevant context.

        Args:
            query: User's question or query text
            n_results: Number of relevant chunks to return
            client_id: Filter by client (for multi-tenant)

        Returns:
            List of relevant document chunks with scores
        """
        if not self._ensure_initialized():
            logger.error("Cannot search — KB not initialized")
            return []

        try:
            where_filter = {"client_id": client_id} if client_id else None

            results = self._collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,
            )

            # Format results
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            formatted = []
            for i in range(len(documents)):
                formatted.append({
                    "text": documents[i],
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "relevance_score": 1.0 - distances[i] if i < len(distances) else 0.0,
                })

            logger.debug(f"Search returned {len(formatted)} results for: {query[:50]}...")
            return formatted

        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            return []

    # ─── Management ─────────────────────────────────────────────────────

    def _ensure_initialized(self):
        """Ensure ChromaDB is initialized. Returns True if ready."""
        if self._collection is None:
            logger.warning("Knowledge Base not initialized — call initialize() first")
            return False
        return True

    def get_stats(self) -> dict:
        """Get knowledge base statistics."""
        if not self._ensure_initialized():
            return {"total_chunks": 0, "status": "not_initialized"}
        try:
            count = self._collection.count()
            return {
                "total_chunks": count,
                "collection": self.collection_name,
                "db_path": self.db_path,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"total_chunks": 0, "error": str(e)}

    def delete_collection(self):
        """Delete the entire collection."""
        if not self._ensure_initialized():
            logger.warning("Cannot delete — KB not initialized")
            return
        try:
            self._client.delete_collection(self.collection_name)
            self._collection = None
            logger.warning(f"Collection {self.collection_name} deleted")
        except Exception as e:
            logger.error(f"Collection deletion failed: {e}")

    async def close(self):
        """Cleanup."""
        self._client = None
        self._collection = None
        logger.info("Knowledge Base shut down")
