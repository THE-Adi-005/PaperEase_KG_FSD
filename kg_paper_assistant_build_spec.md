# Build Spec: Knowledge-Graph-Grounded Research Paper Assistant

## Context for the builder model

You are implementing a full-stack application for an FSD (Full Stack Development) academic
project. The core idea is adapted from the paper *"Grounding LLM Reasoning with Knowledge
Graphs"* (Amayuelas et al., JPMorgan AI Research / UC Santa Barbara, NeurIPS 2025 Workshop).
That paper grounds LLM reasoning by linking each reasoning step to a knowledge graph (KG),
using two interaction methods (an Agent with explicit tools, and Automatic Graph Exploration
with BFS + pruning) combined with three reasoning strategies (CoT, ToT, GoT). It's evaluated
on GRBench, a benchmark of pre-built domain KGs.

This project adapts that idea to a new setting: instead of pre-built domain KGs, **we build the
KG ourselves from uploaded research papers**, then use the paper's Agent + CoT retrieval
pattern as a KG-RAG layer that grounds LLM answers *before* generation, with full traceability
of the reasoning path back to source KG triples, source paper sections, and figures/tables.

Build this as a working, demoable full-stack application. Prioritize a **working end-to-end
pipeline over exhaustive feature coverage**. Ask me clarifying questions only if a decision
would be expensive to reverse later; otherwise pick the most reasonable default and note the
assumption.

---

## 1. Product requirements

The app lets a user:
1. Upload one or more research paper PDFs.
2. See each paper automatically parsed into a knowledge graph (entities: methods, datasets,
   metrics, concepts, figures, tables, authors, sections; relations: uses, reports, discusses,
   cites, illustrates, etc.).
3. Ask natural-language questions about a **single selected paper**, get an answer grounded in
   the KG, with a visible step-by-step reasoning trace (which KG nodes/edges were consulted).
4. Ask **cross-paper** questions ("how does Paper A's method differ from Paper B's?") that
   traverse a merged subgraph of multiple selected papers, with per-claim attribution to the
   source paper.
5. View extracted figures/tables inline, linked to the section/claim that cites them.
6. View the KG subgraph that was actually used to answer the last question (not the whole
   graph — keep it focused and readable).

## 2. Hardware / environment constraints (IMPORTANT — zero paid API budget)

- Student project, **zero dollars for API usage**. Everything must run on local/self-hosted
  infrastructure.
- Available hardware: two machines.
  - Machine A: NVIDIA RTX 4060, 6GB VRAM, 24GB system RAM.
  - Machine B: NVIDIA RTX 3050, 8GB VRAM, 32GB system RAM.
- Run the LLM inference server (Ollama) on Machine A, using a 7-8B instruct model at Q4_K_M
  quantization (e.g. `qwen2.5:7b` or `llama3.1:8b`) — fits comfortably in 6GB VRAM and gives
  roughly 30-50 tokens/sec on this class of GPU. Use **one model for both extraction and
  reasoning** unless testing shows a clear quality gap that justifies a second, larger model.
- Run Neo4j, FastAPI, GROBID, and the React dev server on Machine B (more system RAM headroom).
  FastAPI's LLM client should point at Machine A's Ollama endpoint over LAN
  (`OLLAMA_HOST=0.0.0.0`, firewalled to the LAN only).
- All LLM calls go through Ollama's OpenAI-compatible endpoint
  (`http://<machine-a-ip>:11434/v1`) so the client code is a drop-in OpenAI-style client, not a
  bespoke integration.
- Embeddings for entity resolution use `sentence-transformers` (`all-MiniLM-L6-v2`), CPU-only,
  no GPU needed for this piece.

## 3. Tech stack

- **Backend:** Python, FastAPI, async where it matters (ingestion jobs, SSE streaming).
- **Graph DB:** Neo4j Community Edition (Docker).
- **PDF parsing:** GROBID (Docker) for structured TEI-XML (sections, references, authors,
  figure/table captions). PyMuPDF for raw image extraction. pdfplumber for table structure
  extraction (need actual row/column cell data, not just captions — see Section 6).
- **LLM serving:** Ollama, OpenAI-compatible client in Python (`openai` package pointed at the
  Ollama base URL).
- **Frontend:** React (Vite), Cytoscape.js or react-force-graph for graph visualization, SSE
  (EventSource) for streaming the live reasoning trace.
- **Background jobs:** FastAPI `BackgroundTasks` for MVP; upgrade to Celery/RQ only if ingestion
  latency becomes a real bottleneck in testing.
- **Entity resolution:** `sentence-transformers` + cosine similarity, no LLM call.

