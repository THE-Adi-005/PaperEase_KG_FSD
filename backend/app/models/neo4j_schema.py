"""Neo4j schema definitions — node labels, relation types, and validation.

The schema is split into:
  RELATION_TYPES         — semantic relations (LLM-extractable + SAME_AS)
  STRUCTURAL_RELATIONS   — relations emitted only by merge_paper / table_parser
  SEMANTIC_ENTITY_LABELS — entity nodes that carry config_id and norm_name
  GRAPH_STATS_EXCLUDE_RELATIONS — excluded from the semantic graph_stats helper

Dead entries removed (declared but never emitted by any code path):
  PART_OF, BELONGS_TO, REFERENCES_FIGURE, REFERENCES_TABLE
"""

# ── Semantic entity labels (carry config_id + norm_name) ─────────────
SEMANTIC_ENTITY_LABELS: list[str] = [
    "Concept",
    "Method",
    "Dataset",
    "Metric",
    "Citation",
]

# ── Node Labels ──────────────────────────────────────────────────────
NODE_LABELS: list[str] = [
    "Paper",
    "Author",
    "Section",
    "Figure",
    "Table",
] + SEMANTIC_ENTITY_LABELS

# ── Semantic Relationship Types ───────────────────────────────────────
# REPORTS_METRIC is emitted only by table_to_triples (not the LLM prompt).
# SAME_AS is emitted only by the embedding service.
RELATION_TYPES: list[str] = [
    "DISCUSSES_CONCEPT",  # Section/Paper → Concept
    "USES_METHOD",        # Paper/Section/Concept → Method
    "REPORTS_METRIC",     # Method/Table → Metric  (table_to_triples only)
    "ILLUSTRATED_BY",     # Section → Figure | Table
    "CITES",              # Paper → Citation
    "SAME_AS",            # Concept/Method/Dataset ↔ Concept/Method/Dataset (embeddings)
    "EVALUATED_ON",       # Method → Dataset
    "ACHIEVES",           # Method → Metric (with value)
    "COMPARES_TO",        # Method → Method
    "EXTENDS",            # Method → Method
]

# ── Structural Relations (emitted by merge_paper, never by LLM) ───────
STRUCTURAL_RELATIONS: set[str] = {
    "AUTHORED_BY",
    "CONTAINS_SECTION",
    "CONTAINS_FIGURE",
    "CONTAINS_TABLE",
}

# Relations excluded from semantic graph_stats counts
GRAPH_STATS_EXCLUDE_RELATIONS: set[str] = STRUCTURAL_RELATIONS | {
    "ILLUSTRATED_BY",
}

# Keep a mutable set for dynamically discovered relation types
_dynamic_relations: set[str] = set()


def validate_relation(relation: str) -> bool:
    """Check if a relation type is in the seed or dynamic schema."""
    return relation in RELATION_TYPES or relation in _dynamic_relations


def register_dynamic_relation(relation: str) -> None:
    """Register a new relation type discovered during extraction."""
    if relation not in RELATION_TYPES:
        _dynamic_relations.add(relation)


def normalize_relation(relation: str) -> str:
    """Normalize a relation string to UPPER_SNAKE_CASE."""
    return relation.strip().upper().replace(" ", "_").replace("-", "_")


def get_all_relations() -> list[str]:
    """Return all known relation types (seed + dynamic)."""
    return RELATION_TYPES + sorted(_dynamic_relations)


# ── Neo4j constraint & index setup queries ──────────────────────────
SETUP_QUERIES: list[str] = [
    # Structural-node uniqueness constraints
    "CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT author_id IF NOT EXISTS FOR (a:Author) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT section_id IF NOT EXISTS FOR (s:Section) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT figure_id IF NOT EXISTS FOR (f:Figure) REQUIRE f.id IS UNIQUE",
    "CREATE CONSTRAINT table_id IF NOT EXISTS FOR (t:Table) REQUIRE t.id IS UNIQUE",

    # Composite lookup index for semantic entity nodes (norm_name + config_id)
    "CREATE INDEX entity_norm_config IF NOT EXISTS FOR (n:Entity) ON (n.norm_name, n.config_id)",

    # Full-text indexes for entity search (used by RetrieveNode agent tool)
    """CREATE FULLTEXT INDEX entity_name_index IF NOT EXISTS
       FOR (n:Concept|Method|Dataset|Metric|Figure|Table|Citation|Author)
       ON EACH [n.name]""",

    """CREATE FULLTEXT INDEX section_text_index IF NOT EXISTS
       FOR (s:Section)
       ON EACH [s.title, s.text]""",

    # Regular indexes for common lookups
    "CREATE INDEX paper_title IF NOT EXISTS FOR (p:Paper) ON (p.title)",
]
