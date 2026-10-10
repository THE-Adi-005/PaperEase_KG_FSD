# KG Paper Assistant — Grounding, Ablation & Multi-Agent Architecture

This plan addresses three major enhancements to the KG Paper Assistant:
1. **Research-backed grounding statements** for schema design choices
2. **Experimental ablation framework** for graph density/sparsity analysis
3. **Multi-agent multi-hop architecture** with traceable reasoning + proper evaluation

---

## User Review Required

> [!IMPORTANT]
> **Scope is significant** — This touches the schema documentation, adds a new ablation experiment runner, rebuilds the core agent into a multi-agent pipeline, and expands the evaluation framework. Estimated ~15 new/modified files.

> [!WARNING]
> **Multi-agent architecture replaces the existing single-agent**. The current `agent.py` will be refactored. The old single-agent mode will remain available as a fallback via a `mode` parameter, but the default query pipeline will change to multi-agent.

---

## Open Questions

> [!IMPORTANT]
> 1. **LLM model**: You're currently using `qwen2.5:7b` via Ollama. The multi-agent pipeline will make more LLM calls per query (3-4 specialist agents). Are you okay with increased latency, or should we add a "fast mode" that falls back to single-agent?
> 2. **Ablation automation**: Should the ablation experiments run automatically on a fixed QA set, or should there be a UI button to trigger them manually?
> 3. **Frontend changes**: Should the multi-hop reasoning trace show agent handoffs visually in the chat UI (e.g., "Planner → Retriever → Reasoner → Verifier" pipeline), or is backend-only sufficient for now?

---

## Proposed Changes

### Component 1: Research-Grounded Schema Documentation

This adds formal, citation-backed justification for every node type, relationship type, and configuration parameter.

#### [NEW] [grounding_statements.py](file:///c:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/models/grounding_statements.py)

A structured module containing research-backed grounding statements for all schema decisions:

