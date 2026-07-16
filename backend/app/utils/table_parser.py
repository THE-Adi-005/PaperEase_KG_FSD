"""Table parser — extracts structured table data from PDFs using pdfplumber.

Converts tables into (row_entity, column_header, cell_value) triples,
making questions like "which method scored highest on X" answerable
via graph traversal instead of text search.
"""

import pdfplumber
import logging
from pathlib import Path

from app.models.schemas import TableData, Triple

logger = logging.getLogger(__name__)


def extract_tables_from_pdf(pdf_path: str, paper_id: str) -> list[TableData]:
    """Extract all tables from a PDF using pdfplumber.
    
    Returns TableData objects with actual row/column structure.
    """
    tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            table_idx = 0
            for page_num, page in enumerate(pdf.pages):
                page_tables = page.extract_tables()
                if not page_tables:
                    continue

                for raw_table in page_tables:
                    if not raw_table or len(raw_table) < 2:
                        continue  # Need at least header + 1 row

                    # Clean the table
                    cleaned = _clean_table(raw_table)
                    if not cleaned or len(cleaned) < 2:
                        continue

                    headers = cleaned[0]
                    rows = cleaned[1:]

                    table_id = f"{paper_id}_pdfplumber_tbl_{table_idx}"
                    tables.append(TableData(
                        id=table_id,
                        label=f"Table {table_idx + 1}",
                        caption="",  # pdfplumber doesn't extract captions
                        headers=headers,
                        rows=rows,
                        page_number=page_num + 1,
                    ))
                    table_idx += 1

    except Exception as e:
        logger.warning(f"pdfplumber table extraction failed for {pdf_path}: {e}")

    return tables


def table_to_triples(table: TableData, paper_id: str,
                      section_id: str = "") -> list[Triple]:
    """Convert a structured table into KG triples.
    
    For a results table like:
        | Method | Dataset | F1   | Accuracy |
        | BERT   | SQuAD   | 92.4 | 88.1     |
    
    Produces triples:
        (BERT, F1, 92.4)
        (BERT, Accuracy, 88.1)
        (BERT, EVALUATED_ON, SQuAD)
    """
    triples = []
    if not table.headers or not table.rows:
        return triples

    headers = table.headers

    # Identify column roles
    entity_col = 0  # First column is usually the row entity (method name, etc.)
    metric_cols = []
    dataset_cols = []

    for i, h in enumerate(headers):
        h_lower = h.lower().strip()
        if i == 0:
            continue
        # Check if this is a metric column (contains numbers in rows)
        is_numeric = any(
            _is_numeric(row[i]) for row in table.rows if i < len(row)
        )
        if is_numeric:
            metric_cols.append(i)
        elif h_lower in ("dataset", "benchmark", "data", "corpus"):
            dataset_cols.append(i)

    for row in table.rows:
        if not row or not row[0] or not row[0].strip():
            continue

        row_entity = row[0].strip()
        if not row_entity or row_entity == "-":
            continue

        # Metric triples
        for col_idx in metric_cols:
            if col_idx < len(row) and row[col_idx] and row[col_idx].strip():
                value = row[col_idx].strip()
                if value and value != "-" and value != "N/A":
                    header_name = headers[col_idx].strip()
                    triples.append(Triple(
                        head=row_entity,
                        head_type="Method",
                        relation="REPORTS_METRIC",
                        tail=f"{header_name}={value}",
                        tail_type="Metric",
                        source_paper_id=paper_id,
                        source_section_id=section_id,
                    ))

        # Dataset triples
        for col_idx in dataset_cols:
            if col_idx < len(row) and row[col_idx] and row[col_idx].strip():
                dataset_name = row[col_idx].strip()
                if dataset_name and dataset_name != "-":
                    triples.append(Triple(
                        head=row_entity,
                        head_type="Method",
                        relation="EVALUATED_ON",
                        tail=dataset_name,
                        tail_type="Dataset",
                        source_paper_id=paper_id,
                        source_section_id=section_id,
                    ))

    return triples


def _clean_table(raw_table: list[list]) -> list[list[str]]:
    """Clean raw pdfplumber table: handle None cells, merge rows, etc."""
    cleaned = []
    for row in raw_table:
        if row is None:
            continue
        cleaned_row = []
        for cell in row:
            if cell is None:
                cleaned_row.append("")
            else:
                # Clean whitespace and newlines
                cleaned_row.append(str(cell).replace("\n", " ").strip())
        # Skip empty rows
        if any(c.strip() for c in cleaned_row):
            cleaned.append(cleaned_row)
    return cleaned


def _is_numeric(value: str) -> bool:
    """Check if a string represents a number (including percentages)."""
    if not value:
        return False
    # Remove common formatting
    cleaned = value.strip().rstrip("%").replace(",", "").replace("±", "").split("±")[0].strip()
    try:
        float(cleaned)
        return True
    except (ValueError, TypeError):
        return False
