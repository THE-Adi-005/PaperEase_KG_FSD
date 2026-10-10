"""KG Builder — LLM-driven triple extraction with self-consistency filtering.

Per-section extraction pipeline:
1. Run extraction prompt N times at temp T (self-consistency)
2. Keep only triples where count >= ceil(VOTE_FRACTION * N)
3. Schema-validate relation types per active schema profile
4. Parse table data into triples
5. MERGE into Neo4j under config_id
"""

import logging
import math
from collections import Counter
from typing import AsyncGenerator

from app.config import settings
from app.models.schemas import ParsedPaper, Triple, PaperStatus
from app.models.neo4j_schema import (
    normalize_relation,
    validate_relation,
    register_dynamic_relation,
    RELATION_TYPES,
)
from app.schema_profiles import get_active_profile, SchemaProfile
from app.services.llm_client import llm_client
from app.services.neo4j_client import neo4j_service
from app.utils.table_parser import table_to_triples
from app.triple_filters import min_votes

logger = logging.getLogger(__name__)


def _is_triple_valid(
    relation: str,
    head_type: str,
    tail_type: str,
    profile: SchemaProfile,
) -> bool:
    """Validate a triple against dynamic relation policy and type signatures."""
    # Dynamic relation check
    if not settings.ALLOW_DYNAMIC_RELATIONS:
        if relation not in profile.llm_relations and relation not in RELATION_TYPES:
            return False

    # Type signature check
    if settings.ENFORCE_TYPE_SIGNATURES:
        valid_sigs = profile.type_signatures.get(relation)
        if valid_sigs is not None:
            if (head_type, tail_type) not in valid_sigs:
                return False

    return True


async def build_kg(paper: ParsedPaper,
                   config_id: str = "default",
                   extraction_runs: int | None = None,
                   extraction_temp: float | None = None,
                   text_limit: int | None = None,
                   max_triples: int | None = None,
                   relation_subset: list[str] | None = None) -> AsyncGenerator[dict, None]:
    """Build knowledge graph from a parsed paper.

    Optional overrides allow ablation experiments to vary parameters
    without changing global settings. ``config_id`` scopes all semantic
    entity nodes and edges so multiple configs can coexist in one Neo4j
    instance (use 'default' for normal ingestion).

    Yields progress events: {section_idx, total, status, triples_count}
    """
    # Use overrides or fall back to global settings
    num_runs = extraction_runs if extraction_runs is not None else settings.EXTRACTION_RUNS
    temp = extraction_temp if extraction_temp is not None else settings.EXTRACTION_TEMPERATURE
    cap = max_triples if max_triples is not None else settings.MAX_TRIPLES_PER_SECTION
    profile = get_active_profile()
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
                profile=profile,
            )
            all_runs_triples.append(raw_triples)

        # ── Majority voting ──
        validated_triples = _self_consistency_filter(
            all_runs_triples, paper.id, section.id, num_runs
        )

        # ── Triples-per-section cap ──
        if cap and cap > 0:
            validated_triples = validated_triples[:cap]

        # ── Merge into Neo4j ──
        if validated_triples:
            count = await neo4j_service.merge_triples(validated_triples, config_id=config_id)
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
        table_count = await neo4j_service.merge_triples(table_triples, config_id=config_id)
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
                              section_id: str,
                              num_runs: int | None = None) -> list[Triple]:
    """Filter triples by self-consistency.

    A triple passes if it appears in >= ceil(VOTE_FRACTION * N) runs.
    With the default VOTE_FRACTION=0.5 and N=2: ceil(0.5 * 2)=1, so any
    triple seen at least once passes — identical to the previous behaviour.
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

    # Pass threshold: count >= min_votes(N, VOTE_FRACTION)
    n = num_runs if num_runs is not None else len(all_runs)
    threshold = min_votes(n, settings.VOTE_FRACTION)
    majority_triples = []

    profile = get_active_profile()
    for key, count in triple_counts.items():
        if count >= threshold:
            raw = triple_map[key]
            relation = normalize_relation(raw.get("relation", ""))
            head_type = raw.get("head_type", "Concept")
            tail_type = raw.get("tail_type", "Concept")

            if not _is_triple_valid(relation, head_type, tail_type, profile):
                continue

            # Validate/register relation type
            if not validate_relation(relation):
                register_dynamic_relation(relation)

            majority_triples.append(Triple(
                head=raw.get("head", "").strip(),
                head_type=head_type,
                relation=relation,
                tail=raw.get("tail", "").strip(),
                tail_type=tail_type,
                source_paper_id=paper_id,
                source_section_id=section_id,
                confidence=count / len(all_runs),
            ))

    return majority_triples


def _dicts_to_triples(raw_list: list[dict], paper_id: str,
                       section_id: str) -> list[Triple]:
    """Convert raw dicts to Triple objects with validation."""
    profile = get_active_profile()
    triples = []
    for t in raw_list:
        if not isinstance(t, dict):
            continue
        head = t.get("head", "").strip()
        tail = t.get("tail", "").strip()
        relation = normalize_relation(t.get("relation", ""))
        head_type = t.get("head_type", "Concept")
        tail_type = t.get("tail_type", "Concept")

        if not head or not tail or not relation:
            continue

        if not _is_triple_valid(relation, head_type, tail_type, profile):
            continue

        if not validate_relation(relation):
            register_dynamic_relation(relation)

        triples.append(Triple(
            head=head,
            head_type=head_type,
            relation=relation,
            tail=tail,
            tail_type=tail_type,
            source_paper_id=paper_id,
            source_section_id=section_id,
        ))
    return triples
