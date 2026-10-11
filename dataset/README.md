# KG Paper Assistant: Evaluation Dataset & Ground Truth Benchmark

This dataset provides the standardized evaluation benchmark for the **KG Paper Assistant** system.

---

## 1. Directory Structure

```
dataset/
├── papers/
│   ├── 1e6c7c12_GPT_Radford_2018.pdf          # Core ML paper (GPT-1, Radford et al., 2018)
│   ├── b7f9484b_XLNet_Yang_2019.pdf           # Core ML paper (XLNet, Yang et al., 2019)
│   ├── f7d92af0_Statistical_Inference.pdf     # Out-of-domain evaluation probe (Statistics)
│   └── 680a27f3_Patent_System_2024.pdf        # Out-of-domain evaluation probe (Patent/Systems)
├── ground_truth_qa.json                       # 40 human-verified gold QA questions with evidence
└── README.md                                  # This documentation
```

---

## 2. Ground Truth Question Taxonomy

The evaluation set (`ground_truth_qa.json`) consists of **40 questions** rigorously divided into 5 cognitive difficulty tiers:

| Question Type | Count | Description | Example Target |
|---|---|---|---|
| **`lookup`** | 10 | Direct factual retrieval from a single paper section. | Architecture: `"Transformer"`, Decoder layers: `"12"`, Pretraining tokens: `"BooksCorpus"`. |
| **`multihop`** | 8 | Multi-step reasoning across connected entities (Method $\to$ Task $\to$ Dataset). | *"Which method does XLNet extend, and on which dataset does it outperform that method?"* $\to$ `["BERT", "RACE", "SQuAD"]`. |
| **`aggregation`** | 6 | Mathematical and counting questions over paper results. | *"How many NLP tasks does XLNet achieve SOTA on?"* $\to$ `"20"`. |
| **`cross_paper`** | 8 | Comparative reasoning between two papers using shared bridge entities (`RACE`, `GLUE`, `Transformer`). | *"Both GPT and XLNet evaluate on RACE. Which reports higher accuracy?"* $\to$ `"XLNet"`. |
| **`unanswerable`** | 8 | Adversarial negative control questions whose answers are NOT in the papers. | *"What is GPT's BLEU score on machine translation?"* $\to$ Gold: `[]`, Answerable: `false`. |

---

## 3. The 4-Model Comparative Benchmark

The benchmark compares 4 distinct system architectures against the ground truth:

1. **Model 1: Direct LLM (Zero-Shot / Parametric Only)**
   - No context retrieval or graph tools.
   - Measures raw LLM hallucinations and memory limits.

2. **Model 2: Standard Vector RAG**
   - Dense retrieval using sentence-transformers (`all-MiniLM-L6-v2`) over 300-word section chunks.
   - Top-$k$ context retrieval with temperature-0 generation.

3. **Model 3: Naive / Unconstrained KG Agent**
   - Graph constructed without schema constraints (35+ dynamic relation types) and without majority-vote noise filtering.
   - Measures the cost of graph noise on ReACT reasoning.

4. **Model 4: Our Proposed System (Schema-Constrained ReACT KG Agent)**
   - Curated schema ($R_7$), 50% majority-vote filtering, type-signature enforcement, per-section capping ($K=20$), cross-paper entity linking, and autonomous ReACT path exploration.

---

## 4. Evaluation Criteria

- **Exact & Numeric Match Accuracy:** Scientific tolerance on floating-point metrics (e.g., `92.4%` matches `0.924`).
- **Hallucination Resistance (Abstention Rate):** True positive rate of responding *"Not found in the papers"* on unanswerable questions.
- **Traceability:** Verified provenance linking answers to graph entities, relations, and source section IDs.
