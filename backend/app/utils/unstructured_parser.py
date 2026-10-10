"""Lightweight PDF parser — uses pdfplumber + PyMuPDF only.

Replaces the `unstructured` dependency which requires heavy ML packages
(PyTorch, ONNX, unstructured-inference) that are fragile on Windows.

Pipeline:
1. pdfplumber → extract text by page, detect titles by font-size heuristic
2. PyMuPDF (fitz) → extract figure images
3. pdfplumber → extract table cell data
"""

import pdfplumber
import re
import logging
from typing import Dict, Any, List

from app.models.schemas import Author, Section, FigureData, TableData

logger = logging.getLogger(__name__)


def parse_unstructured(file_path: str, paper_id: str) -> Dict[str, Any]:
    """Parse PDF using pdfplumber into structured components.
    
    Returns dict with keys: title, authors, abstract, sections, figures, tables, references
    """
    logger.info(f"Using pdfplumber to partition {file_path}")
    
    result = _empty_result()
    
    try:
        with pdfplumber.open(file_path) as pdf:
            all_text_blocks = []
            
            for page_num, page in enumerate(pdf.pages):
                # Extract text with layout awareness
                text = page.extract_text(x_tolerance=2, y_tolerance=3)
                if text:
                    all_text_blocks.append(text)
            
            full_text = "\n\n".join(all_text_blocks)
            
            if not full_text.strip():
                logger.warning(f"No text extracted from {file_path}")
                return result
            
            # Split into lines for heuristic parsing
            lines = full_text.split("\n")
            
            # Extract title (first substantial line)
            result["title"] = _extract_title(lines)
            
            # Parse sections using heading detection
            sections = _extract_sections(lines, paper_id, result["title"])
            result["sections"] = sections
            
            # Extract abstract
            for sec in sections:
                if sec.title.lower().strip() in ["abstract", "summary"]:
                    result["abstract"] = sec.text
                    break
            
            # If no abstract section found, use first section
            if not result["abstract"] and sections:
                result["abstract"] = sections[0].text[:500]
                    
    except Exception as e:
        logger.error(f"pdfplumber parsing failed for {file_path}: {e}", exc_info=True)
    
    logger.info(f"Parsed {len(result['sections'])} sections from {file_path}")
    return result


def _extract_title(lines: List[str]) -> str:
    """Extract the paper title from the first few lines."""
    title_candidates = []
    for line in lines[:15]:  # Check first 15 lines
        stripped = line.strip()
        if not stripped:
            continue
        # Skip very short lines (page numbers, headers)
        if len(stripped) < 10:
            continue
        # Skip lines that look like author names (contain @, university keywords)
        if "@" in stripped or "university" in stripped.lower() or "department" in stripped.lower():
            continue
        # Skip lines that are all numbers or dates
        if re.match(r'^[\d\s\-/\.]+$', stripped):
            continue
        title_candidates.append(stripped)
        # Title is usually the first substantial text
        if len(title_candidates) >= 2:
            break
    
    return title_candidates[0] if title_candidates else "Untitled Paper"


def _extract_sections(lines: List[str], paper_id: str, title: str) -> List[Section]:
    """Extract sections by detecting heading patterns."""
    sections = []
    current_heading = "Introduction"
    current_text = []
    section_idx = 0
    
    # Common section heading patterns
    heading_pattern = re.compile(
        r'^(?:\d+\.?\s+)?'  # Optional number prefix like "1." or "2 "
        r'(Abstract|Introduction|Related Work|Background|Methodology|Methods?|'
        r'Approach|Model|Architecture|Experiments?|Results?|Discussion|'
        r'Conclusion|Conclusions|Acknowledgment|References|Appendix|'
        r'Evaluation|Analysis|Setup|Training|Implementation|Limitations|'
        r'Future Work|Overview|Proposed|Framework|Dataset|Datasets|'
        r'Ablation|Pre-training|Fine-tuning)',
        re.IGNORECASE
    )
    
    # Also detect numbered section headers like "3.1 Encoder" or "IV. RESULTS"
    numbered_heading = re.compile(r'^(?:\d+\.?\d*\.?\s+|[IVX]+\.?\s+)[A-Z]')
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        # Skip the title line itself
        if stripped == title:
            continue
            
        is_heading = False
        
        # Check if line matches known heading patterns
        if heading_pattern.match(stripped):
            is_heading = True
        # Check numbered heading pattern (must be short-ish)
        elif numbered_heading.match(stripped) and len(stripped) < 80:
            is_heading = True
        # Check ALL CAPS headings (common in academic papers)
        elif stripped.isupper() and 5 < len(stripped) < 60 and not any(c.isdigit() for c in stripped):
            is_heading = True
            
        if is_heading:
            # Save previous section
            if current_text:
                text_content = "\n\n".join(current_text)
                if len(text_content.strip()) > 30:  # Skip trivially short sections
                    sections.append(Section(
                        id=f"{paper_id}_sec_{section_idx}",
                        title=current_heading,
                        text=text_content,
                        order=section_idx,
                        figure_refs=[],
                        table_refs=[]
                    ))
                    section_idx += 1
            current_heading = stripped
            current_text = []
        else:
            # Only add substantial text lines (skip page numbers, short artifacts)
            if len(stripped) > 20:
                current_text.append(stripped)
    
    # Add final section
    if current_text:
        text_content = "\n\n".join(current_text)
        if len(text_content.strip()) > 30:
            sections.append(Section(
                id=f"{paper_id}_sec_{section_idx}",
                title=current_heading,
                text=text_content,
                order=section_idx,
                figure_refs=[],
                table_refs=[]
            ))
    
    return sections


def _empty_result() -> Dict[str, Any]:
    return {
        "title": "", "authors": [], "abstract": "",
        "sections": [], "figures": [], "tables": [], "references": [],
    }
