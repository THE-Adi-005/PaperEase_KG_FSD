"""Generate comprehensive 80-question benchmark across 10 papers:
20 Lookup, 20 Multi-hop, 20 Aggregation, 20 Cross-paper.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

QUESTIONS = [
    # ── 1. LOOKUP (20 Questions: q01 to q20) ─────────────────────────────────
    {
        "id": "q01", "type": "lookup", "paper_ids": ["1e6c7c12"],
        "question": "What dataset is used to evaluate the language model in the GPT paper?",
        "gold_answers": ["BooksCorpus", "BookCorpus"],
        "answerable": True, "verified": True, "evidence": "Section 3.1 — BooksCorpus dataset"
    },
    {
        "id": "q02", "type": "lookup", "paper_ids": ["demo_bert_2018"],
        "question": "What is the primary pretraining objective used in the BERT paper?",
        "gold_answers": ["Masked Language Modeling", "MLM", "masked language model"],
        "answerable": True, "verified": True, "evidence": "Section 2 — Masked Language Model objective"
    },
    {
        "id": "q03", "type": "lookup", "paper_ids": ["demo_attention_2017"],
        "question": "What BLEU score does the Big Transformer model achieve on WMT 2014 English-to-German?",
        "gold_answers": ["28.4", "28.40"],
        "answerable": True, "verified": True, "evidence": "Table 1 — Transformer (Big Model) WMT EN-DE 28.4"
    },
    {
        "id": "q04", "type": "lookup", "paper_ids": ["demo_gpt3_2020"],
        "question": "What is the maximum parameter count of GPT-3 evaluated in the paper?",
        "gold_answers": ["175 billion", "175B", "175,000,000,000"],
        "answerable": True, "verified": True, "evidence": "Section 1 — GPT-3 175B parameter scale"
    },
    {
        "id": "q05", "type": "lookup", "paper_ids": ["demo_t5_2020"],
        "question": "What pretraining dataset was introduced in the T5 paper?",
        "gold_answers": ["C4", "Colossal Clean Crawled Corpus"],
        "answerable": True, "verified": True, "evidence": "Section 2 — Colossal Clean Crawled Corpus (C4)"
    },
    {
        "id": "q06", "type": "lookup", "paper_ids": ["demo_electra_2020"],
        "question": "What pretraining task is proposed in the ELECTRA paper instead of masked LM?",
        "gold_answers": ["Replaced Token Detection", "RTD"],
        "answerable": True, "verified": True, "evidence": "Section 2 — Replaced Token Detection"
    },
    {
        "id": "q07", "type": "lookup", "paper_ids": ["demo_roberta_2019"],
        "question": "What masking strategy is introduced in RoBERTa to replace static masking?",
        "gold_answers": ["Dynamic Masking", "dynamic"],
        "answerable": True, "verified": True, "evidence": "Section 2 — Dynamic Masking"
    },
    {
        "id": "q08", "type": "lookup", "paper_ids": ["demo_attention_2017"],
        "question": "What attention mechanism does the Transformer use to eschew recurrence?",
        "gold_answers": ["Self-Attention", "Multi-Head Attention", "attention mechanism"],
        "answerable": True, "verified": True, "evidence": "Abstract & Section 2 — Multi-Head Self-Attention"
    },
    {
        "id": "q09", "type": "lookup", "paper_ids": ["demo_attention_2017"],
        "question": "What BLEU score does the Transformer achieve on WMT 2014 English-to-French translation?",
        "gold_answers": ["41.8", "41.80"],
        "answerable": True, "verified": True, "evidence": "Section 3 — WMT 2014 EN-FR BLEU of 41.8"
    },
    {
        "id": "q10", "type": "lookup", "paper_ids": ["demo_bert_2018"],
        "question": "What F1 score does BERT Large achieve on SQuAD v1.1 in the paper?",
        "gold_answers": ["93.2"],
        "answerable": True, "verified": True, "evidence": "Table 2 — SQuAD v1.1 BERT Large F1=93.2"
    },
    {
        "id": "q11", "type": "lookup", "paper_ids": ["demo_roberta_2019"],
        "question": "What overall GLUE score does RoBERTa Large achieve in the paper?",
        "gold_answers": ["88.5"],
        "answerable": True, "verified": True, "evidence": "Table 1 — RoBERTa Large GLUE score 88.5"
    },
    {
        "id": "q12", "type": "lookup", "paper_ids": ["demo_gpt3_2020"],
        "question": "How many parameter tiers does GPT-3 evaluate across in the paper?",
        "gold_answers": ["8", "eight"],
        "answerable": True, "verified": True, "evidence": "Section 2 — scaled across 8 parameter tiers"
    },
    {
        "id": "q13", "type": "lookup", "paper_ids": ["demo_gpt3_2020"],
        "question": "What accuracy does GPT-3 175B achieve on SuperGLUE in the few-shot setting?",
        "gold_answers": ["71.8%", "71.8"],
        "answerable": True, "verified": True, "evidence": "Table 1 — SuperGLUE Few-Shot 71.8%"
    },
    {
        "id": "q14", "type": "lookup", "paper_ids": ["demo_t5_2020"],
        "question": "What is the parameter count of the largest T5 model evaluated in the paper?",
        "gold_answers": ["11 billion", "11B"],
        "answerable": True, "verified": True, "evidence": "Section 3 — T5-11B model"
    },
    {
        "id": "q15", "type": "lookup", "paper_ids": ["b7f9484b"],
        "question": "What dataset does XLNet use for pretraining?",
        "gold_answers": ["BooksCorpus", "Wikipedia", "Giga5", "ClueWeb", "Common Crawl"],
        "answerable": True, "verified": True, "evidence": "Section 3.1 — pretraining datasets"
    },
    {
        "id": "q16", "type": "lookup", "paper_ids": ["demo_roberta_2019"],
        "question": "What mini-batch sequence size is used in RoBERTa pretraining?",
        "gold_answers": ["8K", "8000"],
        "answerable": True, "verified": True, "evidence": "Section 2 — large mini-batches of 8K sequences"
    },
    {
        "id": "q17", "type": "lookup", "paper_ids": ["demo_electra_2020"],
        "question": "What is the parameter count of ELECTRA-Small?",
        "gold_answers": ["14M", "14 million"],
        "answerable": True, "verified": True, "evidence": "Section 3 — ELECTRA-Small with 14M parameters"
    },
    {
        "id": "q18", "type": "lookup", "paper_ids": ["demo_electra_2020"],
        "question": "What is the GLUE score achieved by ELECTRA-Large?",
        "gold_answers": ["89.5"],
        "answerable": True, "verified": True, "evidence": "Table 1 — ELECTRA Large 89.5 GLUE"
    },
    {
        "id": "q19", "type": "lookup", "paper_ids": ["680a27f3"],
        "question": "In the EVOPAT paper, what patent agent qualification examination did PatentGPT pass?",
        "gold_answers": ["2019 China Patent Agent Qualification Examination", "Patent Agent Qualification Examination"],
        "answerable": True, "verified": True, "evidence": "Abstract & Table 3 — 2019 China Patent Agent Exam"
    },
    {
        "id": "q20", "type": "lookup", "paper_ids": ["1e6c7c12"],
        "question": "Which question answering dataset is evaluated in the GPT paper Table 2?",
        "gold_answers": ["RACE"],
        "answerable": True, "verified": True, "evidence": "Table 2 — RACE row"
    },

    # ── 2. MULTI-HOP (20 Questions: q21 to q40) ──────────────────────────────
    {
        "id": "q21", "type": "multihop", "paper_ids": ["b7f9484b"],
        "question": "What mechanism does XLNet use to avoid seeing future tokens, and what attention stream represents it?",
        "gold_answers": ["permutation attention mask", "two-stream attention", "query stream"],
        "answerable": True, "verified": True, "evidence": "Section 2.1 & 2.2 — two-stream permutation attention"
    },
    {
        "id": "q22", "type": "multihop", "paper_ids": ["demo_bert_2018"],
        "question": "In BERT, what special tokens mark sentence boundaries for pair classification tasks?",
        "gold_answers": ["[CLS]", "[SEP]"],
        "answerable": True, "verified": True, "evidence": "Section 2.1 — [CLS] token and [SEP] token"
    },
    {
        "id": "q23", "type": "multihop", "paper_ids": ["demo_attention_2017"],
        "question": "In Transformer, what is the maximum path length between any two tokens in self-attention, and why?",
        "gold_answers": ["O(1)", "constant"],
        "answerable": True, "verified": True, "evidence": "Table 2 — self-attention maximum path length is O(1)"
    },
    {
        "id": "q24", "type": "multihop", "paper_ids": ["demo_electra_2020"],
        "question": "In ELECTRA, what component generates candidate tokens, and what network predicts whether they are replaced?",
        "gold_answers": ["generator", "discriminator"],
        "answerable": True, "verified": True, "evidence": "Section 2 — generator model and discriminator network"
    },
    {
        "id": "q25", "type": "multihop", "paper_ids": ["demo_roberta_2019"],
        "question": "How does RoBERTa modify BERT's pretraining objective regarding document structure, and what loss is removed?",
        "gold_answers": ["full-sentences", "removes Next Sentence Prediction", "no NSP"],
        "answerable": True, "verified": True, "evidence": "Section 2 — full-sentences without NSP loss"
    },
    {
        "id": "q26", "type": "multihop", "paper_ids": ["demo_t5_2020"],
        "question": "How does T5 unify classification, translation, and summarization, and what is the output format?",
        "gold_answers": ["text-to-text", "text strings"],
        "answerable": True, "verified": True, "evidence": "Section 1 — unified text-to-text format where output is text"
    },
    {
        "id": "q27", "type": "multihop", "paper_ids": ["demo_gpt3_2020"],
        "question": "In GPT-3, how does in-context few-shot learning avoid gradient updates during inference?",
        "gold_answers": ["prompt context", "no gradient updates", "demonstrations in context"],
        "answerable": True, "verified": True, "evidence": "Section 1 — demonstrations in context without fine-tuning"
    },
    {
        "id": "q28", "type": "multihop", "paper_ids": ["demo_attention_2017"],
        "question": "What two sublayers make up each Transformer encoder layer, and what connects them?",
        "gold_answers": ["multi-head self-attention", "feed-forward", "residual connection", "Add & Norm"],
        "answerable": True, "verified": True, "evidence": "Section 2 — multi-head attention and feed-forward with Add & Norm"
    },
    {
        "id": "q29", "type": "multihop", "paper_ids": ["demo_bert_2018"],
        "question": "In BERT Large, what are the number of layers L, hidden dimension H, and attention heads A?",
        "gold_answers": ["L=24", "H=1024", "A=16"],
        "answerable": True, "verified": True, "evidence": "Section 2 — L=24, H=1024, A=16"
    },
    {
        "id": "q30", "type": "multihop", "paper_ids": ["b7f9484b"],
        "question": "How does XLNet achieve bidirectional context without using a BERT-style mask token?",
        "gold_answers": ["permutation language modeling", "factorization orders"],
        "answerable": True, "verified": True, "evidence": "Section 2 — permutation over all factorization orders"
    },
    {
        "id": "q31", "type": "multihop", "paper_ids": ["demo_t5_2020"],
        "question": "In T5, how is the C4 dataset created from Common Crawl, and what filtering is applied?",
        "gold_answers": ["cleaned Common Crawl", "heuristic filtering", "deduplication"],
        "answerable": True, "verified": True, "evidence": "Section 2 — C4 heuristic cleaning and deduplication"
    },
    {
        "id": "q32", "type": "multihop", "paper_ids": ["demo_electra_2020", "demo_roberta_2019"],
        "question": "What is the training compute multiplier of RoBERTa Base compared to ELECTRA Base for matching GLUE scores?",
        "gold_answers": ["10x", "10.0x"],
        "answerable": True, "verified": True, "evidence": "ELECTRA Table 1 — RoBERTa 10.0x vs ELECTRA 1.0x"
    },
    {
        "id": "q33", "type": "multihop", "paper_ids": ["demo_gpt3_2020"],
        "question": "In GPT-3, what residual connection modification is adopted from GPT-2?",
        "gold_answers": ["pre-activation residual connections", "modified initialization"],
        "answerable": True, "verified": True, "evidence": "Section 2 — pre-activation residual connections"
    },
    {
        "id": "q34", "type": "multihop", "paper_ids": ["demo_attention_2017"],
        "question": "In Transformer, what is the computational complexity per layer of self-attention as a function of sequence length n and dimension d?",
        "gold_answers": ["O(n² · d)", "O(n^2 * d)"],
        "answerable": True, "verified": True, "evidence": "Table 2 — Self-Attention O(n^2 * d)"
    },
    {
        "id": "q35", "type": "multihop", "paper_ids": ["1e6c7c12"],
        "question": "What optimizer and learning rate schedule are used in GPT pretraining?",
        "gold_answers": ["Adam", "cosine learning rate decay"],
        "answerable": True, "verified": True, "evidence": "Section 3.2 — Adam optimizer with cosine decay"
    },
    {
        "id": "q36", "type": "multihop", "paper_ids": ["demo_bert_2018"],
        "question": "In BERT, what percentage of tokens are chosen for masking, and what fraction are replaced with [MASK]?",
        "gold_answers": ["15%", "80%"],
        "answerable": True, "verified": True, "evidence": "Section 2 — 15% masked, 80% with [MASK]"
    },
    {
        "id": "q37", "type": "multihop", "paper_ids": ["demo_roberta_2019"],
        "question": "In RoBERTa, how does byte-level BPE differ from BERT's vocabulary, and what is its subword size?",
        "gold_answers": ["50K", "50,000 subwords", "byte-level BPE"],
        "answerable": True, "verified": True, "evidence": "Section 2 — 50K subword byte-level BPE"
    },
    {
        "id": "q38", "type": "multihop", "paper_ids": ["demo_t5_2020"],
        "question": "In T5, what is the ROUGE-2 score achieved on CNN/Daily Mail summarization by T5-11B?",
        "gold_answers": ["43.5"],
        "answerable": True, "verified": True, "evidence": "Table 1 — CNN/DM ROUGE-2 43.5"
    },
    {
        "id": "q39", "type": "multihop", "paper_ids": ["680a27f3"],
        "question": "How does PatentGPT in EVOPAT adapt general LLM representations for patent legal examination?",
        "gold_answers": ["hierarchical summarization", "patent claims fine-tuning"],
        "answerable": True, "verified": True, "evidence": "Section 3 — hierarchical patent structure"
    },
    {
        "id": "q40", "type": "multihop", "paper_ids": ["demo_electra_2020"],
        "question": "In ELECTRA, why is the discriminator more sample-efficient than BERT's masked language model?",
        "gold_answers": ["trains over all tokens", "binary classification on all tokens"],
        "answerable": True, "verified": True, "evidence": "Section 1 — trains on 100% of tokens rather than 15%"
    },

    # ── 3. AGGREGATION (20 Questions: q41 to q60) ────────────────────────────
    {
        "id": "q41", "type": "aggregation", "paper_ids": ["1e6c7c12"],
        "question": "How many benchmarks in the GPT paper does the model achieve state-of-the-art results on?",
        "gold_answers": ["9", "9 of 12"],
        "answerable": True, "verified": True, "evidence": "Abstract — 9 of 12 benchmarks"
    },
    {
        "id": "q42", "type": "aggregation", "paper_ids": ["b7f9484b"],
        "question": "On how many NLP tasks does XLNet achieve state-of-the-art results according to the paper?",
        "gold_answers": ["20", "twenty"],
        "answerable": True, "verified": True, "evidence": "Abstract — 20 tasks"
    },
    {
        "id": "q43", "type": "aggregation", "paper_ids": ["demo_t5_2020"],
        "question": "On how many tasks does T5-11B achieve state-of-the-art results in the paper?",
        "gold_answers": ["24", "twenty-four"],
        "answerable": True, "verified": True, "evidence": "Section 3 — state of the art on 24 tasks"
    },
    {
        "id": "q44", "type": "aggregation", "paper_ids": ["demo_attention_2017"],
        "question": "How many attention heads does the base Transformer model use?",
        "gold_answers": ["8", "eight"],
        "answerable": True, "verified": True, "evidence": "Section 2.2 — h=8 parallel attention heads"
    },
    {
        "id": "q45", "type": "aggregation", "paper_ids": ["demo_attention_2017"],
        "question": "How many encoder layers N does the Transformer model stack?",
        "gold_answers": ["6", "six"],
        "answerable": True, "verified": True, "evidence": "Section 2.1 — N=6 identical layers"
    },
    {
        "id": "q46", "type": "aggregation", "paper_ids": ["1e6c7c12"],
        "question": "How many attention heads does the GPT model use?",
        "gold_answers": ["12", "twelve"],
        "answerable": True, "verified": True, "evidence": "Section 3.2 — 12 attention heads"
    },
    {
        "id": "q47", "type": "aggregation", "paper_ids": ["demo_bert_2018"],
        "question": "How many layers does BERT Base have?",
        "gold_answers": ["12", "twelve"],
        "answerable": True, "verified": True, "evidence": "Section 2 — L=12 layers"
    },
    {
        "id": "q48", "type": "aggregation", "paper_ids": ["demo_bert_2018"],
        "question": "How many layers does BERT Large have?",
        "gold_answers": ["24", "twenty-four"],
        "answerable": True, "verified": True, "evidence": "Section 2 — L=24 layers"
    },
    {
        "id": "q49", "type": "aggregation", "paper_ids": ["b7f9484b"],
        "question": "How many total parameters does the largest XLNet model have?",
        "gold_answers": ["340M", "340 million", "340"],
        "answerable": True, "verified": True, "evidence": "Section 3.1 — XLNet-Large 340M parameters"
    },
    {
        "id": "q50", "type": "aggregation", "paper_ids": ["b7f9484b"],
        "question": "What is the highest accuracy XLNet achieves on RACE in the paper?",
        "gold_answers": ["81.75"],
        "answerable": True, "verified": True, "evidence": "Table 4 — XLNet Large 81.75"
    },
    {
        "id": "q51", "type": "aggregation", "paper_ids": ["demo_bert_2018"],
        "question": "What is the overall GLUE score of BERT Large reported in the paper?",
        "gold_answers": ["82.1"],
        "answerable": True, "verified": True, "evidence": "Table 1 — BERT Large GLUE Score 82.1"
    },
    {
        "id": "q52", "type": "aggregation", "paper_ids": ["demo_roberta_2019"],
        "question": "What is the GLUE score of RoBERTa Large reported in the paper?",
        "gold_answers": ["88.5"],
        "answerable": True, "verified": True, "evidence": "Table 1 — RoBERTa Large 88.5"
    },
    {
        "id": "q53", "type": "aggregation", "paper_ids": ["demo_electra_2020"],
        "question": "What is the GLUE score of ELECTRA Large reported in the paper?",
        "gold_answers": ["89.5"],
        "answerable": True, "verified": True, "evidence": "Table 1 — ELECTRA Large 89.5"
    },
    {
        "id": "q54", "type": "aggregation", "paper_ids": ["demo_t5_2020"],
        "question": "What is the GLUE score of T5-11B reported in the paper?",
        "gold_answers": ["89.7"],
        "answerable": True, "verified": True, "evidence": "Table 1 — T5-11B GLUE 89.7"
    },
    {
        "id": "q55", "type": "aggregation", "paper_ids": ["demo_t5_2020"],
        "question": "What is the maximum parameter count of T5?",
        "gold_answers": ["11 billion", "11B"],
        "answerable": True, "verified": True, "evidence": "Table 1 — T5-11B has 11B parameters"
    },
    {
        "id": "q56", "type": "aggregation", "paper_ids": ["1e6c7c12"],
        "question": "What is the pretraining batch size used in the GPT paper?",
        "gold_answers": ["64"],
        "answerable": True, "verified": True, "evidence": "Section 3.2 — batch size 64"
    },
    {
        "id": "q57", "type": "aggregation", "paper_ids": ["demo_roberta_2019"],
        "question": "How many subwords are in RoBERTa's BPE vocabulary?",
        "gold_answers": ["50,000", "50K"],
        "answerable": True, "verified": True, "evidence": "Section 2 — 50K subwords"
    },
    {
        "id": "q58", "type": "aggregation", "paper_ids": ["demo_electra_2020"],
        "question": "What is the parameter count of ELECTRA-Base?",
        "gold_answers": ["110M", "110 million"],
        "answerable": True, "verified": True, "evidence": "Table 1 — ELECTRA Base 110M"
    },
    {
        "id": "q59", "type": "aggregation", "paper_ids": ["demo_attention_2017"],
        "question": "How many parameters does Transformer Big have?",
        "gold_answers": ["213M", "213 million"],
        "answerable": True, "verified": True, "evidence": "Table 1 — Transformer (Big Model) 213M"
    },
    {
        "id": "q60", "type": "aggregation", "paper_ids": ["demo_roberta_2019"],
        "question": "What is the SQuAD v2.0 F1 score of RoBERTa Large?",
        "gold_answers": ["89.8"],
        "answerable": True, "verified": True, "evidence": "Section 3 — SQuAD v2.0 89.8 F1"
    },

    # ── 4. CROSS-PAPER (20 Questions: q61 to q80) ────────────────────────────
    {
        "id": "q61", "type": "cross_paper", "paper_ids": ["1e6c7c12", "b7f9484b"],
        "question": "Both GPT and XLNet evaluate on RACE. Which paper reports higher accuracy on RACE?",
        "gold_answers": ["XLNet", "b7f9484b"],
        "answerable": True, "verified": True, "evidence": "GPT Table 2 (59.0) vs XLNet Table 4 (81.75)"
    },
    {
        "id": "q62", "type": "cross_paper", "paper_ids": ["1e6c7c12", "demo_bert_2018"],
        "question": "Compare the pretraining objectives of GPT and BERT. What is the fundamental difference?",
        "gold_answers": ["GPT is causal autoregressive, BERT is bidirectional masked LM", "autoregressive vs masked LM"],
        "answerable": True, "verified": True, "evidence": "GPT Section 3 vs BERT Section 2"
    },
    {
        "id": "q63", "type": "cross_paper", "paper_ids": ["demo_bert_2018", "demo_roberta_2019"],
        "question": "Both BERT and RoBERTa evaluate on GLUE. Which model achieves higher GLUE score?",
        "gold_answers": ["RoBERTa", "RoBERTa Large", "demo_roberta_2019"],
        "answerable": True, "verified": True, "evidence": "BERT Table 1 (82.1) vs RoBERTa Table 1 (88.5)"
    },
    {
        "id": "q64", "type": "cross_paper", "paper_ids": ["demo_roberta_2019", "b7f9484b", "demo_electra_2020"],
        "question": "Between RoBERTa Large, XLNet Large, and ELECTRA Large, which achieves the highest GLUE score?",
        "gold_answers": ["ELECTRA Large", "ELECTRA", "demo_electra_2020"],
        "answerable": True, "verified": True, "evidence": "RoBERTa (88.5), XLNet (88.4), ELECTRA Large (89.5)"
    },
    {
        "id": "q65", "type": "cross_paper", "paper_ids": ["demo_attention_2017", "demo_bert_2018", "1e6c7c12", "b7f9484b"],
        "question": "What architecture do Transformer, BERT, GPT, and XLNet all build upon?",
        "gold_answers": ["Transformer", "Self-Attention Transformer"],
        "answerable": True, "verified": True, "evidence": "All papers build upon the Transformer architecture"
    },
    {
        "id": "q66", "type": "cross_paper", "paper_ids": ["1e6c7c12", "b7f9484b"],
        "question": "Compare the pretraining objectives of GPT and XLNet. What is the main difference?",
        "gold_answers": ["GPT uses causal LM, XLNet uses permutation LM", "autoregressive vs permutation"],
        "answerable": True, "verified": True, "evidence": "GPT Section 3 vs XLNet Section 2"
    },
    {
        "id": "q67", "type": "cross_paper", "paper_ids": ["demo_bert_2018", "demo_gpt3_2020"],
        "question": "Does BERT or GPT-3 use bidirectional attention across all encoder layers?",
        "gold_answers": ["BERT", "demo_bert_2018"],
        "answerable": True, "verified": True, "evidence": "BERT is bidirectional encoder; GPT-3 is causal autoregressive"
    },
    {
        "id": "q68", "type": "cross_paper", "paper_ids": ["demo_bert_2018", "demo_roberta_2019"],
        "question": "Both RoBERTa and BERT use masked language modeling. What change did RoBERTa make to BERT's masking schedule?",
        "gold_answers": ["dynamic masking", "dynamic instead of static"],
        "answerable": True, "verified": True, "evidence": "RoBERTa Section 2 — Dynamic Masking vs Static Masking"
    },
    {
        "id": "q69", "type": "cross_paper", "paper_ids": ["1e6c7c12", "b7f9484b"],
        "question": "Both GPT and XLNet use BooksCorpus for pretraining. Which additional datasets does XLNet use that GPT does not?",
        "gold_answers": ["Wikipedia", "Giga5", "ClueWeb", "Common Crawl"],
        "answerable": True, "verified": True, "evidence": "GPT (BooksCorpus only) vs XLNet Section 3.1"
    },
    {
        "id": "q70", "type": "cross_paper", "paper_ids": ["demo_t5_2020", "demo_bert_2018"],
        "question": "Between T5-11B and BERT Large, which model achieves higher GLUE score in their respective papers?",
        "gold_answers": ["T5-11B", "T5", "demo_t5_2020"],
        "answerable": True, "verified": True, "evidence": "BERT Large (82.1) vs T5-11B (89.7)"
    },
    {
        "id": "q71", "type": "cross_paper", "paper_ids": ["demo_electra_2020", "demo_bert_2018"],
        "question": "Compare ELECTRA and BERT in terms of pretraining loss. How does ELECTRA differ from BERT?",
        "gold_answers": ["ELECTRA uses replaced token detection over all tokens, BERT reconstructs 15% masked tokens", "discriminator binary loss vs MLM"],
        "answerable": True, "verified": True, "evidence": "ELECTRA Section 1 vs BERT Section 2"
    },
    {
        "id": "q72", "type": "cross_paper", "paper_ids": ["demo_bert_2018", "demo_t5_2020"],
        "question": "Between BERT Large and T5-11B, which model achieves higher SuperGLUE accuracy?",
        "gold_answers": ["T5-11B", "T5", "demo_t5_2020"],
        "answerable": True, "verified": True, "evidence": "T5 Table 1 (89.3 SuperGLUE) vs BERT"
    },
    {
        "id": "q73", "type": "cross_paper", "paper_ids": ["demo_attention_2017", "1e6c7c12", "demo_bert_2018"],
        "question": "Which model was published first: Attention Is All You Need, GPT, or BERT?",
        "gold_answers": ["Attention Is All You Need", "Transformer", "2017"],
        "answerable": True, "verified": True, "evidence": "Vaswani 2017 predates GPT (2018) and BERT (2018)"
    },
    {
        "id": "q74", "type": "cross_paper", "paper_ids": ["1e6c7c12", "demo_bert_2018", "demo_attention_2017"],
        "question": "Does GPT or BERT use an encoder-decoder architecture like the original Transformer?",
        "gold_answers": ["Neither", "neither model", "GPT is decoder-only, BERT is encoder-only"],
        "answerable": True, "verified": True, "evidence": "Transformer is encoder-decoder; GPT is decoder-only, BERT is encoder-only"
    },
    {
        "id": "q75", "type": "cross_paper", "paper_ids": ["demo_t5_2020", "demo_bert_2018"],
        "question": "What unified framing does T5 introduce that contrasts with BERT's separate classification heads?",
        "gold_answers": ["text-to-text", "unified text-to-text framework"],
        "answerable": True, "verified": True, "evidence": "T5 Section 1 vs BERT Section 3"
    },
    {
        "id": "q76", "type": "cross_paper", "paper_ids": ["demo_gpt3_2020", "demo_t5_2020"],
        "question": "Between GPT-3 175B and T5-11B, which has a higher parameter count?",
        "gold_answers": ["GPT-3 175B", "GPT-3", "demo_gpt3_2020"],
        "answerable": True, "verified": True, "evidence": "175B vs 11B"
    },
    {
        "id": "q77", "type": "cross_paper", "paper_ids": ["demo_roberta_2019", "demo_bert_2018"],
        "question": "Which model removed the Next Sentence Prediction (NSP) task from BERT: RoBERTa or XLNet?",
        "gold_answers": ["RoBERTa", "demo_roberta_2019"],
        "answerable": True, "verified": True, "evidence": "RoBERTa Section 2 explicitly removes NSP loss"
    },
    {
        "id": "q78", "type": "cross_paper", "paper_ids": ["demo_electra_2020", "demo_roberta_2019"],
        "question": "Compare the compute efficiency of ELECTRA-Base vs RoBERTa-Base on GLUE. Which requires less compute?",
        "gold_answers": ["ELECTRA-Base", "ELECTRA", "demo_electra_2020"],
        "answerable": True, "verified": True, "evidence": "ELECTRA Table 1 — 1.0x vs 10.0x compute multiplier"
    },
    {
        "id": "q79", "type": "cross_paper", "paper_ids": ["demo_attention_2017"],
        "question": "Between Transformer Base and Transformer Big, which achieved higher BLEU on WMT English-to-French?",
        "gold_answers": ["Transformer Big", "Transformer (Big Model)"],
        "answerable": True, "verified": True, "evidence": "Table 1 — 41.80 vs 38.10"
    },
    {
        "id": "q80", "type": "cross_paper", "paper_ids": ["demo_bert_2018", "b7f9484b"],
        "question": "Both BERT and XLNet evaluate on GLUE. Does XLNet Large outperform BERT Large on the GLUE benchmark?",
        "gold_answers": ["Yes", "XLNet Large", "XLNet outperforms BERT Large"],
        "answerable": True, "verified": True, "evidence": "XLNet Table 3 (88.4) vs BERT Table 1 (82.1)"
    },
]

def main():
    target_80 = PROJECT_ROOT / "dataset" / "ground_truth_qa_80.json"
    target_main = PROJECT_ROOT / "dataset" / "ground_truth_qa.json"
    
    for q in QUESTIONS:
        q["source"] = "manual"
        
    with open(target_80, "w", encoding="utf-8") as f:
        json.dump(QUESTIONS, f, indent=2, ensure_ascii=False)
        
    with open(target_main, "w", encoding="utf-8") as f:
        json.dump(QUESTIONS, f, indent=2, ensure_ascii=False)
        
    print(f"Generated {len(QUESTIONS)} questions in {target_80} and synced to {target_main}!")
    
    # Verify counts per tier
    counts = {}
    for q in QUESTIONS:
        t = q["type"]
        counts[t] = counts.get(t, 0) + 1
    print("Counts per tier:", counts)

if __name__ == "__main__":
    main()

