"""Naive RAG baseline — context-stuffing without Knowledge Graph.

This service provides a baseline QA mode that does NOT use the Knowledge Graph.
Instead, it simply:
  1. Retrieves all section text for the selected papers from Neo4j
  2. Concatenates the raw text as context
  3. Sends context + question to the LLM for a direct answer

This is the standard "chunked text + LLM" approach used by most RAG systems.
By comparing this baseline to the KG-grounded agent, we can quantify the
improvement that Knowledge Graph reasoning provides.

Yields SSE events in the same format as the KG agent for fair comparison.
"""

import logging
import time
from typing import AsyncGenerator

from app.services.neo4j_client import neo4j_service
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)

# ── Metrics tracking ──
_metrics = {
    "total_queries": 0,
    "total_latency_ms": 0,
    "avg_context_chars": 0,
}


NAIVE_SYSTEM_PROMPT = """You are a research paper analysis assistant. Answer the user's question using ONLY the provided context from research papers.

RULES:
- Base your answer strictly on the provided context
- If the context does not contain enough information, say so clearly
- Cite specific facts and numbers from the context when possible
- Be concise but thorough

CONTEXT:
{context}
"""


async def run_naive_rag(question: str, paper_ids: list[str]) -> AsyncGenerator[dict, None]:
    """Run naive RAG — direct text retrieval + LLM, no KG traversal.

    Yields SSE events matching the agent format for UI compatibility:
    - {event: "thought", data: {step, text}}
    - {event: "answer", data: {text, steps_used}}
    - {event: "error", data: {message}}
    """
    _metrics["total_queries"] += 1
    start_time = time.time()

    # Step 1: Retrieve all section texts
    yield {
        "event": "thought",
        "data": {
            "step": 1,
            "text": "Retrieving raw paper text (no Knowledge Graph — baseline mode)...",
        },
    }

    all_context = []
    for paper_id in paper_ids:
        sections = await neo4j_service.get_sections_for_paper(paper_id)
        if not sections:
            continue

        # Also get the paper title for attribution
        paper_info = await neo4j_service.get_paper_info(paper_id)
        paper_title = paper_info.title if paper_info else paper_id

        paper_text_parts = [f"--- Paper: {paper_title} ---"]
        for section in sections:
            title = section.get("title", "Untitled")
            text = section.get("text", "")
            if text and len(text.strip()) > 30:
                paper_text_parts.append(f"\n## {title}\n{text}")

        all_context.append("\n".join(paper_text_parts))

    context = "\n\n".join(all_context)

    if not context.strip():
        yield {
            "event": "error",
            "data": {"message": "No paper text found for the selected papers."},
        }
        return

    # Truncate context to fit within typical LLM context windows
    MAX_CONTEXT_CHARS = 12_000
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n[... context truncated ...]"

    _metrics["avg_context_chars"] = (
        (_metrics["avg_context_chars"] * (_metrics["total_queries"] - 1) + len(context))
        / _metrics["total_queries"]
    )

    yield {
        "event": "thought",
        "data": {
            "step": 2,
            "text": f"Sending {len(context):,} characters of raw text to LLM (no graph reasoning)...",
        },
    }

    # Step 2: Send context + question directly to LLM
    system_prompt = NAIVE_SYSTEM_PROMPT.format(context=context)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    try:
        answer_text = await llm_client.generate(
            messages, temperature=0.1, max_tokens=1024
        )
    except Exception as e:
        yield {"event": "error", "data": {"message": f"LLM error: {str(e)}"}}
        return

    elapsed_ms = int((time.time() - start_time) * 1000)
    _metrics["total_latency_ms"] += elapsed_ms

    # Step 3: Return answer
    yield {
        "event": "answer",
        "data": {
            "text": answer_text,
            "steps_used": 1,  # Always 1 step — no multi-step reasoning
            "lazy_completion_count": 0,  # No lazy completion in naive mode
            "mode": "naive_rag",
            "context_chars": len(context),
            "estimated_tokens": len(context) // 4,
            "latency_ms": elapsed_ms,
        },
    }

    # No subgraph in naive mode — no graph was traversed
    yield {"event": "done", "data": {}}


def get_naive_metrics() -> dict:
    """Return naive RAG metrics for evaluation comparison."""
    return {
        "total_queries": _metrics["total_queries"],
        "avg_latency_ms": (
            _metrics["total_latency_ms"] / _metrics["total_queries"]
            if _metrics["total_queries"] > 0
            else 0
        ),
        "avg_context_chars": int(_metrics["avg_context_chars"]),
    }


def reset_naive_metrics():
    """Reset metrics (for evaluation runs)."""
    _metrics["total_queries"] = 0
    _metrics["total_latency_ms"] = 0
    _metrics["avg_context_chars"] = 0
