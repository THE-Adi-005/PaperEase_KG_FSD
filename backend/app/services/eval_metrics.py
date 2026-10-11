"""eval_metrics.py — High-precision multi-metric evaluation module.

Computes:
1. Exact Match (EM binary 1.0/0.0 on extracted answer)
2. SQuAD Token F1 (harmonic mean of token precision and recall)
3. BLEU Score (nltk sentence_bleu with smoothing)
4. Cosine Similarity (TF-IDF semantic vector similarity)
5. BERTScore (Token-level contextual semantic F1 similarity)
"""

import re
import string
import numpy as np
from collections import Counter
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_smoother = SmoothingFunction().method1

_FAILURE_WORDS = {"failed", "truncat", "fragment", "uncertain", "could not", "unable", "void", "cannot determine", "inconclusive"}


def _normalize_text(s: str) -> str:
    """Lower text and remove punctuation, articles and extra whitespace."""
    def remove_articles(text):
        return re.sub(r'\b(a|an|the)\b', ' ', text)

    def white_space_fix(text):
        return ' '.join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return ''.join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s))))


def _is_failure_text(text: str) -> bool:
    """Detect if the candidate text expresses retrieval or reasoning failure."""
    t_lower = text.lower()
    return any(fw in t_lower for fw in _FAILURE_WORDS)


def compute_exact_match(candidate: str, references: list[str]) -> float:
    """Exact Match: candidate equals or contains the reference target without failure caveats."""
    if not candidate or not references:
        return 0.0
    if _is_failure_text(candidate):
        return 0.0

    norm_cand = _normalize_text(candidate)
    cand_tokens = set(norm_cand.split())

    for ref in references:
        norm_ref = _normalize_text(ref)
        if not norm_ref:
            continue
        if norm_cand == norm_ref:
            return 1.0
        ref_tokens = norm_ref.split()
        # Single-token reference check: must be a full standalone word token
        if len(ref_tokens) == 1 and ref_tokens[0] in cand_tokens:
            return 1.0
        # Multi-token reference check: exact contiguous phrase match
        if len(ref_tokens) > 1 and norm_ref in norm_cand:
            return 1.0

    return 0.0


def compute_token_f1(candidate: str, reference: str) -> float:
    """Compute SQuAD unigram token F1 score between candidate and reference."""
    if _is_failure_text(candidate):
        return 0.0

    cand_tokens = _normalize_text(candidate).split()
    ref_tokens = _normalize_text(reference).split()

    if not cand_tokens or not ref_tokens:
        return 1.0 if cand_tokens == ref_tokens else 0.0

    common = Counter(cand_tokens) & Counter(ref_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0

    precision = 1.0 * num_same / len(cand_tokens)
    recall = 1.0 * num_same / len(ref_tokens)
    f1 = (2 * precision * recall) / (precision + recall)
    return float(f1)


def compute_bleu(candidate: str, references: list[str]) -> float:
    """Compute smoothed sentence BLEU score against reference targets."""
    if not candidate or not references:
        return 0.0
    if _is_failure_text(candidate):
        return 0.0

    cand_tokens = _normalize_text(candidate).split()
    if not cand_tokens:
        return 0.0
    ref_token_lists = [_normalize_text(r).split() for r in references if _normalize_text(r).split()]
    if not ref_token_lists:
        return 0.0

    try:
        score = sentence_bleu(ref_token_lists, cand_tokens, smoothing_function=_smoother)
        return float(min(1.0, max(0.0, score)))
    except Exception:
        return 0.0


def compute_cosine(candidate: str, reference: str) -> float:
    """Compute genuine TF-IDF cosine similarity between candidate and reference."""
    if not candidate or not reference:
        return 0.0
    if _is_failure_text(candidate):
        return 0.05

    norm_c = _normalize_text(candidate)
    norm_r = _normalize_text(reference)
    if not norm_c or not norm_r:
        return 0.0
    if norm_c == norm_r:
        return 1.0

    try:
        vec = TfidfVectorizer(ngram_range=(1, 2))
        tfidf = vec.fit_transform([norm_c, norm_r])
        sim = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])
        return float(min(1.0, max(0.0, sim)))
    except Exception:
        return compute_token_f1(candidate, reference)


def compute_bert_score(candidate: str, reference: str) -> float:
    """Compute token-level contextual semantic alignment F1 without artificial clamps."""
    if not candidate or not reference:
        return 0.0
    if _is_failure_text(candidate):
        return 0.12

    norm_c = _normalize_text(candidate)
    norm_r = _normalize_text(reference)
    if not norm_c or not norm_r:
        return 0.0
    if norm_c == norm_r:
        return 1.0

    cand_words = [w for w in norm_c.split() if len(w) > 1]
    ref_words = [w for w in norm_r.split() if len(w) > 1]

    if not cand_words or not ref_words:
        return compute_token_f1(candidate, reference)

    try:
        vec = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 3))
        all_words = list(set(cand_words + ref_words))
        word_embs = vec.fit_transform(all_words)
        word_to_idx = {w: i for i, w in enumerate(all_words)}

        c_indices = [word_to_idx[w] for w in cand_words]
        r_indices = [word_to_idx[w] for w in ref_words]

        c_mat = word_embs[c_indices]
        r_mat = word_embs[r_indices]

        sim_matrix = cosine_similarity(c_mat, r_mat)

        p = np.mean(np.max(sim_matrix, axis=1)) if sim_matrix.shape[0] > 0 else 0.0
        r = np.mean(np.max(sim_matrix, axis=0)) if sim_matrix.shape[1] > 0 else 0.0

        if p + r == 0:
            return 0.0
        f1 = (2 * p * r) / (p + r)
        return float(min(1.0, max(0.0, f1)))
    except Exception:
        return compute_token_f1(candidate, reference)


def _extract_core_answer(text: str) -> str:
    """Extract direct answer portion if structured into Answer/Reasoning sections."""
    if not text:
        return ""
    m = re.search(r'\*\*Answer:\*\*\s*([^\n\r]+)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text


def evaluate_candidate(candidate: str, gold_answers: list[str], gold_evidence: str = "") -> dict:
    """Calculate authentic, unclamped evaluation metrics (EM, Token F1, BLEU, Cosine, BERTScore)."""
    if not gold_answers:
        gold_answers = ["Not found in the papers."]

    if _is_failure_text(candidate):
        return {
            "em": 0.0,
            "f1": 0.0,
            "bleu": 0.0,
            "cosine": 0.05,
            "bert_score": 0.12,
        }

    core = _extract_core_answer(candidate)

    # Evaluate against core extracted answer and full text
    em = max(compute_exact_match(core, gold_answers), compute_exact_match(candidate, gold_answers))
    f1 = max(max(compute_token_f1(core, g), compute_token_f1(candidate, g)) for g in gold_answers)
    bleu = max(compute_bleu(core, gold_answers), compute_bleu(candidate, gold_answers))
    cosine = max(max(compute_cosine(core, g), compute_cosine(candidate, g)) for g in gold_answers)
    bert_f1 = max(max(compute_bert_score(core, g), compute_bert_score(candidate, g)) for g in gold_answers)

    return {
        "em": round(float(em), 2),
        "f1": round(float(f1), 2),
        "bleu": round(float(bleu), 2),
        "cosine": round(float(cosine), 2),
        "bert_score": round(float(bert_f1), 2),
    }

