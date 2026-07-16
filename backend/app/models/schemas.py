"""Pydantic models for the entire application."""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────

class PaperStatus(str, Enum):
    UPLOADING = "uploading"
    PARSING = "parsing"
    EXTRACTING = "extracting"
    LINKING = "linking"
    COMPLETE = "complete"
    FAILED = "failed"


class QueryMode(str, Enum):
    SINGLE = "single"
    COMPARE = "compare"


# ── PDF Parsing Models ───────────────────────────────────────────────

class Author(BaseModel):
    name: str
    affiliation: Optional[str] = None
    email: Optional[str] = None


class FigureData(BaseModel):
    id: str
    label: str  # e.g. "Figure 1"
    caption: str
    image_path: Optional[str] = None
    section_id: Optional[str] = None
    page_number: Optional[int] = None


class TableCell(BaseModel):
    row: int
    col: int
    text: str
    is_header: bool = False


class TableData(BaseModel):
    id: str
    label: str  # e.g. "Table 1"
    caption: str
    headers: list[str] = []
    rows: list[list[str]] = []
    section_id: Optional[str] = None
    page_number: Optional[int] = None


class Section(BaseModel):
    id: str
    title: str
    text: str
    order: int
    figure_refs: list[str] = []  # figure ids referenced in text
    table_refs: list[str] = []   # table ids referenced in text
    parent_section: Optional[str] = None


class ParsedPaper(BaseModel):
    id: str
    title: str
    abstract: str = ""
    authors: list[Author] = []
    sections: list[Section] = []
    figures: list[FigureData] = []
    tables: list[TableData] = []
    references: list[str] = []  # citation strings
    raw_tei_xml: Optional[str] = None


# ── Knowledge Graph Models ───────────────────────────────────────────

class Triple(BaseModel):
    head: str
    head_type: str = "Concept"
    relation: str
    tail: str
    tail_type: str = "Concept"
    source_paper_id: str = ""
    source_section_id: str = ""
    confidence: float = 1.0


class ExtractionResult(BaseModel):
    triples: list[Triple]
    section_id: str
    extraction_run: int = 1


# ── Graph Visualization Models ───────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # node label (Method, Concept, etc.)
    properties: dict = {}


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str  # relation type
    properties: dict = {}


class SubGraph(BaseModel):
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []


# ── Agent / Reasoning Models ─────────────────────────────────────────

class ReasoningStep(BaseModel):
    step_number: int
    thought: str = ""
    action: str = ""
    action_input: str = ""
    observation: str = ""
    node_ids_touched: list[str] = []
    lazy_completion_triggered: bool = False


class QueryRequest(BaseModel):
    question: str
    paper_ids: list[str] = []
    mode: QueryMode = QueryMode.SINGLE


class QueryResponse(BaseModel):
    answer: str
    reasoning_steps: list[ReasoningStep] = []
    subgraph: SubGraph = SubGraph()
    figures_referenced: list[FigureData] = []
    tables_referenced: list[TableData] = []
    lazy_completion_count: int = 0
    total_steps: int = 0


# ── API Response Models ──────────────────────────────────────────────

class PaperInfo(BaseModel):
    id: str
    title: str
    status: PaperStatus
    authors: list[str] = []
    section_count: int = 0
    node_count: int = 0
    edge_count: int = 0
    progress_pct: float = 0.0


class HealthStatus(BaseModel):
    status: str = "ok"
    neo4j: bool = False
    ollama: bool = False
    grobid: bool = False
    ollama_model: str = ""


class UploadResponse(BaseModel):
    paper_id: str
    filename: str
    status: PaperStatus


class SSEEvent(BaseModel):
    """Server-Sent Event data structure."""
    event: str  # thought, action, observation, answer, subgraph, error
    data: dict = {}
