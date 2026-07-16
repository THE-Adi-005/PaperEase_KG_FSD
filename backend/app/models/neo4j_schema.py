"""Neo4j schema definitions — node labels, relation types, and validation.

The schema is designed to be additive: new relation types can be added
without breaking existing queries. The seed schema below covers the
core types from the build spec (Section 4).
"""

# ── Node Labels ──────────────────────────────────────────────────────
NODE_LABELS: list[str] = [
    "Paper",
    "Author",
    "Section",
    "Concept",
    "Method",
    "Dataset",
    "Metric",
    "Figure",
    "Table",
    "Citation",
]

# ── Relationship Types (seed schema) ────────────────────────────────
RELATION_TYPES: list[str] = [
    "AUTHORED_BY",        # Paper -> Author
    "CONTAINS_SECTION",   # Paper -> Section
    "DISCUSSES_CONCEPT",  # Section -> Concept
    "USES_METHOD",        # Paper/Section -> Method
    "REPORTS_METRIC",     # Method/Table -> Metric (value property)
    "ILLUSTRATED_BY",     # Section -> Figure | Table
    "CITES",              # Paper -> Citation
    "SAME_AS",            # Concept -> Concept (cross-paper, embedding)
    "EVALUATED_ON",       # Method -> Dataset
    "PART_OF",            # Section -> Paper (inverse convenience)
    "REFERENCES_FIGURE",  # Section -> Figure
    "REFERENCES_TABLE",   # Section -> Table
    "ACHIEVES",           # Method -> Metric (with value)
    "COMPARES_TO",        # Method -> Method
    "EXTENDS",            # Method -> Method
    "BELONGS_TO",         # Author -> Paper (inverse convenience)
]

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
    # Uniqueness constraints
    "CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT author_id IF NOT EXISTS FOR (a:Author) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT section_id IF NOT EXISTS FOR (s:Section) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT figure_id IF NOT EXISTS FOR (f:Figure) REQUIRE f.id IS UNIQUE",
    "CREATE CONSTRAINT table_id IF NOT EXISTS FOR (t:Table) REQUIRE t.id IS UNIQUE",

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
