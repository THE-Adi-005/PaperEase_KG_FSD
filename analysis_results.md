# KG Paper Assistant — Deep Analysis

## 1. Main Goal

The project's goal is to **replace traditional "chunk-and-search" RAG with a Knowledge-Graph-grounded reasoning system for research paper QA**.

Conventional RAG splits PDF text into chunks, embeds them, and retrieves the top-k most similar chunks for an LLM to summarize. This fails on:
- **Multi-hop questions** — "Which method achieved the highest accuracy on MMLU?" requires comparing data scattered across multiple sections/tables.
- **Cross-paper comparisons** — "How does Paper A's method compare to Paper B's?" requires linking entities across documents.
- **Hallucination** — the LLM can fabricate numbers or confuse which paper reported what.

This project solves all three by:
1. **Constructing a structured Knowledge Graph** (Neo4j) from uploaded PDFs, where entities (Methods, Datasets, Metrics) and their relationships (ACHIEVES, EVALUATED_ON, USES_METHOD) are explicit, traceable nodes and edges.
2. **Using a ReACT Agent** that traverses this graph step-by-step with Cypher-backed tools instead of hallucinating from raw text.
3. **Lazy graph completion** — if the agent hits a dead-end at query time, it re-reads the source section, extracts the missing triple on the fly, and patches the graph before continuing.
4. **Cross-paper entity linking** via `SAME_AS` edges (cosine similarity on MiniLM embeddings, threshold ≥ 0.85).

**In one sentence:** The goal is to achieve **100% traceable, fact-grounded QA over academic papers** where every claim in the answer can be traced back to a specific node, edge, and source section in the graph.

---

## 2. Domain, Node Types & Relationship Design

### Domain: Academic / ML Research Papers

The system is purpose-built for **machine learning and NLP research papers** — the kind that contain benchmarks, evaluation tables, method descriptions, and citation networks.

### Node Labels (10 types)