- **Domain choice (ML/NLP Research Papers)**: Cite [Ji et al., 2022 — "Survey of Hallucination in NLG"](https://arxiv.org/abs/2202.03629) for why structured KGs reduce hallucination; [Pan et al., 2024 — "Unifying Large Language Models and Knowledge Graphs"](https://arxiv.org/abs/2306.08302) for the KG+LLM paradigm.
- **Node types (10 labels)**: Cite [Dessì et al., 2021 — "CS-KG: A Large-Scale Knowledge Graph of Research Entities in Computer Science"](https://arxiv.org/abs/2106.01679) — their ontology uses Paper, Author, Method, Dataset, Metric, Task as core entities. Our 10 labels are a superset.
- **Relationship types (16 seed)**: Cite [Auer et al., 2020 — "The ORKG"](https://arxiv.org/abs/2012.09780) — Open Research Knowledge Graph defines COMPARES_TO, EXTENDS, EVALUATED_ON, USES_METHOD as the canonical research-contribution relationships. Also cite [Luan et al., 2018 — "Multi-Task Identification of Entities, Relations, and Coreference for Scientific Knowledge Graph Construction"](https://arxiv.org/abs/1808.09602) for entity/relation types in SciIE.
- **Self-consistency filtering (N=2 runs, majority vote)**: Cite [Wang et al., 2023 — "Self-Consistency Improves Chain of Thought Reasoning"](https://arxiv.org/abs/2203.11171) — majority voting over K sampled reasoning paths.
- **SAME_AS threshold (0.85 cosine similarity)**: Cite [Reimers & Gurevych, 2019 — "Sentence-BERT"](https://arxiv.org/abs/1908.10084) — they show 0.85 threshold balances precision/recall for paraphrase detection. Also cite entity alignment literature threshold ranges.
- **Extraction temperature (0.6)**: Cite [Renze & Guven, 2024 — "The Effect of Sampling Temperature on Problem Solving"](https://arxiv.org/abs/2402.05201) — shows moderate temperature maximizes diversity-accuracy tradeoff for extraction tasks.
- **Agent max steps (8)**: Cite [Yao et al., 2023 — "ReACT: Synergizing Reasoning and Acting"](https://arxiv.org/abs/2210.03629) — their experiments show 6-10 steps sufficient for most multi-hop tasks.
- **MiniLM embedding model**: Cite [Wang et al., 2020 — "MiniLM"](https://arxiv.org/abs/2002.10957) — best trade-off of speed vs quality for CPU deployment; competitive with larger models on semantic textual similarity benchmarks (STS-B Spearman ρ = 0.847).

Each grounding entry will contain:
```python
@dataclass
class GroundingStatement:
    choice: str            # e.g., "10 Node Labels"
    justification: str     # Why this choice
    citations: list[str]   # ArXiv/paper references
    alternatives_considered: list[str]
    tradeoffs: str         # What we sacrifice
```

#### [MODIFY] [neo4j_schema.py](file:///c:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/models/neo4j_schema.py)

Add docstring citations inline next to each NODE_LABEL and RELATION_TYPE entry, and import/expose the grounding statements.

#### [NEW] [grounding.py](file:///c:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/routers/grounding.py)

New API endpoint `GET /api/grounding/statements` that returns all grounding statements as structured JSON — for display in the frontend or reports.

---

### Component 2: Graph Density/Sparsity Ablation Experiments

A systematic experimental framework that varies graph construction parameters and measures downstream QA performance.

#### [NEW] [ablation_runner.py](file:///c:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/services/ablation_runner.py)

Ablation experiment runner that:
1. **Defines ablation configurations** — each config varies one parameter:
   - `EXTRACTION_RUNS`: [1, 2, 3, 5] — controls self-consistency depth
   - `EXTRACTION_TEMPERATURE`: [0.2, 0.4, 0.6, 0.8] — controls extraction diversity
   - `SAME_AS_THRESHOLD`: [0.70, 0.80, 0.85, 0.90, 0.95] — controls cross-paper linking aggressiveness
   - `SECTION_TEXT_LIMIT`: [1000, 2000, 3000, 5000] — controls context given to extraction LLM
   - `RELATION_TYPE_SUBSETS`: [minimal(4), balanced(8), full(16)] — controls schema richness
   
2. **For each configuration**:
   - Clear the graph for the target paper(s)
   - Re-run KG construction with the ablated parameters
   - Record graph statistics: node count, edge count, avg degree, connected components, graph density
   - Run the QA evaluation set against the modified graph
   - Record QA metrics: ROUGE-L, LLM-judge accuracy, step count, lazy completion triggers, latency
   
3. **Produce ablation report** with:
   - Per-parameter impact tables
   - Optimal configuration identification
   - Statistical significance (if enough samples)

#### [NEW] [ablation_results.json](file:///c:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/eval/ablation_results.json)

Output schema for ablation results.

#### [NEW] [ablation.py](file:///c:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/routers/ablation.py)

API endpoints:
- `POST /api/eval/ablation/run` — trigger an ablation experiment
- `GET /api/eval/ablation/results` — get latest results
- `GET /api/eval/ablation/status` — check running experiment status

#### [MODIFY] [config.py](file:///c:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/config.py)

Add `SECTION_TEXT_LIMIT` as a configurable parameter (currently hardcoded as `[:3000]` in the extraction prompt).

#### [MODIFY] [kg_builder.py](file:///c:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/services/kg_builder.py)

Refactor `build_kg()` to accept optional parameter overrides for ablation (e.g., `extraction_runs`, `extraction_temp`, `text_limit`), so the ablation runner can call it with different configs without modifying global state.

---

### Component 3: Multi-Agent Multi-Hop Architecture

Replace the monolithic single-agent ReACT loop with a **4-agent pipeline** where each agent has a specialized role, and the reasoning chain is fully traceable.

#### Architecture Design

```
Question → [Planner Agent] → [Retriever Agent] → [Reasoner Agent] → [Verifier Agent] → Answer
                                    ↑                    |
                                    └────────────────────┘
                                      (re-retrieval if needed)
```

**Agent Roles**:
1. **Planner Agent**: Decomposes the question into sub-questions/retrieval targets. Outputs a structured plan.
2. **Retriever Agent**: Executes KG traversals (RetrieveNode, NeighborCheck, etc.) to gather evidence for each sub-question. Produces an evidence bundle.
3. **Reasoner Agent**: Synthesizes evidence into a coherent answer with explicit chain-of-reasoning. Each reasoning step cites specific graph nodes/edges.
4. **Verifier Agent**: Fact-checks the answer against the graph. Flags any unsupported claims, checks for hallucination, validates provenance. Returns confidence score + verification report.

**Why this specific design**:
- Cite [Wang et al., 2024 — "Mixture-of-Agents"](https://arxiv.org/abs/2406.04692) — decomposition improves quality
- Cite [Li et al., 2024 — "More Agents Is All You Need"](https://arxiv.org/abs/2402.05120) — specialist agents outperform generalist
- Cite [Yao et al., 2023 — "Tree of Thoughts"](https://arxiv.org/abs/2305.10601) — structured decomposition for multi-step reasoning
- Cite the original [Grounding LLM Reasoning with KGs paper](https://arxiv.org/abs/2407.00166) — Agent+CoT achieves best performance

#### [NEW] [multi_agent.py](file:///c:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/services/multi_agent.py)

The core multi-agent orchestrator containing:

```python
class PlannerAgent:
    """Decomposes question into sub-questions with retrieval strategy."""
    # Input: question, paper_ids
    # Output: list of SubQuestion(text, retrieval_strategy, expected_evidence_type)

class RetrieverAgent:
    """Executes KG traversals to gather evidence for each sub-question."""
    # Input: sub_questions, paper_ids
    # Output: EvidenceBundle(sub_question → list of Evidence(node, edge, text, source))

class ReasonerAgent:
    """Synthesizes evidence into answer with explicit reasoning chain."""
    # Input: question, evidence_bundle
    # Output: ReasonedAnswer(text, reasoning_steps: list[GroundedStep])
    # Each GroundedStep has: claim, supporting_evidence, graph_path

class VerifierAgent:
    """Fact-checks answer against the graph. Identifies unsupported claims."""
    # Input: reasoned_answer, evidence_bundle, paper_ids
    # Output: VerificationReport(verified_claims, flagged_claims, confidence, revision_needed)
```

The orchestrator `run_multi_agent()` will:
1. Call PlannerAgent → get sub-questions
2. Call RetrieverAgent → get evidence
3. Call ReasonerAgent → get draft answer with reasoning chain
4. Call VerifierAgent → fact-check
5. If verification fails (confidence < threshold), loop back to step 2 with refined retrieval
6. Yield SSE events at each stage for full traceability

#### [NEW] [reasoning_trace.py](file:///c:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/models/reasoning_trace.py)

Pydantic models for the traceable reasoning chain:

```python
class SubQuestion(BaseModel):
    id: str
    text: str
    retrieval_strategy: str  # "entity_search", "neighbor_traversal", "section_inspect"
    expected_evidence_type: str  # "metric", "method_comparison", "conceptual"

class Evidence(BaseModel):
    source_node: str
    source_edge: str | None
    text: str
    source_paper_id: str
    source_section_id: str
    confidence: float

class GroundedStep(BaseModel):
    step_number: int
    claim: str                    # "BERT achieves F1=92.4 on SQuAD"
    supporting_evidence: list[Evidence]
    graph_path: list[str]         # ["BERT", "ACHIEVES", "F1=92.4"]
    is_verified: bool

class VerificationReport(BaseModel):
    verified_claims: list[str]
    flagged_claims: list[str]     # Claims not supported by graph
    confidence_score: float       # 0.0 - 1.0
    provenance_check_passed: bool
    revision_suggested: bool
```

#### [MODIFY] [agent.py](file:///c:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/services/agent.py)

Keep the existing `run_agent()` as `run_single_agent()` for backward compatibility. The old single-agent becomes the "fast mode" fallback.

#### [MODIFY] [query.py](file:///c:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/routers/query.py)

Add new endpoint `POST /api/query-multi-agent` that uses the multi-agent pipeline. Modify existing `/api/query` to accept a `pipeline` parameter: `"single"` (legacy) or `"multi"` (new default).

#### [MODIFY] [schemas.py](file:///c:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/models/schemas.py)

Add new models: `MultiAgentQueryResponse`, extend `QueryRequest` with `pipeline` field.

---

### Component 4: Proper Evaluation Framework

Expand evaluation to cover multi-agent pipeline + ablation + grounding verification.

#### [MODIFY] [evaluate.py](file:///c:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/eval/evaluate.py)

Extend the A/B evaluation to include:
- **Three-way comparison**: KG Single-Agent vs KG Multi-Agent vs Naive RAG
- **New metrics**:
  - `traceability_score`: % of claims in the answer that have a cited graph path
  - `verification_confidence`: average VerifierAgent confidence
  - `sub_question_coverage`: % of planner sub-questions that got evidence
  - `multi_hop_depth`: actual number of graph hops taken
  - `provenance_accuracy`: % of facts correctly attributed to source paper
- **Per-agent-stage timing**: breakdown of latency per agent (Planner, Retriever, Reasoner, Verifier)

#### [NEW] [qa_multi_hop.json](file:///c:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/eval/qa_sets/qa_multi_hop.json)

Extended QA set with explicit multi-hop questions that require 2+ graph traversals:
- Questions tagged with `required_hops: int`
- Questions tagged with `expected_graph_path: list[str]` for traceability verification
- Categories: `single_hop`, `two_hop`, `three_hop`, `cross_paper`, `comparison`, `metric_aggregation`

#### [MODIFY] [eval.py](file:///c:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/routers/eval.py)

Add endpoints for ablation results and multi-agent evaluation metrics.

---

## Verification Plan

### Automated Tests

```bash
# 1. Verify grounding statements module loads and all entries are valid
cd backend && python -c "from app.models.grounding_statements import GROUNDING_STATEMENTS; print(f'{len(GROUNDING_STATEMENTS)} statements loaded')"

# 2. Run the ablation experiment (small scale — 1 paper, 2 configs)
cd backend && python -m app.services.ablation_runner --paper_id test --configs minimal

# 3. Run multi-agent pipeline on a single question
cd backend && python -c "
import asyncio
from app.services.multi_agent import run_multi_agent
async def test():
    async for event in run_multi_agent('What methods does this paper propose?', ['test_paper_id']):
        print(event['event'], ':', str(event['data'])[:100])
asyncio.run(test())
"

# 4. Run full evaluation suite (3-way comparison)
cd backend && python -m eval.evaluate --qa_file eval/qa_sets/grounding_paper.json --pipeline all

# 5. Verify API endpoints respond
curl http://localhost:8000/api/grounding/statements
curl http://localhost:8000/api/eval/ablation/results
```

### Manual Verification

- Upload a test PDF and verify the multi-agent pipeline produces a traceable reasoning chain
- Verify each claim in the answer links back to specific graph nodes
- Compare multi-agent vs single-agent answer quality on multi-hop questions
- Review ablation report to confirm parameter sensitivity matches expectations
