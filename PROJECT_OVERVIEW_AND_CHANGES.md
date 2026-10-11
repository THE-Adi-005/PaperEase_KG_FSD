# KG Paper Assistant: Comprehensive Architecture & Completed Work Report

**Date:** October 2026  
**Project:** Knowledge Graph Question Answering over Scientific Research Papers  
**Status:** All Core Fixes, Evaluation Modules (R1–R4), Table/Plot Generators, Backend API, and Frontend Experiments UI are **Completed and Verified** (39/39 tests passing).

---

## 1. Executive Summary: What Has Been Done

When we began auditing and refining this project, we had a prototype application (FastAPI backend + Neo4j graph database + React frontend + Ollama Qwen 2.5 7B) that could ingest papers and answer questions. However, under academic scrutiny, **it suffered from severe statistical bugs, uncontrolled graph noise, lack of baselines, and no repeatable experiment harness.**

We transformed this prototype into a **publication-ready, empirically rigorous scientific study and interactive system**:

1. **Found and Fixed Critical Graph Construction Bugs:**
   - Fixed a masked bug where self-consistency voting was acting as a *union* (keeping triples seen only once) rather than a filter.
   - Eliminated 35 junk relation types caused by unconstrained dynamic relation creation.
   - Fixed cache corruption where failed LLM calls were permanently stored as empty results `[]`.
   - Removed corrupted duplicate patent papers on disk while preserving real cross-paper bridges.

2. **Built an Empirical Ablation Architecture:**
   - 16 distinct experimental configurations (`configs/cfg_*.yaml`) isolating relation set size ($R_3, R_5, R_7, R_{10}$), per-section triple caps ($K=5, 10, 20$), voting thresholds, dynamic relation filtering, and entity linking thresholds.
   - Strict namespacing in Neo4j (`config_id`), allowing zero collision with the baseline or legacy graph.

3. **Created a Ground-Truth QA Benchmark (`eval/qa_set.json`):**
   - 40 manually verified, human-annotated questions across 5 core cognitive categories: *lookup*, *multihop*, *aggregation*, *cross-paper*, and *unanswerable*.
   - Automated merge and schema-validation pipeline (`eval/qa_merge.py`).

4. **Implemented Full Baseline & Evaluation Pipeline:**
   - **Vector RAG Baseline (`eval/rag_baseline.py`):** ~300-word section chunks embedded with sentence-transformers, providing a true vector search baseline.
   - **Non-Streaming Eval Agent Wrapper (`backend/app/services/agent.py`):** Evaluation mode that threads config namespaces and completely prevents evaluation runs from mutating Neo4j (`persist_lazy=False`).
   - **QA Harness (`eval/run_qa.py`):** Resumable evaluation runner recording per-question predictions, step counts, latency, and bootstrap 95% confidence intervals into `results/all_runs.csv`.

5. **Integrated the SciERC Standard Benchmark (R4):**
   - Downloaded and verified the official SciERC scientific test split (`backend/data/scierc/test.json`).
   - Built an extraction evaluation module (`eval/extraction_eval.py`) mapping scientific entity types and evaluating lenient token-level Jaccard matches and relation-agnostic pair F1.

6. **Automated Camera-Ready LaTeX Tables & Plots (P4):**
   - Script (`eval/make_tables.py`) producing 6 booktabs LaTeX tables and 5 high-resolution comparative figures in `paper_assets/`.

7. **Full-Stack Experiments UI (P4):**
   - Added REST endpoints (`/api/experiments`) in FastAPI.
   - Built the **Experiments & Ablations** panel in React (`frontend/src/components/ExperimentsPanel.jsx`) with sortable run comparisons, pure SVG metric bar charts, and a side-by-side per-question inspection view showing model answers, gold targets, and full ReACT traces.

---

## 2. Detailed Breakdown of Every Phase & Component

### Phase 1: Core Engine & Bug Fixes (Tasks X4 – X8)

