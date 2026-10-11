"""RAG baseline for QA evaluation.

Builds a vector index of Section texts from Neo4j (read-only),
chunks them (~300 words, 50-word overlap), embeds with the same
sentence-transformers model used by embeddings.py, caches to
results/rag_index.pkl.

Usage:
    python -m eval.rag_baseline --rebuild          # rebuild index
    python -m eval.rag_baseline --query "..." --paper-ids id1 id2
"""

import asyncio
import hashlib
import json
import logging
import os
import pickle
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ── Repo root / sys.path setup ──────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.config import settings
from app.services.neo4j_client import neo4j_service

_INDEX_PATH = _REPO_ROOT / "results" / "rag_index.pkl"
_CHUNK_WORDS = 300
_CHUNK_OVERLAP = 50


# ── Chunking ────────────────────────────────────────────────────────────────

def _chunk_text(text: str, max_words: int = _CHUNK_WORDS, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping word-window chunks."""
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = start + max_words
        chunks.append(" ".join(words[start:end]))
        start = end - overlap
        if start >= len(words):
            break
    return chunks


# ── Index build ─────────────────────────────────────────────────────────────

async def _fetch_sections() -> list[dict]:
    """Read all Section nodes from Neo4j (paper_id, section_id, text)."""
    cypher = """
    MATCH (p:Paper)-[:CONTAINS_SECTION]->(s:Section)
    WHERE s.text IS NOT NULL AND size(s.text) > 30
    RETURN p.id AS paper_id, s.id AS section_id, s.text AS text
    """
    async with neo4j_service.driver.session() as session:
        result = await session.run(cypher)
        rows = await result.data()
    return rows


async def build_index(force: bool = False) -> dict:
    """Build (or load cached) chunk index. Returns index dict."""
    if _INDEX_PATH.exists() and not force:
        with open(_INDEX_PATH, "rb") as f:
            idx = pickle.load(f)
        logger.info(f"Loaded RAG index: {len(idx['chunks'])} chunks from {_INDEX_PATH}")
        return idx

    logger.info("Building RAG index from Neo4j sections...")
    await neo4j_service.connect()
    rows = await _fetch_sections()
    logger.info(f"Fetched {len(rows)} sections")

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(settings.EMBEDDING_MODEL)

    chunks = []   # list of {"paper_id", "section_id", "text"}
    for row in rows:
        for c in _chunk_text(row["text"]):
            chunks.append({
                "paper_id": row["paper_id"],
                "section_id": row["section_id"],
                "text": c,
            })

    logger.info(f"Encoding {len(chunks)} chunks...")
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)

    idx = {"chunks": chunks, "embeddings": embeddings}
    _INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_INDEX_PATH, "wb") as f:
        pickle.dump(idx, f)
    logger.info(f"Saved RAG index to {_INDEX_PATH}")
    return idx


# ── Answer function ──────────────────────────────────────────────────────────

_CACHED_INDEX: Optional[dict] = None


async def answer_rag(
    question: str,
    paper_ids: list[str],
    k: int = 5,
    temperature: float = 0.0,
) -> dict:
    """Top-k RAG answer restricted to paper_ids.

    Returns dict: {answer, contexts (list[str]), latency_s}
    """
    global _CACHED_INDEX

    t0 = time.perf_counter()

    if _CACHED_INDEX is None:
        _CACHED_INDEX = await build_index()

    idx = _CACHED_INDEX
    chunks = idx["chunks"]
    embeddings = idx["embeddings"]

    # Filter to paper_ids
    if paper_ids:
        keep = [i for i, c in enumerate(chunks) if c["paper_id"] in paper_ids]
        if not keep:
            return {
                "answer": "Not found in the papers.",
                "contexts": [],
                "latency_s": time.perf_counter() - t0,
            }
        sub_chunks = [chunks[i] for i in keep]
        sub_emb = embeddings[keep]
    else:
        sub_chunks = chunks
        sub_emb = embeddings

    # Embed query
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(settings.EMBEDDING_MODEL)
    q_emb = model.encode([question], convert_to_numpy=True)

    sims = cosine_similarity(q_emb, sub_emb)[0]
    top_k_idx = np.argsort(sims)[::-1][:k]
    top_chunks = [sub_chunks[i]["text"] for i in top_k_idx]
    context = "\n\n---\n\n".join(top_chunks)

    prompt = (
        "Answer the question using ONLY the context below. Be concise. "
        "If the answer is not in the context, reply exactly: Not found in the papers.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    )

    from app.services.llm_client import llm_client
    messages = [{"role": "user", "content": prompt}]
    try:
        answer = await llm_client.generate(messages, temperature=temperature, max_tokens=512)
    except Exception as e:
        logger.error(f"RAG LLM call failed: {e}")
        answer = "Not found in the papers."

    return {
        "answer": answer.strip(),
        "contexts": top_chunks,
        "latency_s": time.perf_counter() - t0,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="RAG baseline")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild index")
    parser.add_argument("--query", type=str, default=None)
    parser.add_argument("--paper-ids", nargs="*", default=[])
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()

    async def main():
        await neo4j_service.connect()
        if args.rebuild:
            await build_index(force=True)
        if args.query:
            result = await answer_rag(args.query, args.paper_ids, k=args.k)
            print(f"\nAnswer: {result['answer']}")
            print(f"Latency: {result['latency_s']:.2f}s")
        await neo4j_service.close()

    asyncio.run(main())
