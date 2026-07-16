"""TEI-XML parser — converts GROBID output to structured sections.

GROBID produces TEI-XML from PDFs. This module extracts:
- Title, authors, abstract from <teiHeader>
- Ordered sections from <body><div>
- Figures and tables from <figure>
- Citation references from <listBibl>
- Cross-references (figure/table refs) from <ref>
"""

from lxml import etree
from typing import Optional
import re
import logging

from app.models.schemas import Author, Section, FigureData, TableData

logger = logging.getLogger(__name__)

# TEI namespace
NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def parse_tei_xml(xml_content: str, paper_id: str) -> dict:
    """Parse TEI-XML string into structured components.
    
    Returns dict with keys: title, authors, abstract, sections, figures, tables, references
    """
    try:
        root = etree.fromstring(xml_content.encode("utf-8"))
    except etree.XMLSyntaxError as e:
        logger.error(f"Failed to parse TEI-XML: {e}")
        return _empty_result()

    result = {
        "title": _extract_title(root),
        "authors": _extract_authors(root),
        "abstract": _extract_abstract(root),
        "sections": _extract_sections(root, paper_id),
        "figures": _extract_figures(root, paper_id),
        "tables": _extract_tables(root, paper_id),
        "references": _extract_references(root),
    }

    # Link figures/tables to nearest sections
    _link_figures_to_sections(result["sections"], result["figures"], result["tables"])

    return result


def _empty_result() -> dict:
    return {
        "title": "", "authors": [], "abstract": "",
        "sections": [], "figures": [], "tables": [], "references": [],
    }


def _extract_title(root) -> str:
    """Extract paper title from teiHeader."""
    title_elem = root.find(".//tei:teiHeader//tei:titleStmt//tei:title", NS)
    if title_elem is not None:
        return _get_text(title_elem).strip()
    return ""


def _extract_authors(root) -> list[Author]:
    """Extract authors from teiHeader."""
    authors = []
    for author_elem in root.findall(
        ".//tei:teiHeader//tei:sourceDesc//tei:biblStruct//tei:analytic//tei:author", NS
    ):
        persname = author_elem.find("tei:persName", NS)
        if persname is None:
            continue

        forename = persname.find("tei:forename", NS)
        surname = persname.find("tei:surname", NS)
        name_parts = []
        if forename is not None and forename.text:
            name_parts.append(forename.text)
        if surname is not None and surname.text:
            name_parts.append(surname.text)

        if not name_parts:
            continue

        # Affiliation
        affiliation = ""
        aff_elem = author_elem.find("tei:affiliation", NS)
        if aff_elem is not None:
            org = aff_elem.find("tei:orgName", NS)
            affiliation = org.text if org is not None and org.text else ""

        # Email
        email = ""
        email_elem = author_elem.find("tei:email", NS)
        if email_elem is not None and email_elem.text:
            email = email_elem.text

        authors.append(Author(
            name=" ".join(name_parts),
            affiliation=affiliation,
            email=email,
        ))

    return authors


def _extract_abstract(root) -> str:
    """Extract abstract text."""
    abstract_elem = root.find(".//tei:teiHeader//tei:profileDesc//tei:abstract", NS)
    if abstract_elem is not None:
        return _get_text(abstract_elem).strip()
    return ""


def _extract_sections(root, paper_id: str) -> list[Section]:
    """Extract body sections in order."""
    sections = []
    body = root.find(".//tei:body", NS)
    if body is None:
        return sections

    for idx, div in enumerate(body.findall("tei:div", NS)):
        # Section title
        head = div.find("tei:head", NS)
        title = head.text if head is not None and head.text else f"Section {idx + 1}"

        # Get section number if present
        if head is not None:
            n = head.get("n", "")
            if n:
                title = f"{n} {title}"

        # Section text (all paragraphs)
        paragraphs = []
        for p in div.findall("tei:p", NS):
            p_text = _get_text(p).strip()
            if p_text:
                paragraphs.append(p_text)

        text = "\n\n".join(paragraphs)
        if not text:
            continue

        section_id = f"{paper_id}_sec_{idx}"

        # Find figure/table references in text
        figure_refs = []
        table_refs = []
        for ref in div.findall(".//tei:ref", NS):
            ref_type = ref.get("type", "")
            target = ref.get("target", "")
            if ref_type == "figure" and target:
                fig_id = target.lstrip("#")
                figure_refs.append(f"{paper_id}_{fig_id}")
            elif ref_type == "table" and target:
                tbl_id = target.lstrip("#")
                table_refs.append(f"{paper_id}_{tbl_id}")

        sections.append(Section(
            id=section_id,
            title=title,
            text=text,
            order=idx,
            figure_refs=figure_refs,
            table_refs=table_refs,
        ))

    return sections


