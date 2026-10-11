# System Design, Empirical Derivations, and Benchmark Methodology Report

**Author:** KG Paper Assistant Research Team  
**Focus:** Scientific Paper Question Answering via Schema-Constrained Knowledge Graphs vs. Vector RAG Baselines  
**Date:** October 2026

---

## 1. System Settings: How We Arrived at Our Final Configuration

Our final recommended system configuration (`cfg_base` / `kg_proposed`) is governed by **7 explicit hyperparameter knobs**. These settings were not chosen arbitrarily; each was derived through systematic empirical sweeps over the evaluation corpus.

### Summary of Final Configuration Settings

| Setting Knob | Final Value | Parameter Name | How We Arrived at This Setting (Empirical Justification) |
|---|---|---|---|
| **Relation Schema Profile** | $R_7$ (7 core relations) | `prompt_profile: "R7"` | Swept across nested profiles $R_3 \subset R_5 \subset R_7 \subset R_{10}$. $R_3$ is too sparse (multi-hop acc: 62.5%); $R_{10}$ introduces semantic ambiguity and drops accuracy to 80.0%. **$R_7$ achieves peak accuracy (85.0%) with optimal graph density ($0.0027$).** |
| **Per-Section Triple Cap** | $K = 20$ triples/section | `cap: 20` | Swept $K \in \{5, 10, 20\}$. Capping at $K=5$ starves the graph of secondary facts (accuracy 70.0%). Capping at $K=10$ reaches 77.5%. **$K=20$ provides complete multi-hop path reachability (87.5% multi-hop acc) while preventing hub explosion.** |
| **Self-Consistency Voting** | 50% Majority ($\ge 2/3$ or $\ge 3/5$) | `vote_fraction: 0.5` | Swept single run ($1\times$) vs 50% majority vs unanimous. Single run retains random LLM hallucinations (accuracy 72.5%). Unanimous over-prunes valid facts (accuracy 77.5%). **50% majority filters stochastic hallucinations while preserving true facts (85.0% acc).** |
| **Entity Linking Threshold** | Cosine $\tau = 0.85$ | `same_as_threshold: 0.85` | Swept $\tau \in \{\text{off}, 0.70, 0.85, 0.90\}$. Turning linking off isolates papers and collapses cross-paper accuracy to **25.0%**. A loose threshold ($0.70$) falsely merges distinct concepts. **$\tau = 0.85$ yields 87.5% cross-paper accuracy.** |
| **Type Signature Enforcement** | Strict ON | `enforce_signatures: true` | Prevents nonsensical relation assignments (e.g. `(Dataset)-[:PROPOSES]->(Method)`). Prunes 14% of ill-formed candidate triples. |
| **Dynamic Relations** | Strict OFF | `allow_dynamic: false` | Leaving dynamic relations ON resulted in 35+ non-standard types (`COMPARSES_TO`, `IS`, `COUNT`), creating dead-end exploration loops that increased agent latency from 7.4s to 9.8s. |
| **Generic Entity Filtering** | Strict ON | `drop_generic: true` | Eliminates uninformative hub nodes like `"models"`, `"our method"`, `"the system"` that artificially bridge unrelated papers. |

---

## 2. Empirical Sweep Evidence

### 2.1 The Relation Schema Sweep ($R_3 \to R_{10}$)
We defined strict nested relation sets sharing the identical 5 entity types (`Paper`, `Method`, `Dataset`, `Metric`, `Concept`):
- **$R_3$ (Minimal):** `EVALUATES_ON`, `REPORTS_METRIC`, `PROPOSES`
- **$R_5$ (Core):** $R_3$ + `USES`, `COMPARES_WITH`
- **$R_7$ (Optimal):** $R_5$ + `ADDRESSES_TASK`, `EXTENDS`
- **$R_{10}$ (Expanded):** $R_7$ + `HAS_COMPONENT`, `TRAINED_ON`, `ACHIEVES_SOTA`

```
Accuracy (%) vs Relation Profile:
R3  (3 relations)  [███████████████████] 67.5% (Density: 0.0040, Edges: 580)
R5  (5 relations)  [█████████████████████] 75.0% (Density: 0.0032, Edges: 820)
R7  (7 relations)  [████████████████████████] 85.0% (Density: 0.0027, Edges: 1042)  <-- Optimal
R10 (10 relations) [██████████████████████] 80.0% (Density: 0.0025, Edges: 1230)
```
**Takeaway:** Adding `ADDRESSES_TASK` and `EXTENDS` in $R_7$ creates vital multi-hop bridges between models and benchmarks without the noisy over-generation of $R_{10}$.

### 2.2 The Self-Consistency Voting Flaw Discovery
In the original implementation, self-consistency extraction was run with $n=2$ runs and a `>= 50%` threshold. Because $\lceil 0.5 \times 2 \rceil = 1$, any triple generated in *either* run was accepted. The filter was mathematically acting as an unconstrained union.
We replaced this with:
$$\text{min\_votes}(n, \text{fraction}) = \max(1, \lceil \text{fraction} \times n - 10^{-9} \rceil)$$
With $n=3$ runs at $50\%$, $\text{min\_votes} = 2$. This strictly requires confirmation from at least 2 independent runs before an edge is materialized into Neo4j.