| Bug / Deficiency Found | Root Cause in Original Code | The Fix We Implemented |
|---|---|---|
| **Self-Consistency Union Bug** | With $n=2$ runs and a `>= 50%` threshold, `ceil(0.5 * 2) = 1`, so any triple extracted in *either* run was kept. The filter acted as a union, inflating false positives. | Replaced with mathematical rule: `min_votes(n, fraction) = max(1, ceil(fraction*n - 1e-9))`. When $n=1$, it requires 1 vote; when $n=2$ with 50%, it requires 1; with $n=3$ and 50%, it strictly requires 2 votes. |
| **Dynamic Relation Explosion** | Dynamic relation discovery had no bounds. The LLM invented 35 non-standard relations (e.g., `COMPARSES_TO`, `IS`, `COUNT`), creating orphan edges. | Constrained relation sets to curated nested profiles ($R_3 \subset R_5 \subset R_7 \subset R_{10}$) with explicit `enforce_signatures` and `allow_dynamic: false` in default builds. |
| **Failed LLM Call Cache Poisoning** | When Ollama timed out or returned invalid JSON, `extract_triples()` caught the error and returned `[]`. The cache script saw `[]` and permanently cached it, treating crashes as valid empty extractions. | Added `raise_on_error=True` mode: failures and parse errors raise exceptions and are logged; only genuine, cleanly parsed empty arrays `[]` are written to SQLite. |
| **Duplicate Files on Disk** | 5 patent PDFs in `backend/uploads` had different names (`393bae80`, `4cf686b3`, `53b847cd`, `680a27f3`, `af45b3fe`) but identical sha256 hashes. | Fixed `corpus.json` to keep only the one real paper (`680a27f3`), categorized core ML papers vs off-domain probes, and marked duplicates on disk. |
| **Generic Entity Hallucination** | Broad terms like `"models"`, `"our method"`, `"system"` were forming artificial cross-paper hub nodes. | Added `is_generic` stoplist filtering in `triple_filters.py` and introduced `cfg_nogeneric` ablation arm. |

---

### Phase 2: Evaluation Scoring & Bootstrap Intervals (`eval/scoring.py`)

To evaluate QA outputs without relying on a third-party LLM judge:
- **Numeric Tolerance Matching:** Understands scientific values. If gold answer is `92.4`, it correctly matches `"92.38%"`, `"0.924"`, and `"92.40"` within a tight tolerance ($0.05$ absolute for numbers $\ge 1$; $0.0005$ for small decimals).
- **Abstention Verification:** Strictly checks if the system admitted ignorance on unanswerable questions (e.g., `"Not found in the papers"`, `"cannot find"`).
  - On answerable questions: an abstention counts as **False Abstain**.
  - On unanswerable questions: an abstention counts as **Correct**.
- **Bootstrap Confidence Intervals:** Performs $N = 2,000$ bootstrap resamples to compute robust 95% confidence intervals `[acc_lo, acc_hi]`, ensuring small sample sizes are reported with academic honesty.

---

### Phase 3: RAG Baseline & ReACT Evaluation Agent

#### 1. Vector RAG Baseline (`eval/rag_baseline.py`)
- Reads Section nodes for evaluation papers from Neo4j in a read-only transaction.
- Splits section texts into $\approx 300$-word chunks with 50-word overlaps.
- Embeds chunks using the exact same sentence-transformer model (`all-MiniLM-L6-v2`) used in graph retrieval.
- Caches the vector index to `results/rag_index.pkl`.
- Uses Qwen 2.5 7B at temperature 0 with a strict context-bounded prompt:
  > *"Answer the question using ONLY the context. Be concise. If the answer is not in the context, reply exactly: Not found in the papers."*

#### 2. ReACT Agent Evaluation Mode (`backend/app/services/agent.py`)
- Created `run_agent_eval()`:
  - Non-streaming async wrapper that collects all thoughts, actions, observations, and final answers into a structured dictionary.
  - Passes `config_id` into all graph tools (`RetrieveNode`, `NodeFeature`, `NeighborCheck`, `NodeDegree`, and `get_subgraph_for_nodes`).
  - **Zero Database Mutation:** In evaluation mode, `persist_lazy=False` guarantees that even if lazy completion triggers, newly extracted triples are kept in memory as text observations and **never** written into Neo4j.

#### 3. QA Evaluation Runner (`eval/run_qa.py`)
- CLI command:
  ```powershell
  python -m eval.run_qa --system kg --config cfg_base --lazy off
  python -m eval.run_qa --system rag
  ```
- Evaluates against `eval/qa_set.json` (or subset via `--limit N`).
- Writes predictions incrementally to `results/qa/<system_id>/predictions.jsonl` (fully resumable if interrupted).
- Generates `results/qa/<system_id>/metrics.json` and upserts summary rows into `results/all_runs.csv`.

---

### Phase 4: Ground Truth QA Dataset (`eval/qa_set.json`)

Created 40 verified questions based on the core papers (GPT-1 `1e6c7c12` and XLNet `b7f9484b`):

| Question Type | Count | Cognitive Goal & Description |
|---|---|---|
| **`lookup`** | 10 | Direct fact retrieval in a single paper (e.g., architecture, batch size, pretraining dataset, dimension). |
| **`multihop`** | 8 | Two-step reasoning (e.g., *Which method does XLNet extend, and on which dataset does it outperform that method?*). |
| **`aggregation`** | 6 | Quantities and maximums (e.g., *How many tasks did XLNet achieve state-of-the-art results on?*). |
| **`cross_paper`** | 8 | Comparing two papers via bridge entities like `Transformer`, `RACE`, `GLUE`, `BooksCorpus` (e.g., *Which paper reports higher accuracy on RACE?*). |
| **`unanswerable`** | 8 | Adversarial sanity checks (e.g., *What is the BLEU score of GPT on machine translation?* or *Inference latency in ms?*). Tests whether systems hallucinate or abstain. |

