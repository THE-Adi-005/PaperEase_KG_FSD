# KG Paper Assistant: Completion Plan (handoff file)

Use this file when your coding-agent credits return. Work top to bottom. Items marked **YOU DO** need no agent and no credits.

---

## 0. How to use this file

1. Do section 3 now (no credits needed).
2. When credits return, paste the **context rules** (section 4.0) once per agent session, then paste one task prompt at a time (R1, R2, ...).
3. After each task, copy the agent's report back to me (the "send me" line under each task says what).
4. If credits are very limited, use the minimum-prompt path in section 6.

---

## 1. Current state (verified from your reports)

| Area | Status |
|---|---|
| Schema profiles R3/R5/R7/R10 (nested relation sets, same 5 entity types), voting fix (`min_votes`), type-signature and dynamic-relation filters, deterministic cap | Done and tested |
| `config_id` namespacing, `norm_name` merge key, metric value properties, confidence on edges | Done and tested |
| Neo4j migration (1,252 entity nodes, 1,666 edges, 12 duplicate groups merged, 0 edges lost) | Done and verified |
| Extraction cache (SQLite `results/cache.sqlite`): R7 = 5 runs, R3 = 3 runs, R10 = 3 runs, 148 sections | Complete, but see section 2 (empties need checking) |
| 16 ablation configs in `configs/` | Written, **not yet built into Neo4j** |
| `eval/build_config.py`, `eval/extract_cache.py`, `eval/clean_empty.py`, `eval/cache_status.py`, `eval/corpus.py`, `eval/generic_report.py` | Done |
| Table cache (`table_triples`) | **Empty, and it will stay empty** (see 2.3) |
| `eval/corpus.json` | **Contains an error** (see 2.4), fix in R1 |
| Scoring module, QA runner, RAG baseline, SciERC extraction/eval | **Not written yet** |
| QA set (questions with gold answers) | **Not written yet** |
| Results tables, plots, Experiments tab in the UI | **Not written yet** |
| Paper | Not started |

---

## 2. Findings so far (use these in the paper, and fix what is flagged)

### 2.1 Bugs found in the original analysis doc (report them as "issues found and fixed")
- Self-consistency with 2 runs and a ">= 50%" rule kept any triple seen once, so it was a union, not a filter. Fixed with `min_votes(n, fraction) = max(1, ceil(fraction*n - 1e-9))`.
- The relation lists were defined in 3 places and dynamic relations were unconstrained. Now a single schema profile.
- 35 junk relation types had been created by dynamic registration (for example `COMPARSES_TO`, `IS`, `COUNT`), almost all with a single edge. This is the evidence for the dynamic-relations ablation.
- Metric values stored inside node names (`F1=92.4`): 484 of 1,252 nodes (39%) are Metric nodes; only 154 of them had a parseable value.
- Failed LLM calls were cached as empty extractions (fixed: failures are never cached; a genuinely empty `[]` is cached).

### 2.2 Empty extractions are a result, not only a nuisance
Before cleanup, the empty rate per profile was R3 60%, R10 36%, R7 36%. A smaller relation set means fewer extracted triples. The model really returned `[]` for the two sections that were checked. **Open question:** after cleanup and re-extraction, the report says there are 0 empty rows, which contradicts the earlier deterministic empties (53/52/53/53 per run). Verify with the script in section 3.3 before you trust any extraction result.

### 2.3 The table parser fails on these PDFs
`pdfplumber` finds 0 tables in GPT and XLNet, unusable header rows in the statistics paper, and prompt boxes (not metric tables) in the patent PDF. The 168 `REPORTS_METRIC` edges in the default graph came from old LLM extraction (164) and fake demo papers (4). Decision: drop the table arm and the table-derived questions. Report the parser failing on arXiv-style PDFs as a limitation.

