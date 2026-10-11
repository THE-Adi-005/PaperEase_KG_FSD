"""CLI script for structural ingestion of PDFs without LLM extraction."""

import argparse
import asyncio
import hashlib
import json
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
backend_dir = PROJECT_ROOT / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.neo4j_client import neo4j_service
from app.services.pdf_parser import parse_pdf
from eval.corpus import CORPUS_JSON_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_structural")


async def ingest_structural(pdf_dir: Path, apply: bool = False) -> list[str]:
    """Parse PDFs and optionally merge structural graph into Neo4j."""
    if not pdf_dir.exists() or not pdf_dir.is_dir():
        print(f"Directory '{pdf_dir}' does not exist.")
        return []

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"Directory '{pdf_dir}' contains no PDF files.")
        return []

    await neo4j_service.connect()
    newly_ingested_ids = []

    print("=" * 80)
    print(f"STRUCTURAL INGESTION ({'APPLY MODE' if apply else 'DRY RUN'})")
    print(f"Source directory: {pdf_dir.resolve()}")
    print(f"PDFs found: {len(pdf_files)}")
    print("=" * 80)

    try:
        for pdf_path in pdf_files:
            # Deterministic paper id = first 8 chars of SHA-256
            file_bytes = pdf_path.read_bytes()
            sha256_hex = hashlib.sha256(file_bytes).hexdigest()
            paper_id = sha256_hex[:8]

            # Check if Paper already exists in Neo4j
            async with neo4j_service.driver.session() as session:
                res = await session.run("MATCH (p:Paper {id: $pid}) RETURN count(p) as c", pid=paper_id)
                exists = (await res.single())["c"] > 0

            if exists:
                print(f"Paper {paper_id} ({pdf_path.name}): Already exists in Neo4j. Skipping.")
                continue

            # Parse PDF structure
            parsed_paper = await parse_pdf(str(pdf_path), paper_id=paper_id)
            title = parsed_paper.title or pdf_path.stem
            secs = parsed_paper.sections
            sec_count = len(secs)
            sec_ge_50 = sum(1 for s in secs if s.text and len(s.text.strip()) >= 50)
            total_chars = sum(len(s.text or "") for s in secs)

            print(f"Paper ID:         {paper_id}")
            print(f"  File:           {pdf_path.name}")
            print(f"  Title:          {title}")
            print(f"  Sections total: {sec_count}")
            print(f"  Sections >=50c: {sec_ge_50}")
            print(f"  Total chars:    {total_chars}")

            if apply:
                await neo4j_service.merge_paper(parsed_paper)
                print(f"  Action:         Merged structural nodes into Neo4j (Paper, Author, Section)")
                newly_ingested_ids.append(paper_id)
            else:
                print(f"  Action:         Dry run (no Neo4j modifications)")
            print("-" * 80)

        # Update eval/corpus.json if applied
        if apply and newly_ingested_ids and CORPUS_JSON_PATH.exists():
            with open(CORPUS_JSON_PATH, "r", encoding="utf-8") as f:
                corpus_data = json.load(f)

            current_core = set(corpus_data.get("core", []))
            for pid in newly_ingested_ids:
                if pid not in current_core:
                    corpus_data.setdefault("core", []).append(pid)

            with open(CORPUS_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(corpus_data, f, indent=2)
            print(f"Updated {CORPUS_JSON_PATH}: added {newly_ingested_ids} to 'core'")

        return newly_ingested_ids

    finally:
        await neo4j_service.close()


def main():
    parser = argparse.ArgumentParser(description="Ingest PDF structural metadata into Neo4j without LLM calls.")
    parser.add_argument(
        "--pdf-dir",
        type=str,
        default="eval_papers",
        help="Directory containing PDF files (default: eval_papers)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to Neo4j (default is dry-run)",
    )

    args = parser.parse_args()
    pdf_dir = Path(args.pdf_dir)

    if not pdf_dir.exists():
        print(f"PDF directory '{pdf_dir}' does not exist.")
        sys.exit(1)

    pdf_files = list(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"PDF directory '{pdf_dir}' contains no PDF files.")
        sys.exit(1)

    asyncio.run(ingest_structural(pdf_dir=pdf_dir, apply=args.apply))


if __name__ == "__main__":
    main()