## 4. Data model (Neo4j schema)

Node labels: `Paper`, `Author`, `Section`, `Concept`, `Method`, `Dataset`, `Metric`, `Figure`,
`Table`, `Citation`.

Relationship types (attach `source_paper_id` and, where applicable, `source_section_id` as
properties on every edge for provenance/traceability):
- `AUTHORED_BY` (Paper -> Author)
- `CONTAINS_SECTION` (Paper -> Section)
- `DISCUSSES_CONCEPT` (Section -> Concept)
- `USES_METHOD` (Paper/Section -> Method)
- `REPORTS_METRIC` (Method/Table -> Metric, with a `value` property)
- `ILLUSTRATED_BY` (Section -> Figure | Table)
- `CITES` (Paper -> Citation)
- `SAME_AS` (Concept -> Concept, cross-paper link via embedding similarity, see Section 8)

Design the schema so it can evolve (see Section 7, dynamic schema induction) without breaking
existing queries — new relation types should be additive, not require migrations.

## 5. Pipeline phases (build in this order)

**Phase 0 — Environment.** Docker Compose for Neo4j + GROBID. Ollama running natively on
Machine A (GPU passthrough needed if containerized — recommend running Ollama outside Docker on
Machine A to avoid GPU passthrough complexity). FastAPI skeleton with a `/health` endpoint that
checks both Neo4j and Ollama connectivity. Verify `ollama ps` / `nvidia-smi` show GPU offload,
not silent CPU fallback, before proceeding.

**Phase 1 — Ingestion & parsing.** `parse_pdf(path) -> ParsedPaper`: call GROBID's
`/api/processFulltextDocument`, parse TEI-XML into title/authors/abstract/ordered sections with
text/reference list. Separately extract figures (PyMuPDF) and full table cell data (pdfplumber),
keyed to `paper_id/section_id`. Test on 3-4 structurally different papers before automating.

