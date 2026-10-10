"""PDF parser service — orchestrates GROBID, PyMuPDF, and pdfplumber.

Pipeline:
1. GROBID /api/processFulltextDocument → TEI-XML
2. Parse TEI-XML → structured sections, authors, figures, tables
3. PyMuPDF → extract figure images
4. pdfplumber → extract table cell data
5. Merge results into ParsedPaper
"""

import httpx
import fitz  # PyMuPDF
import logging
import uuid
from pathlib import Path

from app.config import settings
from app.models.schemas import ParsedPaper, Author, Section, FigureData, TableData
from app.utils.unstructured_parser import parse_unstructured
from app.utils.table_parser import extract_tables_from_pdf

logger = logging.getLogger(__name__)


async def parse_pdf(file_path: str, paper_id: str | None = None) -> ParsedPaper:
    """Full PDF parsing pipeline.
    
    Args:
        file_path: Path to the PDF file
        paper_id: Optional paper ID (generated if not provided)
    
    Returns:
        ParsedPaper with all extracted structure
    """
    if paper_id is None:
        paper_id = str(uuid.uuid4())[:8]

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    logger.info(f"Parsing PDF: {path.name} (id={paper_id})")

    # ── Step 1: Unstructured Parsing ──
    parsed = parse_unstructured(file_path, paper_id)

    # ── Step 2: Extract figure images with PyMuPDF ──
    figure_images = _extract_images(file_path, paper_id)
    extracted_figures = []
    for idx, img in enumerate(figure_images):
        extracted_figures.append(FigureData(
            id=f"{paper_id}_fig_{idx+1}",
            label=f"Figure {idx+1}",
            caption=f"Visual asset extracted from Page {img.get('page', 1)}",
            image_path=img.get("path", ""),
            page_number=img.get("page", 1),
        ))
    all_figures = parsed["figures"] + extracted_figures

    # ── Step 3: Extract table structure with pdfplumber ──
    pdfplumber_tables = extract_tables_from_pdf(file_path, paper_id)
    all_tables = parsed["tables"] + pdfplumber_tables

    # ── Build ParsedPaper ──
    paper = ParsedPaper(
        id=paper_id,
        title=parsed["title"] or path.stem,
        abstract=parsed["abstract"],
        authors=parsed["authors"],
        sections=parsed["sections"],
        figures=all_figures,
        tables=all_tables,
        references=parsed["references"],
        raw_tei_xml=None,
    )

    logger.info(
        f"Parsed '{paper.title}': {len(paper.sections)} sections, "
        f"{len(paper.figures)} figures, {len(paper.tables)} tables, "
        f"{len(paper.authors)} authors"
    )

    return paper


def _extract_images(pdf_path: str, paper_id: str) -> list[dict]:
    """Extract images from PDF using PyMuPDF."""
    images = []
    figures_dir = Path(settings.FIGURES_DIR) / paper_id
    figures_dir.mkdir(parents=True, exist_ok=True)

    try:
        doc = fitz.open(pdf_path)
        img_idx = 0

        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)

            for img_info in image_list:
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    if base_image:
                        ext = base_image.get("ext", "png")
                        img_bytes = base_image["image"]

                        # Skip very small images (likely icons/artifacts)
                        if len(img_bytes) < 5000:
                            continue

                        img_filename = f"fig_{img_idx}.{ext}"
                        img_path = figures_dir / img_filename
                        img_path.write_bytes(img_bytes)

                        images.append({
                            "path": f"/figures/{paper_id}/{img_filename}",
                            "page": page_num + 1,
                        })
                        img_idx += 1
                except Exception as e:
                    logger.debug(f"Failed to extract image xref={xref}: {e}")

        doc.close()
        logger.info(f"Extracted {len(images)} images from PDF")
    except Exception as e:
        logger.warning(f"PyMuPDF image extraction failed: {e}")

    return images