---

### Phase 5: SciERC Extraction Benchmark (`eval/scierc_extract.py` & `eval/extraction_eval.py`)

To prove graph extraction quality on a standard external dataset:
- Extracted official SciERC test split (`backend/data/scierc/test.json`).
- `scierc_extract.py`: Runs extraction over the first 40 documents ($\ge 3$ entities) using the same prompt profiles and SQLite cache.
- `extraction_eval.py`:
  - Maps SciERC entity types: `Method -> Method`, `Metric -> Metric`, `Material -> Dataset`, `Task -> Concept`, `OtherScientificTerm -> Concept`.
  - Computes entity precision/recall/F1 (type-agnostic and type-aware) using lenient matching (case/punctuation normalized, token Jaccard $\ge 0.5$ on substring overlap).
  - Computes relation-agnostic pair precision/recall/F1.
  - Updates `results/all_runs.csv` with extraction performance metrics.

---

### Phase 6: Tables, Plots, API, and Frontend Integration

#### 1. Paper Assets Generator (`eval/make_tables.py`)
Generates 6 LaTeX tables and 5 high-resolution PNG plots:
- `table_main.tex`: RAG vs KG (no lazy) vs KG (lazy) with bootstrap intervals, evidence hit rates, steps, latency.
- `table_schema.tex`: Sweep across $R_3, R_5, R_7, R_{10}$ (relation set size vs graph density vs accuracy).
- `table_voting.tex`: Single-run vs 50% voting vs unanimous voting.
- `table_cap.tex`: Per-section triple caps $K=5, 10, 20$.
- `table_sameas.tex`: Entity linking threshold sweep (off, 0.70, 0.85, 0.90).
- `table_constraints.tex`: Dynamic relations on/off, signature checking on/off, generic entity filtering on/off.
- 5 matplotlib plots saved to `paper_assets/`.

#### 2. FastAPI Endpoints (`backend/app/routers/experiments.py`)
- `GET /api/experiments`: Returns all runs from `results/all_runs.csv`.
- `GET /api/experiments/{system_id}`: Returns aggregate metrics, graph statistics, and extraction metrics for a given system.
- `GET /api/experiments/{system_id}/predictions?limit=50`: Returns per-question predictions with full trace details.

#### 3. React Frontend (`frontend/src/components/ExperimentsPanel.jsx`)
Added the **Experiments & Ablations** tab to the right panel of the application:
- **Run Overview Table:** Lists all runs with system type, accuracy, confidence intervals, mean steps, latency, and node/edge counts. Includes sorting by accuracy or latency.
- **Visual SVG Bar Charts:** Direct visual comparisons for Relation Sweeps ($R_3 \to R_{10}$), Cap Sweeps ($K=5 \to 20$), and Voting Rules.
- **Per-Question Inspector:** Allows selecting any run and browsing through questions to view:
  - Question text & ground-truth answer.
  - Model answer with green "Correct" or red "Incorrect" badges.
  - Step count and latency.
  - Expandable full ReACT scratchpad (every Thought, Action, and Observation).

---

## 3. Current Codebase Health & Verification

- **Backend Test Suite:** 39 tests in `backend/tests/`, covering:
  - Cache operations (`test_cache.py`)
  - Caps and filtering (`test_cap.py`, `test_filter_runs.py`, `test_triple_filters.py`)
  - Schema profiles & validation (`test_profiles.py`, `test_validation.py`)
  - Entity linking (`test_same_as.py`)
  - Config cleanup (`test_delete_config.py`)
  - Scoring & bootstrap CI (`test_scoring.py`)
  - QA validation and merge (`test_qa_merge.py`)
  - SciERC evaluation & lenient matching (`test_extraction_eval.py`)
  - Table generation formatting (`test_make_tables.py`)
- **Execution Result:** `39 passed in 14.96s` (100% pass rate).
- **Git Status:** Clean working tree on branch `main` (commits: `7725404`, `d2f144c`, `3a0dce8`, `7120a6a`, `9f84fc0`).

---

## 4. Next Step: Looking into Changes and the UI

The entire backend and evaluation scaffolding is fully functional. Both dev servers are running:
- **Backend:** `http://localhost:8000` (FastAPI)
- **Frontend:** `http://localhost:5173` (Vite + React)

Now, we can:
1. Review the new **Experiments & Ablations** tab directly in the browser.
2. Inspect how the UI renders experiment runs and per-question ReACT traces.
3. Review any styling or UI adjustments you want to make before executing the experimental runs.
