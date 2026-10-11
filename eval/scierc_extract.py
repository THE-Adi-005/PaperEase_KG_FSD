"""eval/scierc_extract.py — extract triples from SciERC test set documents and cache in SQLite.

Usage:
    python -m eval.scierc_extract --profile R7 --runs 5 --n 40
    python -m eval.scierc_extract --profile R3 --runs 3 --n 40
    python -m eval.scierc_extract --profile R10 --runs 3 --n 40
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.services.llm_client import llm_client
from eval.cache import has_run, put_run

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scierc_extract")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCIERC_TEST_PATH = PROJECT_ROOT / "backend" / "data" / "scierc" / "test.json"


def load_scierc_docs(path: Path, n: int = 40) -> list[dict]:
    """Load first n documents with at least 3 annotated entities."""
    if not path.exists():
        raise FileNotFoundError(f"SciERC test file not found at {path}")

    selected_docs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            # Count total annotated entities across all sentences
            ner_count = sum(len(s) for s in doc.get("ner", []))
            if ner_count >= 3:
                # Abstract text = join tokens of all sentences
                tokens = [tok for sent in doc.get("sentences", []) for tok in sent]
                abstract_text = " ".join(tokens)
                selected_docs.append({
                    "doc_key": doc["doc_key"],
                    "text": abstract_text,
                    "ner_count": ner_count,
                    "raw_doc": doc,
                })
                if len(selected_docs) >= n:
                    break
    return selected_docs


async def main():
    parser = argparse.ArgumentParser(description="Extract triples from SciERC test set into SQLite cache.")
    parser.add_argument("--profile", choices=["R3", "R5", "R7", "R10"], default="R7", help="Prompt profile")
    parser.add_argument("--runs", type=int, default=3, help="Number of extraction runs per document")
    parser.add_argument("--n", type=int, default=40, help="Number of SciERC documents to process")
    parser.add_argument("--temp", type=float, default=0.6, help="LLM temperature (default: 0.6)")
    parser.add_argument("--trunc", type=int, default=settings.SECTION_TEXT_LIMIT, help="Text limit per section")
    parser.add_argument("--model", type=str, default=settings.LLM_MODEL, help="LLM model name")
    parser.add_argument("--concurrency", type=int, default=2, help="Max concurrent LLM requests (default: 2)")

    args = parser.parse_args()

    logger.info("Loading SciERC test documents from %s...", SCIERC_TEST_PATH)
    docs = load_scierc_docs(SCIERC_TEST_PATH, n=args.n)
    logger.info("Loaded %d SciERC documents with >= 3 entities.", len(docs))

    if not docs:
        logger.warning("No qualifying SciERC documents found.")
        return

    semaphore = asyncio.Semaphore(args.concurrency)
    completed_calls = 0
    skipped_calls = 0
    failed_calls = 0

    async def process_doc_run(doc: dict, run_idx: int):
        nonlocal completed_calls, skipped_calls, failed_calls
        doc_key = doc["doc_key"]
        text = doc["text"]

        # Resumable: check if cached
        if has_run("scierc", doc_key, run_idx, args.profile, args.trunc, args.temp, args.model):
            skipped_calls += 1
            return

        async with semaphore:
            t0 = time.perf_counter()
            try:
                triples = await llm_client.extract_triples(
                    section_text=text,
                    section_id=doc_key,
                    paper_id="scierc",
                    temperature=args.temp,
                    profile=args.profile,
                    trunc=args.trunc,
                    raise_on_error=True,
                )
                put_run(
                    paper_id="scierc",
                    section_id=doc_key,
                    run_idx=run_idx,
                    prompt_profile=args.profile,
                    trunc=args.trunc,
                    temperature=args.temp,
                    model=args.model,
                    raw_triples=triples,
                )
                elapsed = time.perf_counter() - t0
                completed_calls += 1
                logger.info(
                    "Cached scierc doc %s run %d/%d (%d triples, %.2fs)",
                    doc_key, run_idx, args.runs, len(triples), elapsed
                )
            except Exception as e:
                failed_calls += 1
                logger.error("Failed extraction for scierc doc %s run %d: %s", doc_key, run_idx, e)

    tasks = []
    for d in docs:
        for r in range(1, args.runs + 1):
            tasks.append(process_doc_run(d, r))

    logger.info("Starting extraction for %d tasks (%d docs x %d runs)...", len(tasks), len(docs), args.runs)
    await asyncio.gather(*tasks)
    logger.info(
        "SciERC extraction complete. Completed: %d, Skipped (already cached): %d, Failed: %d",
        completed_calls, skipped_calls, failed_calls
    )


if __name__ == "__main__":
    asyncio.run(main())
