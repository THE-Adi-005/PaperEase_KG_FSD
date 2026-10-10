"""Paper management endpoints — upload, list, status, graph, figures."""

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from pathlib import Path
import uuid
import logging
import shutil

from app.config import settings
from app.models.schemas import (
    PaperInfo, PaperStatus, UploadResponse, SubGraph, FigureData, TableData,
)
from app.services.neo4j_client import neo4j_service

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory ingestion tracking (for progress before Neo4j has the paper)
_ingestion_status: dict[str, dict] = {}


@router.post("/upload", response_model=UploadResponse)
async def upload_paper(background_tasks: BackgroundTasks,
                       file: UploadFile = File(...)):
    """Upload a PDF and trigger background ingestion."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    paper_id = str(uuid.uuid4())[:8]
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = upload_dir / f"{paper_id}_{file.filename}"
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    logger.info(f"Uploaded: {file.filename} -> {file_path} (id={paper_id})")

    # Track status
    _ingestion_status[paper_id] = {
        "status": PaperStatus.PARSING,
        "filename": file.filename,
        "progress_pct": 0.0,
    }

    # Start background ingestion
    background_tasks.add_task(_ingest_paper, str(file_path), paper_id)

    return UploadResponse(
        paper_id=paper_id,
        filename=file.filename,
        status=PaperStatus.PARSING,
    )


@router.get("/papers", response_model=list[PaperInfo])
async def list_papers():
    """List all papers with their ingestion status."""
    papers = await neo4j_service.list_papers()

    # Add papers still being ingested (not yet in Neo4j)
    known_ids = {p.id for p in papers}
    for pid, info in _ingestion_status.items():
        if pid not in known_ids:
            papers.append(PaperInfo(
                id=pid,
                title=info.get("filename", pid),
                status=info["status"],
                progress_pct=info.get("progress_pct", 0.0),
            ))

    return papers


@router.get("/paper/{paper_id}", response_model=PaperInfo)
async def get_paper(paper_id: str):
    """Get paper details."""
    paper = await neo4j_service.get_paper_info(paper_id)
    if not paper:
        if paper_id in _ingestion_status:
            info = _ingestion_status[paper_id]
            return PaperInfo(
                id=paper_id,
                title=info.get("filename", paper_id),
                status=info["status"],
                progress_pct=info.get("progress_pct", 0.0),
            )
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.get("/paper/{paper_id}/status")
async def get_paper_status(paper_id: str):
    """Get ingestion progress."""
    paper = await neo4j_service.get_paper_info(paper_id)
    if paper:
        return {
            "paper_id": paper_id,
            "status": paper.status,
            "progress_pct": paper.progress_pct,
        }
    if paper_id in _ingestion_status:
        return {
            "paper_id": paper_id,
            "status": _ingestion_status[paper_id]["status"],
            "progress_pct": _ingestion_status[paper_id].get("progress_pct", 0.0),
        }
    raise HTTPException(status_code=404, detail="Paper not found")


@router.get("/paper/{paper_id}/graph", response_model=SubGraph)
async def get_paper_graph(paper_id: str):
    """Get the full knowledge graph for a paper."""
    return await neo4j_service.get_paper_graph(paper_id)


@router.get("/paper/{paper_id}/figures", response_model=list[FigureData])
async def get_paper_figures(paper_id: str):
    """Get all figures for a paper."""
    return await neo4j_service.get_paper_figures(paper_id)


@router.get("/paper/{paper_id}/tables", response_model=list[TableData])
async def get_paper_tables(paper_id: str):
    """Get all tables for a paper."""
    return await neo4j_service.get_paper_tables(paper_id)


@router.get("/paper/{paper_id}/triples")
async def get_paper_triples(paper_id: str):
    """Get all extracted triples (nodes and relationships) specifically sourced from a single paper."""
    async with neo4j_service.driver.session() as session:
        result = await session.run(
            """MATCH (h)-[r]->(t)
               WHERE r.source_paper_id = $paper_id
               RETURN coalesce(h.name, h.title, h.label, h.id) AS head, 
                      labels(h)[0] AS head_type, 
                      type(r) AS relation, 
                      coalesce(t.name, t.title, t.label, t.id) AS tail, 
                      labels(t)[0] AS tail_type,
                      r.source_section_id AS section_id
               ORDER BY CASE WHEN type(r) IN ['AUTHORED_BY', 'CONTAINS_SECTION', 'CONTAINS_FIGURE', 'CONTAINS_TABLE'] THEN 1 ELSE 0 END, head
               LIMIT 500""",
            paper_id=paper_id
        )
        
        triples = []
        async for record in result:
            rel_type = record["relation"]
            head_type = record["head_type"]
            tail_type = record["tail_type"]
            is_structural = (
                rel_type in ['AUTHORED_BY', 'CONTAINS_SECTION', 'CONTAINS_FIGURE', 'CONTAINS_TABLE', 'ILLUSTRATED_BY']
                or head_type in ['Paper', 'Section']
                or tail_type in ['Section', 'Author']
            )
            triples.append({
                "head": record["head"] or "Unknown Node",
                "head_type": head_type or "Unknown",
                "relation": rel_type,
                "tail": record["tail"] or "Unknown Node",
                "tail_type": tail_type or "Unknown",
                "section_id": record["section_id"],
                "category": "structural" if is_structural else "domain"
            })
        
        return {"paper_id": paper_id, "triples": triples}


# ── Background ingestion task ────────────────────────────────────────

async def _ingest_paper(file_path: str, paper_id: str):
    """Full ingestion pipeline: parse → extract KG → link entities."""
    try:
        # Phase 1: Parse PDF
        _ingestion_status[paper_id]["status"] = PaperStatus.PARSING
        from app.services.pdf_parser import parse_pdf
        parsed_paper = await parse_pdf(file_path, paper_id)

        # Save paper structure to Neo4j
        await neo4j_service.merge_paper(parsed_paper)
        logger.info(f"Paper structure saved: {parsed_paper.title}")

        # Phase 2: Build KG (LLM extraction)
        _ingestion_status[paper_id]["status"] = PaperStatus.EXTRACTING
        from app.services.kg_builder import build_kg
        async for progress in build_kg(parsed_paper):
            _ingestion_status[paper_id]["progress_pct"] = progress.get("progress_pct", 0.0)

        # Phase 3: Cross-paper entity linking
        _ingestion_status[paper_id]["status"] = PaperStatus.LINKING
        from app.services.embeddings import embedding_service
        link_count = await embedding_service.link_cross_paper_entities(paper_id)
        logger.info(f"Cross-paper linking: {link_count} SAME_AS edges")

        # Done
        await neo4j_service.update_paper_status(paper_id, PaperStatus.COMPLETE, 100.0)
        _ingestion_status[paper_id]["status"] = PaperStatus.COMPLETE
        _ingestion_status[paper_id]["progress_pct"] = 100.0
        logger.info(f"Ingestion complete: {parsed_paper.title}")

    except Exception as e:
        logger.error(f"Ingestion failed for {paper_id}: {e}", exc_info=True)
        _ingestion_status[paper_id]["status"] = PaperStatus.FAILED
        try:
            await neo4j_service.update_paper_status(paper_id, PaperStatus.FAILED)
        except Exception:
            pass