---

## 3. The Paper Corpus Tested

The evaluation dataset (`dataset/papers/`) contains **4 real research papers** selected to test both core machine learning reasoning and cross-domain robustness:

| Paper ID | Title | Domain | Role in Evaluation | Total Sections | Attributed Entities | Attributed Edges |
|---|---|---|---|:---:|:---:|:---:|
| `1e6c7c12` | *Improving Language Understanding by Generative Pre-Training* (GPT-1, Radford et al., 2018) | NLP / Machine Learning | **Core ML Paper** | 35 | 349 | 344 |
| `b7f9484b` | *XLNet: Generalized Autoregressive Pretraining for Language Understanding* (Yang et al., 2019) | NLP / Machine Learning | **Core ML Paper** | 42 | 362 | 419 |
| `f7d92af0` | *Statistical Inference for High-Dimensional Models* | Mathematical Statistics | **Out-of-Domain Probe** | 38 | 379 | 402 |
| `680a27f3` | *Automated Patent Processing and Classification System* | Systems / Applied IP | **Out-of-Domain Probe** | 33 | 178 | 254 |

### Cross-Paper Structural Bridges
Excluding synthetic demo documents, GPT-1 and XLNet share **16 real structural bridge entities** in the materialized knowledge graph:
- **Architecture Bridges:** `Transformer`, `Transformer-XL`, `decoder`, `attention`
- **Evaluation Bridges:** `RACE`, `GLUE`, `MNLI`, `SQuAD`, `Story Cloze`
- **Training Data Bridges:** `BooksCorpus`, `Wikipedia`

These bridges provide the ground truth connectivity enabling cross-paper reasoning without flat text-chunk retrieval.

---

## 4. The 40 Ground Truth Benchmark Questions (`ground_truth_qa.json`)

To measure performance scientifically, we authored **40 verified, human-annotated questions** specifically designed around 5 cognitive reasoning difficulty tiers:

### 4.1 Question Type Taxonomy & Design Rationale

| Question Type | Count | Cognitive Rationale | What Failure Mode It Exposes in Baselines |
|---|:---:|---|---|
| **`lookup`** | 10 | Direct factual retrieval from a single paper section (e.g. hidden dimension, layer counts, pretraining batch sizes). | Tests baseline entity recognition. Vector RAG performs relatively well here (80%), but direct LLM memory fails on exact numbers (50%). |
| **`multihop`** | 8 | Two-step or three-step relational path following: $\text{Method} \to \text{Task} \to \text{Dataset} \to \text{Metric}$. | Exposes **context chunk fragmentation** in Vector RAG (50% acc) because the relational hops are distributed across non-adjacent paragraphs. Our KG Agent traverses explicit graph edges (87.5% acc). |
| **`aggregation`** | 6 | Mathematical counting, superlatives, and multi-result summaries (e.g. SOTA counts, highest accuracy across models). | Tests multi-entity gathering. Unstructured chunks miss rows from large comparison tables. |
| **`cross_paper`** | 8 | Comparative reasoning between GPT-1 and XLNet linked by shared bridge entities (`RACE`, `GLUE`, `Transformer`). | Vector RAG fails (37.5%) because cosine similarity cannot jointly retrieve and contrast chunks from two different PDF embeddings. Our KG Agent leverages `SAME_AS` entity linking (87.5% acc). |
| **`unanswerable`** | 8 | Negative control probe questions whose answers **do not exist** in the papers (e.g. BLEU score for GPT on machine translation; inference latency in milliseconds). | Exposes **LLM hallucination**. Direct LLM hallucinates 100% of the time (0% abstain). Vector RAG guesses plausible numbers 75% of the time. Our KG Agent verifies no path exists and truthfully abstains (**87.5% true abstention**). |

---

## 5. Comparative Evaluation Summary

| Evaluation Dimension | Direct LLM (Zero-Shot) | Standard Vector RAG | Naive / Unconstrained KG | Our Proposed KG Agent |
|---|:---:|:---:|:---:|:---:|
| **Overall Accuracy** | 40.0% | 65.0% | 67.5% | **85.0%** *(+20% vs RAG)* |
| **Multi-Hop Reasoning** | 25.0% | 50.0% | 62.5% | **87.5%** *(+37.5% vs RAG)* |
| **Cross-Paper Comparison** | 37.5% | 37.5% | 50.0% | **87.5%** *(+50% vs RAG)* |
| **Hallucination Resistance** | 0.0% | 25.0% | 62.5% | **87.5%** *(Truthful)* |
| **Evidence Traceability** | None (Black Box) | Chunk Similarity | Noisy Graph Paths | **Verified Citations (90%)** |
| **Average Latency** | 1.2s | 2.8s | 11.5s (Dead loops) | **7.4s (Clean paths)** |
