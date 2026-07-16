"""Query-driven lazy graph completion.

The key architectural contribution (Section 7, technique #1):
Instead of exhaustive extraction on ingest, trigger targeted re-extraction
at query time when the Agent can't find enough information.

This closes the loop between KG construction (normally front-loaded) and
reasoning-time retrieval (normally read-only against a static graph).

Metrics logged: trigger count, new triples added, success rate.
"""

import logging
from typing import Optional

from app.services.llm_client import llm_client
from app.services.neo4j_client import neo4j_service
from app.models.schemas import Triple
from app.models.neo4j_schema import normalize_relation, validate_relation, register_dynamic_relation

logger = logging.getLogger(__name__)

# ── Metrics tracking ──
_metrics = {
    "total_triggers": 0,
    "successful_triggers": 0,
    "total_new_triples": 0,
}


async def trigger_lazy_completion(question: str, thought: str,
                                   action_name: str, action_input: str,
                                   paper_ids: list[str]) -> int:
    """Attempt targeted re-extraction to fill a gap in the KG.
    
    1. Identify what's missing from the agent's thought + failed action
    2. Find relevant source sections
    3. Run focused extraction on those sections
    4. MERGE new triples
    
    Returns: number of new triples added
    """
    _metrics["total_triggers"] += 1

    # Build a description of what's missing
    missing_info = f"{thought}. Looking for: {action_input}"
    logger.info(f"Lazy completion triggered: {missing_info[:100]}...")

    total_new = 0

    for paper_id in paper_ids:
        # Get all sections for the paper
        sections = await neo4j_service.get_sections_for_paper(paper_id)

        if not sections:
            continue

        # Find most relevant sections (simple keyword matching for MVP)
        keywords = _extract_keywords(action_input, thought)
        relevant_sections = _rank_sections(sections, keywords)

        for section in relevant_sections[:2]:  # Re-extract from top 2 sections
            section_text = section.get("text", "")
            section_id = section.get("id", "")

            if not section_text or len(section_text) < 50:
                continue

            # Targeted extraction
            raw_triples = await llm_client.extract_triples_targeted(
                section_text=section_text,
                missing_info=missing_info,
                section_id=section_id,
                paper_id=paper_id,
            )

            if not raw_triples:
                continue

            # Convert and merge
            triples = []
            for t in raw_triples:
                if not isinstance(t, dict):
                    continue
                head = t.get("head", "").strip()
                tail = t.get("tail", "").strip()
                relation = normalize_relation(t.get("relation", ""))

                if not head or not tail or not relation:
                    continue

                if not validate_relation(relation):
                    register_dynamic_relation(relation)

                triples.append(Triple(
                    head=head,
                    head_type=t.get("head_type", "Concept"),
                    relation=relation,
                    tail=tail,
                    tail_type=t.get("tail_type", "Concept"),
                    source_paper_id=paper_id,
                    source_section_id=section_id,
                ))

            if triples:
                count = await neo4j_service.merge_triples(triples)
                total_new += count
                logger.info(
                    f"Lazy completion: added {count} triples "
                    f"from section '{section.get('title', section_id)}'"
                )

    if total_new > 0:
        _metrics["successful_triggers"] += 1
        _metrics["total_new_triples"] += total_new

    return total_new


def _extract_keywords(action_input: str, thought: str) -> list[str]:
    """Extract search keywords from the agent's action and thought."""
    # Combine inputs and extract meaningful words
    text = f"{action_input} {thought}".lower()
    # Remove common words
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "can", "shall", "to", "of",
        "in", "for", "on", "with", "at", "by", "from", "as", "into",
        "through", "during", "before", "after", "above", "below",
        "between", "out", "off", "over", "under", "again", "further",
        "then", "once", "here", "there", "when", "where", "why", "how",
        "all", "each", "every", "both", "few", "more", "most", "other",
        "some", "such", "no", "nor", "not", "only", "own", "same",
        "so", "than", "too", "very", "just", "because", "but", "and",
        "or", "if", "this", "that", "these", "those", "what", "which",
        "who", "whom", "i", "we", "need", "find", "search", "look",
        "get", "check", "about", "related", "information", "node",
    }
    words = text.split()
    keywords = [w.strip('",.:;!?()[]') for w in words if w.strip('",.:;!?()[]') not in stopwords and len(w) > 2]
    return list(dict.fromkeys(keywords))[:10]  # Dedupe, keep order, max 10


def _rank_sections(sections: list[dict], keywords: list[str]) -> list[dict]:
    """Rank sections by keyword relevance."""
    scored = []
    for section in sections:
        text_lower = (section.get("text", "") + " " + section.get("title", "")).lower()
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scored.append((score, section))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s[1] for s in scored]


def get_metrics() -> dict:
    """Return lazy completion metrics for evaluation."""
    return {
        "total_triggers": _metrics["total_triggers"],
        "successful_triggers": _metrics["successful_triggers"],
        "total_new_triples": _metrics["total_new_triples"],
        "trigger_rate": (
            _metrics["successful_triggers"] / _metrics["total_triggers"]
            if _metrics["total_triggers"] > 0 else 0.0
        ),
    }


def reset_metrics():
    """Reset metrics (for evaluation runs)."""
    _metrics["total_triggers"] = 0
    _metrics["successful_triggers"] = 0
    _metrics["total_new_triples"] = 0