### 2.4 The corpus is small and partly junk
- Real papers in Neo4j: GPT (`1e6c7c12`), XLNet (`b7f9484b`), a statistics paper (`f7d92af0`, off-domain), and one patent paper (`680a27f3`, off-domain). The other four patent files in `backend/uploads` are byte-identical copies that were never ingested.
- 3 synthetic demo papers (`demo_*`) must be excluded from all evaluation.
- **Fix `corpus.json`** (it wrongly lists `393bae80` and excludes `680a27f3`). Correct content:
```json
{
  "core": ["1e6c7c12", "b7f9484b"],
  "ood": ["f7d92af0", "680a27f3"],
  "excluded": ["demo_attention_2017", "demo_bert_2018", "demo_gpt3_2020"],
  "duplicates_on_disk_only": ["393bae80", "4cf686b3", "53b847cd", "af45b3fe"],
  "note": "core=ML/NLP papers, ood=off-domain probes, excluded=synthetic demo papers"
}
```
- Cross-paper structure (excluding demo papers): 16 shared entity nodes. 5 of them are generic (`METHOD`, `model`, `models`, `our approach`, `our method`). Real bridges: `Transformer`, `RACE`, `GLUE`, `SQuAD`, `Wikipedia`. Build cross-paper questions around these.
- Plan: add 4 ML papers (Attention Is All You Need 1706.03762, BERT 1810.04805, RoBERTa 1907.11692, ALBERT 1909.11942). Ingest them structurally only (no extraction, no entity nodes), then extract through the cache.

### 2.5 Other measured facts
- Generic entities: 11 of 1,252 nodes (0.9%) in the default graph, but about a third of shared nodes once demo papers are excluded. `cfg_nogeneric` is a meaningful arm.
- `F1=93.2` is a Metric node shared by two papers: scores get linked across papers because the value is in the node name. Limitation, and future work: paper-scoped result nodes.
- Throughput: 9 calls/min in the first measurement, 39 calls/min later (suspiciously fast, check that outputs are not truncated or empty).

---

## 3. What you can do NOW without credits

### 3.1 Downloads
- Create `eval_papers/` in the repo root (next to `backend/`) and put 4 PDFs in it: arXiv 1706.03762, 1810.04805, 1907.11692, 1909.11942.
- Save the SciERC test split as `backend/data/scierc/test.json` (SciERC, Luan et al. 2018, JSON lines). If you cannot find it, tell me and we will decide on an alternative.

### 3.2 Fix `corpus.json` by hand
Paste the JSON from 2.4 into `eval/corpus.json`. Then run `python -m pytest tests -q`. If `tests/test_corpus.py` fails because it still expects the old lists, tell me; it is a one-line test update.

### 3.3 Check the extraction cache yourself
Save this as `check_cache.py` in the repo root and run `python check_cache.py` from the repo root. Send me the output.
```python
import sqlite3, json, statistics, collections

con = sqlite3.connect("results/cache.sqlite")
q = "select prompt_profile, run_idx, paper_id, section_id, raw_json from extractions"
stats = collections.defaultdict(lambda: [0, 0, []])
by_sec = collections.defaultdict(lambda: collections.defaultdict(list))
for prof, run, pid, sid, raw in con.execute(q):
    n = len(json.loads(raw))
    s = stats[(prof, run)]
    s[0] += 1
    if n == 0:
        s[1] += 1
    else:
        s[2].append(n)
    by_sec[prof][(pid, sid)].append(n == 0)

print("profile run total empty mean_triples_when_nonempty")
for (prof, run), (tot, emp, ns) in sorted(stats.items()):
    print(prof, run, tot, emp, round(statistics.mean(ns), 2) if ns else 0)
for prof, d in by_sec.items():
    all_e = sum(1 for v in d.values() if all(v))
    some = sum(1 for v in d.values() if any(v) and not all(v))
    print(prof, "sections empty in ALL runs:", all_e, "| in SOME runs:", some, "| of", len(d))
```

### 3.4 Write the QA questions (the most important manual step)
Questions can be written from the PDFs alone. You do not need Neo4j for this. Create `eval/qa_manual.json` as a list of items with this schema:
```json
{
  "id": "q01",
  "type": "lookup",
  "source": "manual",
  "paper_ids": ["1e6c7c12"],
  "question": "On which datasets did the paper evaluate the model?",
  "gold_answers": ["RACE"],
  "answerable": true,
  "verified": true
}
```
Target about 40 questions on the core papers (use the paper id from Neo4j, or the PDF filename prefix):