def _extract_figures(root, paper_id: str) -> list[FigureData]:
    """Extract figure metadata from TEI."""
    figures = []
    for fig in root.findall(".//tei:figure", NS):
        fig_type = fig.get("type", "")
        if fig_type == "table":
            continue  # Tables handled separately

        xml_id = fig.get("{http://www.w3.org/XML/1998/namespace}id", "")
        fig_id = f"{paper_id}_{xml_id}" if xml_id else f"{paper_id}_fig_{len(figures)}"

        # Label (e.g., "Figure 1")
        head = fig.find("tei:head", NS)
        label_elem = fig.find("tei:label", NS)
        label = ""
        if label_elem is not None and label_elem.text:
            label = f"Figure {label_elem.text}"
        elif head is not None and head.text:
            label = head.text

        # Caption
        figdesc = fig.find("tei:figDesc", NS)
        caption = _get_text(figdesc).strip() if figdesc is not None else ""

        if label or caption:
            figures.append(FigureData(
                id=fig_id,
                label=label or f"Figure {len(figures) + 1}",
                caption=caption,
            ))

    return figures


def _extract_tables(root, paper_id: str) -> list[TableData]:
    """Extract table metadata from TEI (structure comes from pdfplumber separately)."""
    tables = []
    for fig in root.findall(".//tei:figure[@type='table']", NS):
        xml_id = fig.get("{http://www.w3.org/XML/1998/namespace}id", "")
        tbl_id = f"{paper_id}_{xml_id}" if xml_id else f"{paper_id}_tbl_{len(tables)}"

        head = fig.find("tei:head", NS)
        label_elem = fig.find("tei:label", NS)
        label = ""
        if label_elem is not None and label_elem.text:
            label = f"Table {label_elem.text}"
        elif head is not None and head.text:
            label = head.text

        figdesc = fig.find("tei:figDesc", NS)
        caption = _get_text(figdesc).strip() if figdesc is not None else ""

        if label or caption:
            tables.append(TableData(
                id=tbl_id,
                label=label or f"Table {len(tables) + 1}",
                caption=caption,
            ))

    return tables


def _extract_references(root) -> list[str]:
    """Extract bibliography references."""
    refs = []
    for bibl in root.findall(".//tei:listBibl//tei:biblStruct", NS):
        # Try to build a citation string
        parts = []
        # Authors
        for author in bibl.findall(".//tei:author//tei:persName", NS):
            surname = author.find("tei:surname", NS)
            if surname is not None and surname.text:
                parts.append(surname.text)

        # Title
        title = bibl.find(".//tei:title", NS)
        if title is not None and title.text:
            parts.append(f'"{title.text}"')

        # Year
        date = bibl.find(".//tei:date", NS)
        if date is not None:
            year = date.get("when", date.text or "")
            if year:
                parts.append(f"({year[:4]})")

        if parts:
            refs.append(", ".join(parts))

    return refs


def _link_figures_to_sections(sections: list[Section],
                               figures: list[FigureData],
                               tables: list[TableData]) -> None:
    """Link figures/tables to sections based on ref markers and order."""
    # Build a mapping of figure/table IDs to objects
    fig_map = {f.id: f for f in figures}
    tbl_map = {t.id: t for t in tables}

    for section in sections:
        # Link figures referenced in this section
        for fref in section.figure_refs:
            if fref in fig_map:
                fig_map[fref].section_id = section.id

        # Link tables referenced in this section
        for tref in section.table_refs:
            if tref in tbl_map:
                tbl_map[tref].section_id = section.id


def _get_text(elem) -> str:
    """Recursively get all text content from an element."""
    if elem is None:
        return ""
    return "".join(elem.itertext())