**Phase 2 — KG construction.** Per-section LLM extraction into `(head, relation, tail,
source_section_id)` triples. Schema-validate relation types before writing to Neo4j. Run as a
background job per paper upload, with a progress indicator in the UI (this can take a couple of
minutes per paper depending on section count — that's expected and fine to background).
Incorporate the self-consistency filtering and lazy-completion ideas from Section 7 here.

**Phase 3 — Neo4j load + cross-paper linking.** MERGE nodes/edges. Embed `Concept` node names
with MiniLM, cosine-similarity match (threshold ~0.85 to start, tune empirically) to create
`SAME_AS` edges across papers.

**Phase 4 — Agent + CoT reasoning (core deliverable).** Implement four tools as Cypher-backed
Python functions: `RetrieveNode(keyword)`, `NodeFeature(node_id, feature)`,
`NeighborCheck(node_id, edge_type)`, `NodeDegree(node_id, edge_type)`. Implement the ReACT loop
(ollama call: thought -> action -> observation -> repeat) with a step cap (start at 8, tune).
Stream every thought/action/observation to the frontend via SSE — this is both a UX necessity
(local inference isn't instant) and the core interpretability feature the whole project is
built around. On retrieval failure, trigger the lazy graph completion described in Section 7.

**Phase 5 — FastAPI + React wiring.** Endpoints: `POST /upload`, `GET /papers`,
`GET /paper/{id}/graph`, `GET /paper/{id}/figures`, `POST /query` (SSE-streamed), `POST /compare`
(multi-paper, SSE-streamed). React: paper picker/uploader, chat-style question box, live
reasoning-trace panel, graph panel, figure/table panel.

**Phase 6 — Visualization.** Render only the subgraph touched by the last reasoning trace, not
the full KG (full-graph rendering will visibly lag in-browser for real papers with hundreds of
nodes). Figure/table panel shows items tied to sections cited in the current answer.

**Phase 7 — Multi-paper QA.** Extend `RetrieveNode` to search across all selected `paper_id`s
plus `SAME_AS` edges. Final answer synthesis must include per-claim paper attribution
(e.g. "According to Paper A, ...; Paper B reports a different approach...").

**Phase 8 — Evaluation.** Rouge-L (`rouge-score` package) against a small hand-written QA set
per paper. LLM-as-judge using the same local 7-8B model as judge (note explicitly in the
project report that a local judge is weaker/noisier than GPT-4o-class judges; mitigate by
sampling the judge call 2-3 times and taking a majority vote).

**Phase 9 — Stretch: ToT.** Add a state evaluator (`Selection` or `Score`, per the reference
paper's Section 4.1) and a BFS wrapper around the Phase 4 loop, branching factor k=3, depth 3.
Only attempt after Phases 1-8 are stable and demoable.

## 6. Table/figure handling (do this properly, don't just caption-summarize)

- Extract actual table structure via pdfplumber (rows, columns, headers), not just the caption
  text. Parse into template triples: `(row_entity, {column_header}, cell_value)` — e.g. a
  results table becomes queryable facts like "Model X achieves F1=0.85 on Dataset Y" instead of
  an opaque caption string. This is what makes questions like "which method scored highest on
  X" answerable via graph traversal instead of text search.
- Link every `Figure`/`Table` node to its nearest preceding/following in-text reference via
  GROBID's citation markers, so the QA system can say "see Figure 3" and the UI can actually
  surface that figure.

## 7. Novel extraction/construction techniques to implement (this is the project's key
differentiator — implement at least #1)

Frame these honestly in the project report as **underexplored technique combinations for this
specific application domain**, not as unprecedented inventions — some extend published ideas
(self-consistency, ontology induction, citation intent classification) into a phase or setting
they aren't usually applied to.

1. **Query-driven lazy graph completion (implement this one — it's the architectural
   contribution).** Don't exhaustively extract every possible triple on ingest. Build a
   lightweight initial graph (section-level entity mentions only — cheap). At query time, when
   the Agent's retrieval loop fails to find sufficient triples to answer confidently, trigger a
   **targeted re-extraction pass** on the specific source section text, using a query-focused
   prompt ("extract only triples relevant to: {missing_relation_or_entity}"). This closes the
   loop between KG construction (normally front-loaded and exhaustive) and reasoning-time
   retrieval (normally read-only against a static graph) — the reference paper treats these as
   fully separate phases and lists extending this kind of dynamic behavior as future work.
   Log a metric: % of queries that triggered lazy completion, and the marginal Rouge-L gain
   from it, for the project report.

2. **Self-consistency filtering for extraction.** Run the extraction prompt 2-3 times per
   section at moderate temperature (~0.5-0.7); commit a triple to Neo4j only if it appears in a
   majority of samples. Filters hallucinated relations without a separate verifier LLM call.

3. **Structured table-to-triple parsing.** Covered in Section 6 — implement as part of Phase 2.

4. **Dynamic schema induction with periodic consolidation (stretch).** Let the extraction LLM
   propose new relation types outside the seed schema; log proposals separately; periodically
   cluster proposed types by embedding similarity and merge near-duplicates before promoting
   into the live schema. Prevents both a too-rigid schema and schema explosion.

## 8. Evaluation & report deliverables

- Rouge-L and local-LLM-judge scores per paper/domain, following the reference paper's
  methodology (Section 5) as closely as feasible.
- Ablation matching the reference paper's Section 7 findings but **adding a wall-clock latency
  axis** they didn't measure (they only counted LLM-call complexity, Appendix E): plot accuracy
  vs. average query latency across at least two model sizes (e.g. the 7-8B primary model vs. a
  smaller 3-4B model if time allows) — this is a legitimate extension of their ablation study
  given that local inference speed is a real constraint they didn't have to face on hosted
  infrastructure.
- Report the lazy-completion trigger rate and its effect on accuracy (from item 1 above).
- Be explicit in the report about what's a direct application of the reference paper's methods
  (Agent tools, ReACT loop, CoT baseline) vs. what's a new contribution (lazy completion,
  table-to-triple parsing, self-consistency extraction filtering).

## 9. Build order priority (if time-constrained, cut from the bottom up)

1. Phases 0-5 (working single-paper ingest -> KG -> Agent+CoT QA -> UI) — this is the
   non-negotiable MVP.
2. Phase 6 (focused graph viz) and figure/table linking.
3. Phase 7 (multi-paper QA).
4. Novel technique #1 (lazy completion) — do this before #2-4, it's the headline contribution.
5. Phase 8 (formal evaluation + latency ablation) for the report.
6. Novel techniques #2-4, Phase 9 (ToT) — genuine stretch goals only.

## 10. Reference material

The reasoning-strategy definitions (CoT/ToT/GoT), the Agent tool set, the Automatic Graph
Exploration algorithm (Algorithm 1), and the extraction/pruning prompt templates (Appendix F)
are drawn from Amayuelas et al., "Grounding LLM Reasoning with Knowledge Graphs" (NeurIPS 2025
Workshop: Foundations of Reasoning in Language Models). Reuse their Appendix F prompt templates
as starting points for both the KG-construction extraction prompts and the Agent/ReACT prompts,
adapting from "traverse a pre-built graph" framing to "traverse a graph you built from this
paper" framing.