| Type | Count | Notes |
|---|---|---|
| `lookup` | 10 | One fact in one paper: dataset used, score on a benchmark |
| `multihop` | 8 | Method to dataset to score ("which dataset did X evaluate on, and what did it score?") |
| `aggregation` | 6 | "Which method scored highest on dataset D in paper P?" |
| `cross_paper` | 8 | Use bridge entities (GLUE, RACE, SQuAD, Transformer) and compare two papers |
| `unanswerable` | 8 | Plausible questions whose answer is not in the papers (`answerable: false`, `gold_answers: []`) |

Rules: copy numbers exactly from the PDFs, write the page or table in an extra `"evidence"` field for yourself, keep gold answers short (a number, a name), and write the cross-paper questions so each one names both papers. After the 4 new papers are ingested you can add questions on them.

### 3.5 Start the paper
You can write Introduction, Related Work, System Description, and Experimental Setup now, using your project description doc. Results sections stay as placeholders until the experiments run. A starter skeleton is in Appendix B.

---

## 4. Work for the coding agent (when credits return)

### 4.0 Context rules (paste once at the start of each agent session)
````text
CONTEXT RULES (apply to every task): FastAPI + Neo4j + React project "KG Paper Assistant". The ablation framework lives in eval/, configs/, results/. Smallest possible diffs; no refactors; defaults unchanged; never modify or delete data with config_id='default' in Neo4j; no new heavy dependencies without asking; Windows PowerShell 5.1 (use ; not &&); commit after each task (git add -A; git commit -m "<task id>"); if the code differs from an assumption, adapt minimally and tell me; at the end report files changed (one line each), assumptions, and the output of `python -m pytest tests -q`. Do not stop background jobs unless told. Reply "understood" and wait.
````

### R1: corpus fix, cache verification, stoplist, structural ingestion of new papers
Skip the sub-steps you already did by hand (corpus.json, check_cache.py).
````text
TASK R1. Do the steps in order; no LLM jobs.
1. Fix eval/corpus.json to: core ["1e6c7c12","b7f9484b"], ood ["f7d92af0","680a27f3"], excluded ["demo_attention_2017","demo_bert_2018","demo_gpt3_2020"], duplicates_on_disk_only ["393bae80","4cf686b3","53b847cd","af45b3fe"] (not used by any code). Update tests/test_corpus.py (eval list has no duplicates and no excluded ids).
2. Add "models","the models","our models" to GENERIC_ENTITIES in app/triple_filters.py and extend the is_generic test.
3. Create eval/ingest_structural.py (CLI): --pdf-dir (default eval_papers), --apply (dry-run by default). For each PDF: sha256, paper id = first 8 hex chars; skip with a message if a Paper with that id already exists; parse with the same PDF parser and metadata logic the upload route uses; write Paper, Author, Section (and Figure/Table if the parser creates them) nodes via neo4j_service.merge_paper; NO triple extraction, NO entity nodes, NO embeddings, NO SAME_AS, NO LLM calls. Dry-run prints per PDF: id, title, number of sections, number of sections >= 50 chars, total characters. With --apply also add the new ids to the "core" list in eval/corpus.json. If the pdf dir does not exist or has no PDFs, stop and tell me.
4. Run the dry run, paste it, then run with --apply and paste the output. Then re-run a paper audit (id, title, sections, attributed entities and semantic edges for config 'default') and confirm these counts are unchanged: 1e6c7c12 349 entities / 344 edges; 680a27f3 178 / 254; b7f9484b 362 / 419; f7d92af0 379 / 402.
5. In eval/build_config.py and (if present) eval/rag_baseline.py and eval/run_qa.py, make papers 'all' resolve to get_eval_papers().
Commit "R1". Report.
````
**Send me:** the dry-run and apply output, the audit table, and the pytest line.

### R2: scoring module (code supplied; no agent needed)
Create `eval/scoring.py` and `tests/test_scoring.py` by copying Appendix A. Run `python -m pytest tests -q`. If you want the agent to do it instead, paste: "Create eval/scoring.py and tests/test_scoring.py exactly as in the attached code" together with the Appendix A code.

