"""eval/qa_merge.py — merge and validate QA question files.

Reads eval/qa_manual.json and (if it exists) eval/qa_drafts.json,
keeps only verified items with valid schema, checks paper_ids are in
corpus, deduplicates by id, writes eval/qa_set.json.

Usage:
    python -m eval.qa_merge
    python -m eval.qa_merge --out eval/qa_set.json
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_EVAL = _REPO_ROOT / "eval"
_VALID_TYPES = {"lookup", "multihop", "aggregation", "cross_paper", "unanswerable"}


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def _corpus_ids() -> set[str]:
    p = _EVAL / "corpus.json"
    if not p.exists():
        return set()
    with open(p, encoding="utf-8-sig") as f:
        c = json.load(f)
    ids: set[str] = set()
    for key in ("core", "ood"):
        ids.update(c.get(key, []))
    return ids


def validate_and_filter(items: list[dict], corpus_ids: set[str]) -> tuple[list[dict], list[str]]:
    """Return (valid_items, error_messages)."""
    valid = []
    errors = []
    for item in items:
        qid = item.get("id", "<no-id>")

        # Must be verified
        if not item.get("verified", False):
            errors.append(f"{qid}: skipped (verified=false)")
            continue

        # Non-empty question
        if not str(item.get("question", "")).strip():
            errors.append(f"{qid}: skipped (empty question)")
            continue

        # Gold answers check
        gold = item.get("gold_answers", [])
        answerable = item.get("answerable", True)
        if answerable and not gold:
            errors.append(f"{qid}: skipped (answerable=true but gold_answers empty)")
            continue

        # Schema check
        missing = [k for k in ("id", "type", "source", "paper_ids", "question", "gold_answers", "answerable")
                   if k not in item]
        if missing:
            errors.append(f"{qid}: skipped (missing keys: {missing})")
            continue

        # Type check
        if item["type"] not in _VALID_TYPES:
            errors.append(f"{qid}: skipped (invalid type '{item['type']}')")
            continue

        # Paper ids check
        bad = [pid for pid in item["paper_ids"] if pid not in corpus_ids]
        if bad:
            errors.append(f"{qid}: WARNING — paper_ids not in corpus: {bad} (kept anyway)")

        valid.append(item)

    return valid, errors


def merge(sources: list[list[dict]], corpus_ids: set[str]) -> tuple[list[dict], list[str]]:
    """Merge multiple source lists, deduplicate by id."""
    all_items = [item for src in sources for item in src]
    valid, errors = validate_and_filter(all_items, corpus_ids)

    # Deduplicate: last write wins (later sources override earlier)
    seen: dict[str, dict] = {}
    for item in valid:
        seen[item["id"]] = item
    deduped = list(seen.values())
    deduped.sort(key=lambda x: x["id"])
    return deduped, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(_EVAL / "qa_set.json"))
    args = parser.parse_args()

    corpus_ids = _corpus_ids()
    manual = _load(_EVAL / "qa_manual.json")
    drafts = _load(_EVAL / "qa_drafts.json")

    merged, errors = merge([manual, drafts], corpus_ids)

    for e in errors:
        print(f"  {e}", file=sys.stderr)

    by_type = Counter(q["type"] for q in merged)
    by_source = Counter(q["source"] for q in merged)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print(f"Written {len(merged)} questions to {out_path}")
    print(f"By type:   {dict(by_type)}")
    print(f"By source: {dict(by_source)}")
    return merged


if __name__ == "__main__":
    main()
