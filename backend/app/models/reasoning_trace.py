"""Pydantic models for the traceable multi-hop reasoning chain.

Every claim in the final answer maps back to specific graph nodes and edges,
making the entire reasoning process transparent and verifiable.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ── Sub-question planning ────────────────────────────────────────────

class RetrievalStrategy(str, Enum):
    ENTITY_SEARCH = "entity_search"
    NEIGHBOR_TRAVERSAL = "neighbor_traversal"
    SECTION_INSPECT = "section_inspect"
    METRIC_LOOKUP = "metric_lookup"
    CROSS_PAPER_LINK = "cross_paper_link"


class EvidenceType(str, Enum):
    METRIC = "metric"
    METHOD_COMPARISON = "method_comparison"
    CONCEPTUAL = "conceptual"
    FACTUAL = "factual"
    STRUCTURAL = "structural"


class SubQuestion(BaseModel):
    """A decomposed sub-question from the Planner agent."""
    id: str
    text: str
    retrieval_strategy: RetrievalStrategy = RetrievalStrategy.ENTITY_SEARCH
    expected_evidence_type: EvidenceType = EvidenceType.FACTUAL
    priority: int = 1  # 1 = highest priority
    depends_on: list[str] = Field(default_factory=list)  # IDs of prerequisite sub-questions


# ── Evidence from KG traversal ───────────────────────────────────────

class Evidence(BaseModel):
    """A single piece of evidence retrieved from the Knowledge Graph."""
    source_node: str          # Node name (e.g., "BERT")
    source_node_type: str = ""  # Node label (e.g., "Method")
    source_edge: Optional[str] = None  # Edge type (e.g., "ACHIEVES")
    target_node: Optional[str] = None  # Connected node (e.g., "F1=92.4")
    target_node_type: str = ""
    text: str                 # Human-readable evidence text
    source_paper_id: str = ""
    source_paper_title: str = ""
    source_section_id: str = ""
    confidence: float = 1.0   # Extraction confidence
    graph_path: list[str] = Field(default_factory=list)  # Full traversal path


class EvidenceBundle(BaseModel):
    """Evidence collected for a sub-question."""
    sub_question_id: str
    sub_question_text: str
    evidence: list[Evidence] = Field(default_factory=list)
    retrieval_steps: int = 0  # How many KG queries were needed
    is_satisfied: bool = False  # Whether enough evidence was found


# ── Grounded reasoning steps ─────────────────────────────────────────

class GroundedStep(BaseModel):
    """A single reasoning step with explicit evidence linkage."""
    step_number: int
    claim: str                           # "BERT achieves F1=92.4 on SQuAD"
    supporting_evidence: list[Evidence] = Field(default_factory=list)
    graph_path: list[str] = Field(default_factory=list)  # ["BERT", "ACHIEVES", "F1=92.4"]
    is_verified: bool = False
    verification_note: str = ""


class ReasonedAnswer(BaseModel):
    """The Reasoner agent's output — answer with explicit reasoning chain."""
    text: str
    reasoning_steps: list[GroundedStep] = Field(default_factory=list)
    sub_questions_answered: list[str] = Field(default_factory=list)  # Sub-question IDs


# ── Verification report ──────────────────────────────────────────────

class VerificationResult(str, Enum):
    VERIFIED = "verified"       # Claim supported by graph evidence
    UNSUPPORTED = "unsupported" # No graph evidence found
    CONTRADICTED = "contradicted"  # Graph evidence contradicts claim
    PARTIAL = "partial"         # Partially supported


class ClaimVerification(BaseModel):
    """Verification result for a single claim."""
    claim: str
    result: VerificationResult
    supporting_evidence: list[str] = Field(default_factory=list)  # Evidence IDs
    contradicting_evidence: list[str] = Field(default_factory=list)
    note: str = ""


class VerificationReport(BaseModel):
    """The Verifier agent's output — fact-checking results."""
    verified_claims: list[ClaimVerification] = Field(default_factory=list)
    confidence_score: float = 0.0   # 0.0 - 1.0 overall confidence
    provenance_check_passed: bool = False
    revision_suggested: bool = False
    revision_reason: str = ""
    total_claims: int = 0
    verified_count: int = 0
    unsupported_count: int = 0
    contradicted_count: int = 0


# ── Multi-agent pipeline trace ───────────────────────────────────────

class AgentStage(str, Enum):
    PLANNER = "planner"
    RETRIEVER = "retriever"
    REASONER = "reasoner"
    VERIFIER = "verifier"


class PipelineStageResult(BaseModel):
    """Result from a single stage of the multi-agent pipeline."""
    stage: AgentStage
    duration_ms: int = 0
    input_summary: str = ""
    output_summary: str = ""
    llm_calls: int = 0
    kg_queries: int = 0


class MultiAgentTrace(BaseModel):
    """Full trace of the multi-agent pipeline execution."""
    question: str
    paper_ids: list[str] = Field(default_factory=list)

    # Planning stage
    sub_questions: list[SubQuestion] = Field(default_factory=list)

    # Retrieval stage
    evidence_bundles: list[EvidenceBundle] = Field(default_factory=list)
    total_kg_queries: int = 0

    # Reasoning stage
    reasoned_answer: Optional[ReasonedAnswer] = None

    # Verification stage
    verification_report: Optional[VerificationReport] = None

    # Pipeline metadata
    stage_results: list[PipelineStageResult] = Field(default_factory=list)
    total_duration_ms: int = 0
    total_llm_calls: int = 0
    revision_loops: int = 0
    final_answer: str = ""
    final_confidence: float = 0.0
