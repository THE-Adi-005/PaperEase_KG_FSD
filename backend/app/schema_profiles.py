"""Schema profiles for KG extraction experiments.

Four profiles of increasing schema richness. Profile name is the single
source of truth for which entity types and relation types the LLM is asked
to produce. Both ``llm_client.extract_triples`` and the agent prompt read
from the active profile at runtime.

NOTE:
  - REPORTS_METRIC is intentionally absent from every ``llm_relations`` list.
    It is emitted *only* by ``table_to_triples`` (deterministic, structured path).
  - SAME_AS is emitted *only* by the embedding service (never by LLM prompt).
  - CONTAINS_FIGURE / CONTAINS_TABLE / AUTHORED_BY / CONTAINS_SECTION are
    structural and live in ``neo4j_schema.STRUCTURAL_RELATIONS``.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import re


@dataclass
class SchemaProfile:
    name: str
    entity_types: list[str]
    llm_relations: list[str]          # Relation types the LLM is asked to emit
    type_signatures: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    allow_dynamic_relations: bool = True


# ── Canonical (head_type, tail_type) signatures ──────────────────────
ENTITY_TYPES = ["Method", "Dataset", "Metric", "Concept", "Citation"]
ALL_HEADS = ENTITY_TYPES + ["Paper", "Section"]
_ORDER = [
    "USES_METHOD",
    "DISCUSSES_CONCEPT",
    "EVALUATED_ON",
    "ACHIEVES",
    "COMPARES_TO",
    "EXTENDS",
    "CITES",
    "TRAINED_ON",
    "OUTPERFORMS",
    "HAS_COMPONENT",
]
_R3 = {"USES_METHOD", "EVALUATED_ON", "ACHIEVES"}
_R5 = _R3 | {"COMPARES_TO", "EXTENDS"}
_R7 = _R5 | {"DISCUSSES_CONCEPT", "CITES"}
_R10 = _R7 | {"TRAINED_ON", "OUTPERFORMS", "HAS_COMPONENT"}
_SIGNATURES = {
    "ACHIEVES": [("Method", "Metric")],
    "EVALUATED_ON": [("Method", "Dataset")],
    "USES_METHOD": [(h, t) for h in ALL_HEADS for t in ("Method", "Concept")],
    "DISCUSSES_CONCEPT": [(h, "Concept") for h in ALL_HEADS],
    "COMPARES_TO": [("Method", "Method")],
    "EXTENDS": [("Method", "Method")],
    "CITES": [(h, "Citation") for h in ALL_HEADS],
    "TRAINED_ON": [("Method", "Dataset")],
    "OUTPERFORMS": [("Method", "Method")],
    "HAS_COMPONENT": [("Method", "Method"), ("Method", "Concept")],
    "SAME_AS": [("Concept", "Concept"), ("Method", "Method"), ("Dataset", "Dataset")],
}

# ── Profile definitions ───────────────────────────────────────────────

R3 = SchemaProfile(
    name="R3",
    entity_types=ENTITY_TYPES,
    llm_relations=[r for r in _ORDER if r in _R3],
    type_signatures={r: _SIGNATURES[r] for r in _ORDER if r in _R3},
)

R5 = SchemaProfile(
    name="R5",
    entity_types=ENTITY_TYPES,
    llm_relations=[r for r in _ORDER if r in _R5],
    type_signatures={r: _SIGNATURES[r] for r in _ORDER if r in _R5},
)

R7 = SchemaProfile(
    name="R7",
    entity_types=ENTITY_TYPES,
    llm_relations=[r for r in _ORDER if r in _R7],
    type_signatures={r: _SIGNATURES[r] for r in _ORDER if r in _R7},
)

R10 = SchemaProfile(
    name="R10",
    entity_types=ENTITY_TYPES,
    llm_relations=[r for r in _ORDER if r in _R10],
    type_signatures={r: _SIGNATURES[r] for r in _ORDER if r in _R10},
)

PROFILES: dict[str, SchemaProfile] = {
    "R3": R3,
    "R5": R5,
    "R7": R7,
    "R10": R10,
    "S8": R7,
}


def get_active_profile() -> SchemaProfile:
    """Return the active schema profile as specified in settings.

    Uses a lazy import to avoid circular dependency with config.py.
    """
    from app.config import settings  # noqa: PLC0415
    name = getattr(settings, "SCHEMA_PROFILE", "R7")
    profile = PROFILES.get(name)
    if profile is None:
        return PROFILES["R7"]
    return profile


def norm_name(name: str) -> str:
    """Normalize an entity name for the Neo4j MERGE key.

    Lower-cases, strips surrounding whitespace, collapses internal runs of
    whitespace to a single space.

    Examples::

        norm_name("  BERT  ")     -> "bert"
        norm_name("GPT-3\\n")     -> "gpt-3"
        norm_name("F1  Score")    -> "f1 score"
    """
    return re.sub(r"\s+", " ", name.lower().strip())
