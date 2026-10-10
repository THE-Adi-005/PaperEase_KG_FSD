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
_SIGNATURES: dict[str, list[tuple[str, str]]] = {
    "ACHIEVES":          [("Method", "Metric")],
    "EVALUATED_ON":      [("Method", "Dataset")],
    "USES_METHOD":       [("Paper", "Method"), ("Section", "Method"), ("Concept", "Method")],
    "DISCUSSES_CONCEPT": [("Section", "Concept"), ("Paper", "Concept")],
    "COMPARES_TO":       [("Method", "Method")],
    "EXTENDS":           [("Method", "Method")],
    "CITES":             [("Paper", "Citation"), ("Citation", "Citation")],
    "SAME_AS":           [("Concept", "Concept"), ("Method", "Method"), ("Dataset", "Dataset")],
}

# ── Profile definitions ───────────────────────────────────────────────

S3 = SchemaProfile(
    name="S3",
    entity_types=["Method", "Dataset", "Metric"],
    llm_relations=["ACHIEVES", "EVALUATED_ON", "USES_METHOD"],
    type_signatures={k: v for k, v in _SIGNATURES.items()
                     if k in {"ACHIEVES", "EVALUATED_ON", "USES_METHOD"}},
    allow_dynamic_relations=False,
)

S5 = SchemaProfile(
    name="S5",
    entity_types=["Method", "Dataset", "Metric", "Concept", "Citation"],
    llm_relations=[
        "ACHIEVES", "EVALUATED_ON", "USES_METHOD",
        "DISCUSSES_CONCEPT", "CITES",
    ],
    type_signatures={k: v for k, v in _SIGNATURES.items()
                     if k in {"ACHIEVES", "EVALUATED_ON", "USES_METHOD",
                              "DISCUSSES_CONCEPT", "CITES"}},
    allow_dynamic_relations=False,
)

# S8 is the *current default* — matches pre-Phase-1 behaviour exactly.
S8 = SchemaProfile(
    name="S8",
    entity_types=["Method", "Dataset", "Metric", "Concept", "Citation"],
    llm_relations=[
        "USES_METHOD", "DISCUSSES_CONCEPT", "EVALUATED_ON",
        "ACHIEVES", "COMPARES_TO", "EXTENDS", "CITES",
    ],
    type_signatures={k: v for k, v in _SIGNATURES.items() if k != "SAME_AS"},
    allow_dynamic_relations=True,
)

S12 = SchemaProfile(
    name="S12",
    entity_types=["Method", "Dataset", "Metric", "Concept", "Citation"],
    llm_relations=[
        "USES_METHOD", "DISCUSSES_CONCEPT", "EVALUATED_ON",
        "ACHIEVES", "COMPARES_TO", "EXTENDS", "CITES", "SAME_AS",
    ],
    type_signatures=dict(_SIGNATURES),
    allow_dynamic_relations=True,
)

PROFILES: dict[str, SchemaProfile] = {
    "S3": S3,
    "S5": S5,
    "S8": S8,
    "S12": S12,
}


def get_active_profile() -> SchemaProfile:
    """Return the active schema profile as specified in settings.

    Uses a lazy import to avoid circular dependency with config.py.
    """
    from app.config import settings  # noqa: PLC0415
    name = getattr(settings, "SCHEMA_PROFILE", "S8")
    profile = PROFILES.get(name)
    if profile is None:
        raise ValueError(
            f"Unknown SCHEMA_PROFILE={name!r}. Valid values: {list(PROFILES)}"
        )
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
