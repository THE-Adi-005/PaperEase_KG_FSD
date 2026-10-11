"""Corpus definition helper functions."""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_JSON_PATH = REPO_ROOT / "eval" / "corpus.json"


def get_corpus() -> dict:
    """Load and return corpus metadata from corpus.json."""
    if not CORPUS_JSON_PATH.exists():
        raise FileNotFoundError(f"Corpus file not found: {CORPUS_JSON_PATH}")
    with open(CORPUS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_core_papers() -> list[str]:
    """Return core evaluation paper IDs."""
    return list(get_corpus().get("core", []))


def get_ood_papers() -> list[str]:
    """Return out-of-domain evaluation paper IDs."""
    return list(get_corpus().get("ood", []))


def get_eval_papers() -> list[str]:
    """Return all evaluation papers (core + ood)."""
    return get_core_papers() + get_ood_papers()
