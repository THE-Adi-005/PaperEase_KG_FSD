"""Script to extract table triples from stored PDF files and populate sqlite cache."""

import argparse
import logging
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.utils.table_parser import extract_tables_from_pdf, table_to_triples
from eval.cache import put_table_triples

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cache_tables")


def find_pdf_files(uploads_dir: Path, target_papers: list[str] | None = None) -> list[tuple[str, Path]]:
    """Find all (paper_id, file_path) pairs in the upload directory."""
    pdf_files = []
    if not uploads_dir.exists():
        logger.warning("Uploads directory %s does not exist.", uploads_dir)
        return pdf_files

    for f in uploads_dir.glob("*.pdf"):
        if "_" in f.stem:
            paper_id = f.stem.split("_", 1)[0]
        else:
            paper_id = f.stem

        if target_papers and paper_id not in target_papers:
            continue
        pdf_files.append((paper_id, f))

    return pdf_files


def main():
    parser = argparse.ArgumentParser(description="Extract table triples from stored PDFs into sqlite cache.")
    parser.add_argument(
        "--uploads-dir",
        type=str,
        default=str(backend_dir / "uploads"),
        help="Path to uploaded PDF files directory",
    )
    parser.add_argument(
        "--papers",
        type=str,
        default=None,
        help="Comma-separated paper IDs to process (default: all found in uploads)",
    )

    args = parser.parse_args()
    target_papers = [p.strip() for p in args.papers.split(",") if p.strip()] if args.papers else None

    uploads_path = Path(args.uploads_dir)
    pdf_files = find_pdf_files(uploads_path, target_papers)

    logger.info("Found %d PDF file(s) in %s.", len(pdf_files), uploads_path)
    if not pdf_files:
        logger.info("No matching PDF files to process.")
        return

    total_tables = 0
    total_triples = 0

    for paper_id, pdf_path in pdf_files:
        logger.info("Processing tables for paper %s from %s...", paper_id, pdf_path.name)
        tables = extract_tables_from_pdf(str(pdf_path), paper_id)
        paper_triples = []

        for tbl in tables:
            triples = table_to_triples(tbl, paper_id, tbl.section_id or "")
            for t in triples:
                paper_triples.append({
                    "paper_id": t.source_paper_id,
                    "section_id": t.source_section_id or "",
                    "head": t.head,
                    "relation": t.relation,
                    "tail": t.tail,
                })

        count = put_table_triples(paper_triples)
        total_tables += len(tables)
        total_triples += count
        logger.info("  Paper %s: %d tables, %d triples cached.", paper_id, len(tables), count)

    print("\n" + "=" * 65)
    print("TABLE TRIPLES CACHE SUMMARY")
    print("=" * 65)
    print(f"PDFs processed:       {len(pdf_files)}")
    print(f"Tables extracted:     {total_tables}")
    print(f"Triples cached:       {total_triples}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
