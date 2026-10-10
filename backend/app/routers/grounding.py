"""Grounding statements API — exposes research-backed design justifications."""

from fastapi import APIRouter, Query
from typing import Optional

from app.models.grounding_statements import (
    get_all_statements,
    get_statements_by_category,
    BIBTEX_REFERENCES,
)

router = APIRouter()


@router.get("/statements")
async def list_grounding_statements(
    category: Optional[str] = Query(
        None,
        description="Filter by category: domain, node_type, relationship_type, hyperparameter, architecture",
    ),
):
    """Return all research-grounded design justifications.

    Each statement includes:
    - The design choice made
    - Why it was made (justification)
    - Academic citations backing the choice
    - Alternatives that were considered and rejected
    - Tradeoffs acknowledged
    """
    if category:
        statements = get_statements_by_category(category)
    else:
        statements = get_all_statements()

    return {
        "count": len(statements),
        "statements": statements,
        "categories": ["domain", "node_type", "relationship_type", "hyperparameter", "architecture"],
    }


@router.get("/bibtex")
async def get_bibtex():
    """Return BibTeX references for all cited papers."""
    return {"bibtex": BIBTEX_REFERENCES}


@router.get("/summary")
async def grounding_summary():
    """High-level summary of all grounding evidence."""
    all_stmts = get_all_statements()

    # Count citations across all statements
    all_citations = []
    for s in all_stmts:
        all_citations.extend(s.get("citations", []))
    unique_papers = set()
    for c in all_citations:
        # Extract paper identifier (first author + year)
        parts = c.split("—")[0].strip() if "—" in c else c[:40]
        unique_papers.add(parts)

    by_category = {}
    for s in all_stmts:
        cat = s["category"]
        if cat not in by_category:
            by_category[cat] = 0
        by_category[cat] += 1

    return {
        "total_grounding_statements": len(all_stmts),
        "total_unique_papers_cited": len(unique_papers),
        "total_citation_references": len(all_citations),
        "statements_by_category": by_category,
        "categories": list(by_category.keys()),
    }