### R3: KG agent runner, RAG baseline, QA runner
````text
TASK R3. Do not run any QA or extraction job; code and unit tests only. Keep any change to llm_client.py strictly backward compatible (do not touch extract_triples' raise_on_error, _parse_json_array, or eval/extract_cache.py). Run pytest after every item.
R3.1 Find the ReACT agent entry point used by the QA API route. If it is only a streaming generator, add a non-streaming wrapper `async def run_agent_eval(question, paper_ids, config_id, max_steps, lazy_completion: bool, persist_lazy: bool=False, temperature=0.0) -> dict` returning {answer, steps, observations (list[str]), n_lazy_triggers, trace}. The existing API behavior must not change. Thread config_id and paper_ids into every graph tool call (retrieve_node, neighbor_check, node_degree, node_feature, subgraph). If lazy_completion is False the agent must never call lazy completion; if persist_lazy is False, lazy completion must return its extracted triples as a text observation and MUST NOT write to Neo4j. Report which functions you changed and how lazy completion is triggered.
R3.2 Create eval/rag_baseline.py: builds an index of all Section texts for the evaluation papers (Neo4j read-only), chunks of ~300 words with 50 overlap, embedded with the same sentence-transformers model used in embeddings.py, cached in results/rag_index.pkl. answer_rag(question, paper_ids, k=5) -> {answer, contexts, latency}: top-k chunks restricted to paper_ids, then the SAME Ollama Qwen model at temperature 0 with this prompt: "Answer the question using ONLY the context. Be concise. If the answer is not in the context, reply exactly: Not found in the papers." Use the existing llm_client (add an optional temperature argument; default keeps old behavior).
R3.3 Create eval/run_qa.py (CLI): --system kg|rag, --config <config_id> (kg only), --lazy on|off (default off), --qa eval/qa_set.json, --limit N (stable shuffle, seed 0, stratified by type if possible), --max-steps 6. system_id = "rag" or f"kg_{config}_{'lazy' if lazy else 'nolazy'}". For each question call the system, then compute with eval/scoring.py: correct, abstained, evidence_hit; record steps, latency_s, n_lazy_triggers, answer, trace. Append to results/qa/<system_id>/predictions.jsonl after EVERY question; resumable. At the end write results/qa/<system_id>/metrics.json with: n, accuracy with bootstrap CI, accuracy by type, accuracy by source, abstain rate on unanswerable, false-abstain rate on answerable, evidence_hit rate, mean steps, mean latency, mean lazy triggers. Update one row for system_id in results/all_runs.csv (columns: system_id, system, config, lazy, n, acc, acc_lo, acc_hi, acc_table, acc_manual, abstain_rate_unanswerable, evidence_hit, mean_steps, mean_latency) and for kg systems merge in total_nodes, total_edges, avg_degree, graph_density from results/<config>/graph_stats.json if it exists. Print a one-line summary.
Commit "R3". Report.
````
**Send me:** which agent function was changed, how lazy completion is triggered, files changed, pytest line.

### R4: SciERC extraction benchmark
````text
TASK R4. The file backend/data/scierc/test.json should exist; if not, stop and tell me. First inspect its format and print ONE example doc. Code and unit tests only; do not run scierc_extract or extraction_eval.
R4.1 Create eval/scierc_extract.py (CLI): --profile R3|R7|R10 --runs N --n 40. Take the first n documents with at least 3 annotated entities (stable order). Section text = abstract (join tokens of all sentences). paper_id="scierc", section_id=doc_key. Call llm_client.extract_triples with the explicit profile, raise_on_error=True, the same temperature and truncation as eval/extract_cache.py; store raw runs in the same SQLite cache (resumable, never cache failures). No Neo4j.
R4.2 Create eval/extraction_eval.py: `python -m eval.extraction_eval configs/cfg_base.yaml ...`. For each config: load cached scierc runs for its prompt_profile and runs value, apply filter_runs with the config's vote_fraction, cap, enforce_signatures, allow_dynamic, relation_subset and drop_generic (same fields as eval/build_config.py), then score against SciERC gold:
 - Entity mapping: Method->Method, Metric->Metric, Material->Dataset, Task->Concept, OtherScientificTerm->Concept, Generic->ignored. Predicted entities = heads and tails of kept triples. Lenient match: normalized strings equal, or one contains the other and token Jaccard >= 0.5. Report entity precision/recall/F1 (type-agnostic and type-aware).
 - Relation-agnostic pair score: a predicted triple matches a gold relation if its two endpoints lenient-match the two gold argument spans in either order; ignore relation labels. Report pair P/R/F1. State in the docstring that this is a proxy because SciERC relation semantics differ.
 - Also report triples_per_doc and distinct relation types used.
Write results/<config_id>/extraction_metrics.json and add columns ent_f1, ent_p, ent_r, pair_f1, pair_p, pair_r, triples_per_doc to a row for system_id f"extract_{config_id}" in results/all_runs.csv. Add pure-function unit tests for the lenient matcher and for P/R/F1.
Commit "R4". Report.
````
**Send me:** the printed SciERC example doc, files changed, pytest line.

---

## 5. Experiments you run yourself (plain commands, no agent needed)

Open PowerShell in the repo root, activate the venv (`backend\venv\Scripts\Activate.ps1`), keep the laptop plugged in with sleep disabled, and start Ollama in a separate window with `$env:OLLAMA_NUM_PARALLEL=2; ollama serve`. **Run one GPU job at a time.** Every extraction command is resumable: if it stops, run the same command again.

### 5.1 Find the ids of the new papers
After R1 `--apply`, `python -m eval.corpus` is not guaranteed to print them; open `eval/corpus.json` and read the "core" list. Call the 4 new ids `NEW1,NEW2,NEW3,NEW4` below.

### 5.2 Extraction for the new papers, then SciERC (GPU, hours)
```text
python -m eval.extract_cache --profile R7 --runs 5 --papers NEW1,NEW2,NEW3,NEW4
python -m eval.extract_cache --profile R3 --runs 3 --papers NEW1,NEW2,NEW3,NEW4
python -m eval.extract_cache --profile R10 --runs 3 --papers NEW1,NEW2,NEW3,NEW4
python -m eval.scierc_extract --profile R7 --runs 5 --n 40
python -m eval.scierc_extract --profile R3 --runs 3 --n 40
python -m eval.scierc_extract --profile R10 --runs 3 --n 40
python -m eval.cache_status
```
Expected volume: about 4 papers x 35 sections per profile, so about 700 calls for R7 and 420 for each of the others, plus about 800 SciERC calls. At 9 to 39 calls/min this is 1 to 3 hours.

### 5.3 Extraction metrics for all configs (CPU, minutes)
```text
python -m eval.extraction_eval configs/cfg_base.yaml configs/cfg_r3.yaml configs/cfg_r5.yaml configs/cfg_r10.yaml configs/cfg_v_run1.yaml configs/cfg_v_union.yaml configs/cfg_v_unan.yaml configs/cfg_k5.yaml configs/cfg_k10.yaml configs/cfg_k20.yaml configs/cfg_sig_on.yaml configs/cfg_dyn_on.yaml configs/cfg_nogeneric.yaml
```
(The three `cfg_sa_*` arms only change `SAME_AS` linking, so they have no extraction metric.)

### 5.4 Build every config into Neo4j (CPU and database, about 10 minutes each)
Take a fresh Neo4j dump before this step. Each build deletes and recreates only its own `config_id`.
```text
python -m eval.build_config configs/cfg_base.yaml
python -m eval.build_config configs/cfg_r3.yaml
python -m eval.build_config configs/cfg_r5.yaml
python -m eval.build_config configs/cfg_r10.yaml
python -m eval.build_config configs/cfg_v_run1.yaml
python -m eval.build_config configs/cfg_v_union.yaml
python -m eval.build_config configs/cfg_v_unan.yaml
python -m eval.build_config configs/cfg_sa_off.yaml
python -m eval.build_config configs/cfg_sa_070.yaml
python -m eval.build_config configs/cfg_sa_090.yaml
python -m eval.build_config configs/cfg_k5.yaml
python -m eval.build_config configs/cfg_k10.yaml
python -m eval.build_config configs/cfg_k20.yaml
python -m eval.build_config configs/cfg_sig_on.yaml
python -m eval.build_config configs/cfg_dyn_on.yaml
python -m eval.build_config configs/cfg_nogeneric.yaml
```
Each build writes `results/<config_id>/graph_stats.json`. Check that nodes and edges differ across configs (if every config shows the same counts, the config values are not being applied; tell me).

### 5.5 QA runs, in priority order (GPU; roughly 6 LLM calls per question)
Only after `eval/qa_set.json` exists (section 6, step QA-merge). Priority order, most important first:
```text
python -m eval.run_qa --system rag
python -m eval.run_qa --system kg --config cfg_base --lazy off
python -m eval.run_qa --system kg --config cfg_base --lazy on
python -m eval.run_qa --system kg --config cfg_r3 --lazy off
python -m eval.run_qa --system kg --config cfg_r5 --lazy off
python -m eval.run_qa --system kg --config cfg_r10 --lazy off
python -m eval.run_qa --system kg --config cfg_v_run1 --lazy off
python -m eval.run_qa --system kg --config cfg_v_union --lazy off
python -m eval.run_qa --system kg --config cfg_v_unan --lazy off
python -m eval.run_qa --system kg --config cfg_sa_off --lazy off
python -m eval.run_qa --system kg --config cfg_sa_090 --lazy off
python -m eval.run_qa --system kg --config cfg_nogeneric --lazy off
python -m eval.run_qa --system kg --config cfg_k5 --lazy off
python -m eval.run_qa --system kg --config cfg_k10 --lazy off
python -m eval.run_qa --system kg --config cfg_sig_on --lazy off
python -m eval.run_qa --system kg --config cfg_dyn_on --lazy off
```
If time is short add `--limit 30` to everything after the first twelve lines. Bonus arm at no build cost: `--config default` (the legacy graph before the experiment framework).

---

## 6. Remaining agent tasks and minimum-prompt path

### QA-merge (small agent task)
````text
TASK QA-merge. Create eval/qa_merge.py: reads eval/qa_manual.json (and, if it exists, eval/qa_drafts.json), keeps ONLY items with verified:true, a non-empty question, and (gold_answers non-empty or answerable false); validates the schema {id, type in [lookup, multihop, aggregation, cross_paper, unanswerable], source, paper_ids, question, gold_answers, answerable}; checks that every paper id exists in eval/corpus.json (core or ood) and that ids are unique; writes eval/qa_set.json and prints counts by type and by source. Add a unit test with a tiny temporary file. Commit "QA-merge". Report.
````
You can also write this script by hand; it is about 40 lines.

### P4: tables, plots, API, Experiments tab
````text
TASK P4. Do not run any LLM job.
P4.1 Create eval/make_tables.py: reads results/all_runs.csv and writes LaTeX tables (booktabs) and PNG plots into paper_assets/. Tables: (a) main comparison: rag, kg_cfg_base_nolazy, kg_cfg_base_lazy (acc with CI, acc by type, abstain rate on unanswerable, evidence_hit, steps, latency); (b) schema sweep cfg_r3/r5/base/r10: nodes, edges, density, ent_f1, pair_f1, triples_per_doc, acc; (c) voting sweep cfg_v_run1/cfg_v_union/cfg_base/cfg_v_unan; (d) cap sweep cfg_k5/k10/k20/base; (e) SAME_AS sweep cfg_sa_off/070/base/090 (cross-paper acc, same_as edge count); (f) constraints: cfg_sig_on, cfg_dyn_on, cfg_nogeneric vs base. Plots (matplotlib; install it if missing and tell me): accuracy vs relation count; accuracy vs cap K; extraction F1 vs vote threshold; nodes/edges vs F1 trade-off; each with error bars from acc_lo/acc_hi where available. Missing rows must show "--", never crash.
P4.2 API: add a router experiments.py: GET /api/experiments (all rows of all_runs.csv), GET /api/experiments/{system_id} (metrics.json + graph_stats.json + extraction_metrics.json when present), GET /api/experiments/{system_id}/predictions?limit=50. Register it in the existing app. Read-only.
P4.3 Frontend: add an "Experiments" tab to the existing React app: a table of all runs (sortable), line or bar charts for accuracy vs relation count, cap K and vote threshold (use the charting approach already in the project; if none, plain SVG), a graph-stats card per config, and a per-question comparison view for two selected systems (question, gold, each answer with correct/incorrect, steps, expandable trace; link to the Cytoscape subgraph view if one exists). Keep it minimal.
P4.4 Unit-test the pure parts of make_tables.py (CSV parsing and LaTeX row formatting).
Commit "P4". Report files changed and how to start everything.
````

### Minimum-prompt path (if credits are very limited)
Do R1, R3, R4, QA-merge and P4 in that order (5 prompts), plus about 2 fix rounds. Write R2 and QA-merge by hand (or paste them into one prompt with R3), and run section 5 yourself. Without the UI task (P4.2 and P4.3), you still have all results and LaTeX tables; the UI then needs screenshots of the existing interface plus the plots.

---

## 7. Paper outline and how to frame the claims

**Title idea:** Schema size and graph density in knowledge-graph question answering over research papers: an empirical study.

**Contributions (claim only these):**
1. A schema-constrained, vote-filtered triple extraction pipeline with explicit size knobs (relation-set size, per-section cap, vote threshold, linking threshold).
2. An empirical study of how those knobs change graph size and answer accuracy against a vector-RAG baseline.
3. Findings on pitfalls: a union-in-disguise self-consistency rule, dynamic relation inflation, metric-value-in-node-name, generic entities, empty extractions.

**Sections:** Introduction, Related Work (GraphRAG, scientific IE such as SciERC/SciREX, ReAct), System, Experimental Setup (corpus, QA set, SciERC subset, systems, metrics), Results (main comparison, then one subsection per sweep), Analysis (error analysis, trace case study, cross-paper links and generic entities), Limitations, Conclusion.

**Where each result goes:** Table (a) is the main result; the schema sweep answers your sir's question "what happens when relations increase or decrease"; the cap sweep answers it for nodes; the voting table shows the union bug effect.

**Do not claim:**
- "100% traceable" (say: every answer cites graph facts with their source section).
- "No hallucinated connections" (say: measured abstention rate on unanswerable questions).
- Any generalization beyond a small corpus of ML/NLP papers; state the corpus size and that n is small, with bootstrap intervals.
- Strong claims from SciERC (it is a proxy: relation labels are ignored in the pair score).

**Limitations to state:** small corpus, Qwen 2.5 7B Q4 only, rule-based answer matching (substring and numeric tolerance), manual gold annotations by one person, table parser failure, metric value inside the node name, lazy completion not persisted in evaluation.

---

## 8. Risks and checks

| Risk | Check |
|---|---|
| Cache empties are deterministic and the claimed "0 empty rows" is wrong | Run `check_cache.py` (3.3) before trusting extraction results |
| Every config produces the same graph | Compare `graph_stats.json` across configs after builds; investigate if identical |
| Lazy completion writes into the graph during evaluation | Confirm `persist_lazy=False` in R3.1 and that node counts do not change after a QA run |
| New papers added only to `corpus.json` but not extracted | `python -m eval.cache_status` must show about 148 + new sections for each profile |
| GPU shared between jobs | One GPU job at a time; do not use the app while a queue runs |
| Substring answer matching gives false positives on short numeric golds | Keep gold answers specific; manually review 20% of predictions |
| Small n | Always report bootstrap CIs; avoid ranking arms whose intervals overlap |

---

## 9. What to bring back to me when credits return

1. Output of `check_cache.py` (3.3).
2. The R1 report (dry run, apply, audit table, pytest).
3. R3 report (agent function changed, how lazy completion is triggered).
4. R4 report (SciERC example doc).
5. Your `qa_set.json` counts by type.
6. `results/all_runs.csv` (or the first rows) after the experiments.

I will review each one, tell you what to fix, then help write the results sections from the CSV.

---

## Appendix A: `eval/scoring.py` and `tests/test_scoring.py`

`eval/scoring.py`
```python
import random
import re

_ABSTAIN = [
    "not found", "no information", "cannot find", "can't find", "not mentioned",
    "not available", "unable to find", "no data", "not reported",
    "do not contain", "does not contain",
]
_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s.%]", " ", s)
    return " ".join(s.split())


_ABSTAIN_N = [normalize(p) for p in _ABSTAIN]


def extract_numbers(s: str) -> list[float]:
    s = re.sub(r"(?<=\d),(?=\d{3})", "", s)
    return [float(x) for x in _NUM.findall(s)]


def is_abstain(answer: str) -> bool:
    n = normalize(answer)
    return any(p in n for p in _ABSTAIN_N)


def _to_float(s: str):
    try:
        return float(s.replace("%", "").strip())
    except ValueError:
        return None


def _matches(text: str, golds) -> bool:
    nt = normalize(text)
    nums = extract_numbers(text)
    for g in golds:
        g = str(g)
        gf = _to_float(g)
        if gf is not None:
            for c in (gf, gf * 100, gf / 100):
                tol = 0.05 if abs(c) >= 1 else 0.0005
                if any(abs(a - c) <= tol for a in nums):
                    return True
        else:
            gn = normalize(g)
            if gn and gn in nt:
                return True
    return False


def is_correct(answer: str, gold_answers, answerable: bool) -> bool:
    if not answerable:
        return is_abstain(answer)
    return (not is_abstain(answer)) and _matches(answer, gold_answers)


def evidence_hit(observations_text: str, gold_answers) -> bool:
    return _matches(observations_text, gold_answers)


def bootstrap_ci(values, n: int = 2000, seed: int = 0):
    vals = [float(v) for v in values]
    if not vals:
        return (0.0, 0.0, 0.0)
    rng = random.Random(seed)
    k = len(vals)
    means = sorted(sum(rng.choice(vals) for _ in range(k)) / k for _ in range(n))
    mean = sum(vals) / k
    low = min(means[int(0.025 * n)], mean)
    high = max(means[int(0.975 * n) - 1], mean)
    return (mean, low, high)
```

`tests/test_scoring.py`
```python
from eval.scoring import (bootstrap_ci, evidence_hit, extract_numbers,
                          is_abstain, is_correct, normalize)


def test_numeric_tolerance():
    assert is_correct("It scored 92.38%", ["92.4"], True)
    assert not is_correct("It scored 80.1", ["92.4"], True)


def test_percent_scaling():
    assert is_correct("The F1 is 92.4", ["0.924"], True)
    assert is_correct("The F1 is 0.924", ["92.4"], True)


def test_abstain_detection():
    assert is_abstain("Not found in the papers.")
    assert is_abstain("I can't find this information")
    assert not is_abstain("The answer is RACE")


def test_unanswerable_correct_only_when_abstaining():
    assert is_correct("Not found in the papers.", [], False)
    assert not is_correct("The answer is 5", [], False)


def test_substring_match_and_numbers():
    assert is_correct("The model was evaluated on RACE and GLUE", ["race"], True)
    assert extract_numbers("1,000 and 92.4%") == [1000.0, 92.4]
    assert normalize("  A  b ") == "a b"


def test_evidence_hit():
    assert evidence_hit("f1 = 92.4 on squad", ["92.4"])


def test_bootstrap_ci():
    m, lo, hi = bootstrap_ci([1, 0, 1, 1, 0, 1])
    assert lo <= m <= hi
```
Make sure `eval/__init__.py` exists and that pytest runs from the repo root or `backend/` with `eval` importable (the existing tests already import from `eval`, so the same setup works).

---

## Appendix B: Overleaf starter (targeted blocks)

Section skeleton:
```latex
\section{Introduction}
\section{Related Work}
\section{System}
\subsection{Graph construction}
\subsection{Agentic question answering}
\section{Experimental Setup}
\section{Results}
\subsection{Main comparison}
\subsection{Effect of schema size}
\subsection{Effect of per-section cap}
\subsection{Effect of voting threshold}
\subsection{Effect of entity linking}
\section{Analysis}
\section{Limitations}
\section{Conclusion}
```

Results table template (replace `--` after the experiments; `make_tables.py` will generate these automatically):
```latex
\begin{table}[t]
\centering
\caption{Question answering accuracy (\%) with 95\% bootstrap intervals. All systems use the same Qwen~2.5~7B model.}
\begin{tabular}{lcccc}
\toprule
System & Acc. & Cross-paper & Unanswerable ref. & Latency (s) \\
\midrule
Vector RAG            & -- & -- & -- & -- \\
KG agent (no lazy)    & -- & -- & -- & -- \\
KG agent (full)       & -- & -- & -- & -- \\
\bottomrule
\end{tabular}
\end{table}
```

Schema-sweep table template:
```latex
\begin{table}[t]
\centering
\caption{Effect of relation-set size (nested sets; entity types fixed).}
\begin{tabular}{lccccc}
\toprule
Profile & Nodes & Edges & Density & Pair F1 & QA acc. \\
\midrule
R3  & -- & -- & -- & -- & -- \\
R5  & -- & -- & -- & -- & -- \\
R7  & -- & -- & -- & -- & -- \\
R10 & -- & -- & -- & -- & -- \\
\bottomrule
\end{tabular}
\end{table}
```