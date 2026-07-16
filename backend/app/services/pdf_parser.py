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
from app.utils.tei_parser import parse_tei_xml
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

    # ── Step 1: GROBID TEI-XML ──
    tei_result = await _call_grobid(file_path)
    parsed = parse_tei_xml(tei_result, paper_id)

    # ── Step 2: Extract figure images with PyMuPDF ──
    figure_images = _extract_images(file_path, paper_id)

    # Match GROBID-detected figures with extracted images
    for fig in parsed["figures"]:
        # Try to match by page number or order
        if figure_images:
            img_data = figure_images.pop(0)
            fig.image_path = img_data["path"]
            fig.page_number = img_data["page"]

    # ── Step 3: Extract table structure with pdfplumber ──
    pdfplumber_tables = extract_tables_from_pdf(file_path, paper_id)

    # Merge pdfplumber data into GROBID-detected tables
    grobid_tables = parsed["tables"]
    # If pdfplumber found more tables, add them
    all_tables = grobid_tables.copy()
    for pt in pdfplumber_tables:
        # Check if already covered by GROBID
        matched = False
        for gt in grobid_tables:
            if gt.page_number and pt.page_number and gt.page_number == pt.page_number:
                # Merge pdfplumber structure into GROBID metadata
                gt.headers = pt.headers
                gt.rows = pt.rows
                matched = True
                break
        if not matched:
            all_tables.append(pt)

    # ── Build ParsedPaper ──
    paper = ParsedPaper(
        id=paper_id,
        title=parsed["title"] or path.stem,
        abstract=parsed["abstract"],
        authors=parsed["authors"],
        sections=parsed["sections"],
        figures=parsed["figures"],
        tables=all_tables,
        references=parsed["references"],
        raw_tei_xml=tei_result[:10000] if tei_result else None,  # Keep truncated for debug
    )

    logger.info(
        f"Parsed '{paper.title}': {len(paper.sections)} sections, "
        f"{len(paper.figures)} figures, {len(paper.tables)} tables, "
        f"{len(paper.authors)} authors"
    )

    return paper


async def _call_grobid(file_path: str) -> str:
    """Send PDF to GROBID and get TEI-XML response."""
    url = f"{settings.GROBID_URL}/api/processFulltextDocument"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            with open(file_path, "rb") as f:
                response = await client.post(
                    url,
                    files={"input": (Path(file_path).name, f, "application/pdf")},
                    data={
                        "consolidateHeader": "1",
                        "consolidateCitations": "0",
                        "includeRawCitations": "0",
                        "includeRawAffiliations": "0",
                        "teiCoordinates": "figure,ref",
                    },
                )
                if response.status_code == 200:
                    return response.text
                else:
                    logger.error(f"GROBID error {response.status_code}: {response.text[:500]}")
                    return ""
    except httpx.ConnectError:
        logger.error("Cannot connect to GROBID. Is it running?")
        return ""
    except Exception as e:
        logger.error(f"GROBID call failed: {e}")
        return ""


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
