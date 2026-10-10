"""KG Builder — LLM-driven triple extraction with self-consistency filtering.

Per-section extraction pipeline:
1. Run extraction prompt 2-3x at temp ~0.6 (self-consistency)
2. Keep only triples appearing in majority of runs
3. Schema-validate relation types
4. Parse table data into triples
5. MERGE into Neo4j
"""

import logging
from collections import Counter
from typing import AsyncGenerator

from app.config import settings
from app.models.schemas import ParsedPaper, Triple, PaperStatus
from app.models.neo4j_schema import normalize_relation, validate_relation, register_dynamic_relation
from app.services.llm_client import llm_client
from app.services.neo4j_client import neo4j_service
from app.utils.table_parser import table_to_triples

logger = logging.getLogger(__name__)


async def build_kg(paper: ParsedPaper,
                   extraction_runs: int | None = None,
                   extraction_temp: float | None = None,
                   text_limit: int | None = None,
                   relation_subset: list[str] | None = None) -> AsyncGenerator[dict, None]:
    """Build knowledge graph from a parsed paper.
    
    Optional overrides allow ablation experiments to vary parameters
    without changing global settings.
    
    Yields progress events: {section_idx, total, status, triples_count}
    """
    # Use overrides or fall back to global settings
    num_runs = extraction_runs if extraction_runs is not None else settings.EXTRACTION_RUNS
    temp = extraction_temp if extraction_temp is not None else settings.EXTRACTION_TEMPERATURE
    total_sections = len(paper.sections)
    total_triples = 0

    logger.info(f"Building KG for '{paper.title}' ({total_sections} sections)")

    # Update status to extracting
    await neo4j_service.update_paper_status(paper.id, PaperStatus.EXTRACTING)

    for idx, section in enumerate(paper.sections):
        if not section.text or len(section.text.strip()) < 50:
            # Skip very short sections (e.g., "References")
            yield {"section_idx": idx, "total": total_sections,
                   "status": "skipped", "triples_count": 0}
            continue

        # ── Self-consistency extraction ──
        all_runs_triples = []

        for run_idx in range(num_runs):
            raw_triples = await llm_client.extract_triples(
                section_text=section.text,
                section_id=section.id,
                paper_id=paper.id,
                temperature=temp,
            )
            all_runs_triples.append(raw_triples)

        # ── Majority voting ──
        validated_triples = _self_consistency_filter(
            all_runs_triples, paper.id, section.id
        )

        # ── Merge into Neo4j ──
        if validated_triples:
            count = await neo4j_service.merge_triples(validated_triples)
            total_triples += count
        else:
            count = 0

        progress = (idx + 1) / total_sections * 100
        await neo4j_service.update_paper_status(
            paper.id, PaperStatus.EXTRACTING, progress
        )

        yield {
            "section_idx": idx,
            "section_title": section.title,
            "total": total_sections,
            "status": "extracted",
            "triples_count": count,
            "progress_pct": progress,
        }

        logger.info(
            f"  Section {idx+1}/{total_sections} '{section.title}': "
            f"{count} triples (from {num_runs} runs)"
        )

    # ── Table-to-triple extraction ──
    table_triples = []
    for table in paper.tables:
        if table.rows:
            t_triples = table_to_triples(table, paper.id, table.section_id or "")
            table_triples.extend(t_triples)

    if table_triples:
        table_count = await neo4j_service.merge_triples(table_triples)
        total_triples += table_count
        logger.info(f"  Tables: {table_count} triples from {len(paper.tables)} tables")

    # Update status to linking
    await neo4j_service.update_paper_status(paper.id, PaperStatus.LINKING, 100.0)

    yield {
        "section_idx": total_sections,
        "total": total_sections,
        "status": "complete",
        "triples_count": total_triples,
        "progress_pct": 100.0,
    }

    logger.info(f"KG build complete for '{paper.title}': {total_triples} total triples")


def _self_consistency_filter(all_runs: list[list[dict]],
                              paper_id: str,
                              section_id: str) -> list[Triple]:
    """Filter triples by self-consistency: keep only majority-agreed triples.
    
    A triple is "the same" if (head, relation, tail) match after normalization.
    """
    if not all_runs:
        return []

    # If only 1 run, keep everything
    if len(all_runs) == 1:
        return _dicts_to_triples(all_runs[0], paper_id, section_id)

    # Count occurrences of each (head, relation, tail) tuple
    triple_counts = Counter()
    triple_map = {}

    for run_triples in all_runs:
        seen_in_run = set()
        for t in run_triples:
            if not isinstance(t, dict):
                continue
            head = t.get("head", "").strip()
            tail = t.get("tail", "").strip()
            relation = normalize_relation(t.get("relation", ""))

            if not head or not tail or not relation:
                continue

            key = (head.lower(), relation, tail.lower())
            if key not in seen_in_run:
                seen_in_run.add(key)
                triple_counts[key] += 1
                triple_map[key] = t  # Keep the last raw dict

    # Majority threshold
    threshold = len(all_runs) / 2.0
    majority_triples = []

    for key, count in triple_counts.items():
        if count >= threshold:
            raw = triple_map[key]
            relation = normalize_relation(raw.get("relation", ""))

            # Validate/register relation type
            if not validate_relation(relation):
                register_dynamic_relation(relation)

            majority_triples.append(Triple(
                head=raw.get("head", "").strip(),
                head_type=raw.get("head_type", "Concept"),
                relation=relation,
                tail=raw.get("tail", "").strip(),
                tail_type=raw.get("tail_type", "Concept"),
                source_paper_id=paper_id,
                source_section_id=section_id,
                confidence=count / len(all_runs),
            ))

    return majority_triples


def _dicts_to_triples(raw_list: list[dict], paper_id: str,
                       section_id: str) -> list[Triple]:
    """Convert raw dicts to Triple objects with validation."""
    triples = []
    for t in raw_list:
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
    return triples