Defined in [`neo4j_schema.py`](file:///C:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/models/neo4j_schema.py#L9-L20):

| Node Label | What it represents | Why it exists |
|---|---|---|
| `Paper` | The uploaded PDF itself | Root anchor — everything connects back here |
| `Author` | Paper authors | Attribution queries |
| `Section` | Individual sections of the paper | Stores raw text for lazy completion re-extraction |
| `Concept` | Theoretical ideas (attention, transformers) | Catch-all for abstract entities |
| `Method` | Algorithms, models, architectures (BERT, GPT) | Core entity for benchmark comparisons |
| `Dataset` | Datasets, benchmarks (SQuAD, MMLU) | Needed for "evaluated on what?" queries |
| `Metric` | Evaluation scores (F1=92.4, accuracy=88.1%) | Stores actual numeric results |
| `Figure` | Figures extracted from the PDF | Visual reference |
| `Table` | Tables extracted via pdfplumber | Structured data source |
| `Citation` | Referenced external works | Citation network |

### Relationship Types (16 seed types)

Defined in [`neo4j_schema.py`](file:///C:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/models/neo4j_schema.py#L23-L40):

| Relationship | Direction | Purpose |
|---|---|---|
| `AUTHORED_BY` | Paper → Author | Attribution |
| `CONTAINS_SECTION` | Paper → Section | Document structure |
| `DISCUSSES_CONCEPT` | Section → Concept | Topic linkage |
| `USES_METHOD` | Paper/Section → Method | Method usage |
| `REPORTS_METRIC` | Method/Table → Metric | Numeric results |
| `EVALUATED_ON` | Method → Dataset | Benchmark evaluation |
| `ACHIEVES` | Method → Metric (with value) | Performance claims |
| `COMPARES_TO` | Method → Method | Comparative analysis |
| `EXTENDS` | Method → Method | Lineage/improvement |
| `CITES` | Paper → Citation | Reference network |
| `SAME_AS` | Concept ↔ Concept | Cross-paper entity resolution |
| `ILLUSTRATED_BY` | Section → Figure/Table | Visual reference |
| `PART_OF` | Section → Paper | Inverse navigation |
| `REFERENCES_FIGURE/TABLE` | Section → Figure/Table | In-text references |
| `BELONGS_TO` | Author → Paper | Inverse navigation |

### How Node/Relationship Count Is Determined During PDF Parsing

The number of nodes and relationships is **NOT pre-configured** — it's **emergent** from the PDF content itself. Here's the pipeline:

#### Step 1 — Structural Parsing
The PDF is parsed by `unstructured` (text sections) and `pdfplumber` (tables). This creates a fixed set of structural nodes:
- 1 `Paper` node
- N `Author` nodes (from the paper header)
- M `Section` nodes (one per detected section)
- K `Table` + `Figure` nodes

#### Step 2 — LLM-driven Triple Extraction
Each section's text (truncated to 3,000 chars) is sent to the LLM with the extraction prompt in [`llm_client.py:L67-L105`](file:///C:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/services/llm_client.py#L67-L105). The LLM returns a JSON array of `{head, head_type, relation, tail, tail_type}` triples. **The LLM decides** how many triples each section produces — typically 3-15 per section depending on information density.

#### Step 3 — Self-Consistency Filtering
The extraction runs **2 times** (`EXTRACTION_RUNS=2` in [`config.py:L29`](file:///C:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/config.py#L29)) at `temperature=0.6`. Only triples that appear in **≥50% of runs** (majority vote) survive. This **reduces** the final node/edge count by filtering hallucinated extractions.

#### Step 4 — Table-to-Triple Conversion  
The [`table_parser.py`](file:///C:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/utils/table_parser.py#L60-L136) converts each table row into triples deterministically:
- Row entity → `REPORTS_METRIC` → `{header}={value}` (for numeric columns)
- Row entity → `EVALUATED_ON` → dataset name (for dataset columns)

#### Step 5 — Cross-Paper Linking
[`embeddings.py`](file:///C:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/services/embeddings.py#L40-L103) embeds all `Concept`, `Method`, and `Dataset` node names using `all-MiniLM-L6-v2` and creates `SAME_AS` edges for pairs with cosine similarity ≥ 0.85.

**In summary:** A typical 10-section ML paper might produce ~1 Paper + 3 Authors + 10 Sections + 2 Tables + 40-80 entity nodes + 60-120 relationship edges. The count is driven entirely by the paper's content density.

---

## 3. Domain Specificity, Grounding, and Edge Cases

### 3a. Grounded Reasoning for Choosing Node Types and Relationship Types

The schema is **specifically designed for the ML/NLP research paper domain**. Here's why each choice is grounded:

**Why these specific node types?**
Every ML paper follows a predictable structure: *Authors* propose a *Method*, evaluate it on *Datasets*, report *Metrics*, discuss *Concepts*, and *Cite* prior work. The 10 node labels directly mirror this ontology. The `Concept` label acts as a catch-all for anything the LLM extracts that doesn't fit the other categories.

**Why these specific relationship types?**
The 8 relation types given to the LLM in the extraction prompt ([`llm_client.py:L72-L79`](file:///C:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/services/llm_client.py#L72-L79)) are chosen because they represent **the core factual claims in ML papers**:

| Relation | What factual claim it captures | Example |
|---|---|---|
| `USES_METHOD` | "We use X" | Paper → Transformer |
| `EVALUATED_ON` | "We test on X" | BERT → SQuAD |
| `ACHIEVES` | "We get X score" | BERT → F1=92.4 |
| `REPORTS_METRIC` | "Table shows X" | GPT-2 → Perplexity=35.2 |
| `COMPARES_TO` | "We compare against X" | Our Method → Baseline |
| `EXTENDS` | "We build on X" | RoBERTa → BERT |
| `DISCUSSES_CONCEPT` | "Section talks about X" | Section 3 → Attention |
| `CITES` | "We reference X" | Paper → (Vaswani et al., 2017) |

This is **not a generic schema** — it's tuned for the question types researchers actually ask: "What accuracy did X get on Y?", "Which methods were compared?", "What does this paper build on?"

**Dynamic relation registration:** The system also supports dynamic relations — if the LLM produces a relation not in the seed list (e.g., `TRAINED_ON`, `OUTPERFORMS`), it's normalized to `UPPER_SNAKE_CASE` and registered on the fly via [`register_dynamic_relation()`](file:///C:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/models/neo4j_schema.py#L51-L54). This makes the schema **additive, not rigid**.

---

### 3b. What Happens When You Change/Reduce/Increase Nodes and Relationships

#### Reducing nodes/relationships (sparser graph):

| Scenario | How to do it | Effect |
|---|---|---|
| Fewer extraction runs | Set `EXTRACTION_RUNS=1` | Self-consistency is disabled. More hallucinated triples survive → **noisier graph**. But the graph is denser. |
| Higher self-consistency threshold | Require >66% agreement instead of >50% | Fewer triples survive → **cleaner but sparser graph**. Agent hits dead-ends more often → triggers more lazy completions → higher latency. |
| Truncate section text more | Currently `section_text[:3000]` in the prompt | LLM sees less context → misses facts buried later in sections → fewer triples extracted. |
| Remove relation types from the prompt | e.g., drop `EXTENDS`, `COMPARES_TO` | The LLM won't extract those relationships → the agent **cannot answer lineage or comparison questions**. |
| Remove node types | e.g., drop `Dataset` from schema | All datasets get labeled `Concept` → EVALUATED_ON queries break because the agent can't filter by node type. |

**Net effect of reduction:** The agent relies on **lazy completion** ([`lazy_completion.py`](file:///C:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/services/lazy_completion.py)) as a safety net. When it searches for a node and gets "No nodes found", it triggers targeted re-extraction. So a sparser graph = more lazy completions = **slower but potentially still correct**. However, if the relation type itself was removed from the schema, lazy completion can't recover it.

#### Increasing nodes/relationships (denser graph):

| Scenario | How to do it | Effect |
|---|---|---|
| More extraction runs | Set `EXTRACTION_RUNS=3-5` | More robust self-consistency, but 2-3x slower ingestion. |
| Lower temperature | Change `EXTRACTION_TEMPERATURE` from 0.6 to 0.3 | More deterministic extractions → higher agreement → more triples pass the filter. |
| Remove the 3000-char truncation | Send full section text | More triples per section, but risk exceeding LLM context window. |
| Add more relation types | e.g., `OUTPERFORMS`, `TRAINED_ON`, `HYPERPARAMETER_OF` | Richer graph for niche questions, but the extraction prompt gets longer → LLM may get confused. |
| Lower `SAME_AS_THRESHOLD` | From 0.85 to 0.7 | More cross-paper links, but also more **false positive** entity merges (e.g., linking "BERT" and "RoBERTa" as SAME_AS when they're distinct). |

**Net effect of increase:** Denser graph = agent finds answers faster (fewer steps, fewer lazy completions), but ingestion is slower and there's higher risk of noise/hallucinated edges if self-consistency isn't strict enough.

> [!IMPORTANT]
> **The critical tradeoff is: graph density vs. graph quality.** The current settings (`2 runs`, `temp=0.6`, `threshold=0.85`) are a balanced middle ground. Moving in either direction has clear costs.

---

### 3c. What Happens When 2 Unrelated PDFs Are Given

Example: Upload a paper on "Transformer Architectures for NLP" and a paper on "Climate Change Modeling"

**During Ingestion:**
1. Each paper gets its own `Paper` node, `Section` nodes, and extracted entity nodes. These are **isolated subgraphs** within the same Neo4j database.
2. The `SAME_AS` linking step ([`embeddings.py:L40-L103`](file:///C:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/services/embeddings.py#L40-L103)) runs cosine similarity between entity names from Paper A and Paper B. For truly unrelated papers, **almost no entities will exceed the 0.85 threshold**, so effectively **no cross-paper links are created**.
3. Exception: Generic concepts like "accuracy", "neural network", or "optimization" might still get `SAME_AS` links because the names are identical or near-identical. This is a **false positive** but largely harmless — the agent can still filter by `source_paper_id` on each edge.

**During Querying:**
- If you ask a question about **one** paper (passing its `paper_id`), the agent filters searches to that paper's subgraph ([`neo4j_client.py:L296-L304`](file:///C:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/services/neo4j_client.py#L296-L304)). The other paper's data is invisible.
- If you ask a **comparison** question across both papers (e.g., "Compare the methods in Paper A and Paper B"), the agent will search both subgraphs but find **no meaningful connections** (no shared methods, datasets, or metrics). It will likely return: *"These papers discuss unrelated topics — Paper A covers X while Paper B covers Y."*
- The **provenance rule** in the agent prompt ([`agent.py:L48`](file:///C:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/services/agent.py#L48)) explicitly tells the agent to check `source_paper` fields and never misattribute facts across papers.

**Bottom line:** Unrelated PDFs coexist safely. The system **does not hallucinate connections** between them because:
1. `SAME_AS` threshold is high enough (0.85) to block false links between unrelated domains.
2. Every relationship edge carries `source_paper_id` for provenance.
3. The agent prompt has explicit instructions against cross-paper misattribution.

---

### 3d. Prompting Strategy — Specific, On-Point Guidance

The system uses **three distinct prompting strategies**, each tuned for a specific purpose:

#### 1. Extraction Prompt (Ingestion Time)
**Location:** [`llm_client.py:L67-L105`](file:///C:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/services/llm_client.py#L67-L105)

**Strategy: Constrained extraction with explicit schema**
```
"You are a knowledge graph extraction expert."
+ Exact list of 8 allowed RELATION TYPES
+ Exact list of 5 allowed ENTITY TYPES
+ 4 concrete RULES (factual only, include values, canonical names, independent triples)
+ 1 JSON output example with exact format
+ "Return ONLY the JSON array, no other text"
```

**Why it works:**
- The **closed relation set** prevents the LLM from inventing random relationship names. It funnels all extractions into the 8 types that the agent knows how to query.
- The **entity type list** ensures nodes get the right Neo4j label (Method vs Concept vs Dataset) so that the full-text index and type-filtered queries work.
- The **"canonical names" rule** prevents duplicate nodes (e.g., "the BERT model" vs "BERT").
- The **JSON-only output** constraint prevents free-text preambles that would break parsing.

**Temperature = 0.6** — deliberately higher than generation tasks. This is intentional: slightly varied extractions across the 2 self-consistency runs increase coverage (the LLM might catch different facts each time), while majority voting filters out the noise.

#### 2. Targeted Re-Extraction Prompt (Lazy Completion)
**Location:** [`llm_client.py:L118-L149`](file:///C:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/services/llm_client.py#L118-L149)

**Strategy: Query-focused, narrow extraction**
```
"Extract ONLY triples relevant to this specific query"
+ QUERY: {what the agent was looking for}
+ Same relation type list
+ Temperature = 0.3 (lower, more focused)
+ max_tokens = 1024 (shorter, just the missing facts)
```

**Why it works:**
- The original extraction might miss facts because the section was long or the fact was implicit. By telling the LLM **exactly what to look for**, the second pass is surgical.
- Lower temperature (0.3 vs 0.6) reduces creativity and hallucination since we're targeting a specific gap.
- Shorter max_tokens prevents the LLM from over-extracting irrelevant triples.

#### 3. Agent System Prompt (Query Time)
**Location:** [`agent.py:L30-L65`](file:///C:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/services/agent.py#L30-L65)

**Strategy: Strict ReACT format with tool descriptions and safety rules**
```
6 available tools with exact syntax
+ Strict format: "Thought: ... Action: ActionName[arg1, arg2]"
+ Safety rules:
  - "Copy metrics EXACTLY character-for-character"
  - "Always check source_paper field" (provenance)
  - "Cite specific facts from the graph"
+ Maximum 8 steps
```

**Critical prompting decisions:**
- The `PROVENANCE RULE` at line 48 is the single most important anti-hallucination measure. It forces the agent to check **which paper** a fact came from before citing it.
- The `MULTI_PAPER_PROMPT_ADDITION` ([`agent.py:L57-L65`](file:///C:/Users/Adithya%20R/FSD_project_MAIN/FSD_project/backend/app/services/agent.py#L57-L65)) is injected only for comparison queries and adds a **completeness checklist** — the agent must explicitly address every paper before calling `Finish`.
- The `InspectSection` tool (line 37) lets the agent **read raw section text** when graph traversal alone isn't enough — a fallback for nuanced questions that need exact wording from the paper.
- `max_steps=8` prevents infinite loops while giving enough room for multi-hop reasoning (typically 3-5 steps for simple questions, 6-8 for comparisons).

---

## Summary Table

| Question | Core Answer |
|---|---|
| **Main goal** | Replace vector-search RAG with KG-grounded agentic reasoning for traceable, fact-based academic paper QA |
| **Domain** | ML/NLP research papers. Node/relationship counts are emergent from LLM extraction + self-consistency filtering + table parsing |
| **Nodes/rels reduced** | Sparser graph → more lazy completions → slower but recoverable (unless the schema type itself is removed) |
| **Nodes/rels increased** | Denser graph → faster answers but slower ingestion + risk of noise |
| **Unrelated PDFs** | Isolated subgraphs, no false cross-links (0.85 threshold + provenance tags), agent won't misattribute |
| **Prompting strategy** | 3-layer design: constrained schema extraction (ingestion), query-focused re-extraction (lazy completion), strict ReACT with provenance rules (querying) |
