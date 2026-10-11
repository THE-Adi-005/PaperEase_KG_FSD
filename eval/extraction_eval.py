"""eval/extraction_eval.py — evaluate extracted KG triples against SciERC benchmark.

Evaluates entity extraction and relation-agnostic entity-pair extraction against
gold annotations in backend/data/scierc/test.json.

NOTE: Relation-agnostic pair score is a proxy because SciERC relation semantics
differ from the schema profiles used in this project.

Usage:
    python -m eval.extraction_eval configs/cfg_base.yaml
    python -m eval.extraction_eval configs/cfg_base.yaml configs/cfg_r3.yaml configs/cfg_r10.yaml
"""

import argparse
import csv
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import yaml
from app.config import settings
from app.schema_profiles import PROFILES
from app.services.kg_builder import filter_runs
from eval.cache import get_runs

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("extraction_eval")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCIERC_TEST_PATH = PROJECT_ROOT / "backend" / "data" / "scierc" / "test.json"
RESULTS_DIR = PROJECT_ROOT / "results"
ALL_RUNS_CSV = RESULTS_DIR / "all_runs.csv"

SCIERC_TYPE_MAPPING = {
    "Method": "Method",
    "Metric": "Metric",
    "Material": "Dataset",
    "Task": "Concept",
    "OtherScientificTerm": "Concept",
}


def normalize_text(s: str) -> str:
    """Normalize text: lowercase, remove non-alphanumeric, collapse whitespace."""
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(s.split())


def lenient_match(a: str, b: str) -> bool:
    """Check if strings match leniently.
    
    True if normalized strings are equal, or one contains the other and
    token-level Jaccard similarity is >= 0.5.
    """
    na = normalize_text(a)
    nb = normalize_text(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if na in nb or nb in na:
        toks_a = set(na.split())
        toks_b = set(nb.split())
        union = toks_a | toks_b
        if not union:
            return False
        jaccard = len(toks_a & toks_b) / len(union)
        return jaccard >= 0.5
    return False


def compute_prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """Compute precision, recall, and F1 score."""
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return round(p, 4), round(r, 4), round(f1, 4)


def load_scierc_docs(path: Path, n: int = 40) -> list[dict]:
    """Load first n documents with at least 3 annotated entities."""
    if not path.exists():
        raise FileNotFoundError(f"SciERC test file not found at {path}")
    docs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            ner_count = sum(len(s) for s in doc.get("ner", []))
            if ner_count >= 3:
                tokens = [tok for sent in doc.get("sentences", []) for tok in sent]
                docs.append({
                    "doc_key": doc["doc_key"],
                    "tokens": tokens,
                    "ner": doc.get("ner", []),
                    "relations": doc.get("relations", []),
                })
                if len(docs) >= n:
                    break
    return docs


def extract_gold_items(doc: dict) -> tuple[list[dict], list[tuple[str, str]]]:
    """Extract gold entities and gold relation pairs from a SciERC doc.
    
    Returns (gold_entities, gold_pairs) where:
      gold_entities: list of {"text": span_str, "type": mapped_type}
      gold_pairs: list of (span1_str, span2_str)
    """
    tokens = doc["tokens"]
    gold_entities = []
    for sent_ner in doc["ner"]:
        for item in sent_ner:
            start, end, label = item[0], item[1], item[2]
            if label == "Generic" or label not in SCIERC_TYPE_MAPPING:
                continue
            span_text = " ".join(tokens[start : end + 1])
            mapped_type = SCIERC_TYPE_MAPPING[label]
            gold_entities.append({"text": span_text, "type": mapped_type})

    gold_pairs = []
    for sent_rels in doc["relations"]:
        for rel in sent_rels:
            s1, e1, s2, e2 = rel[0], rel[1], rel[2], rel[3]
            span1 = " ".join(tokens[s1 : e1 + 1])
            span2 = " ".join(tokens[s2 : e2 + 1])
            gold_pairs.append((span1, span2))

    return gold_entities, gold_pairs


def evaluate_doc_entities(predicted_triples: list, gold_entities: list[dict]):
    """Evaluate predicted entities against gold entities for one document."""
    # Deduplicate predicted entities: heads and tails
    seen_ents = {}
    for t in predicted_triples:
        h_norm = normalize_text(t.head)
        if h_norm and h_norm not in seen_ents:
            seen_ents[h_norm] = {"text": t.head, "type": t.head_type}
        t_norm = normalize_text(t.tail)
        if t_norm and t_norm not in seen_ents:
            seen_ents[t_norm] = {"text": t.tail, "type": t.tail_type}
    pred_entities = list(seen_ents.values())

    # Type-agnostic matching
    unmatched_gold = list(range(len(gold_entities)))
    agnostic_tp = 0
    for pred in pred_entities:
        match_idx = None
        for g_idx in unmatched_gold:
            if lenient_match(pred["text"], gold_entities[g_idx]["text"]):
                match_idx = g_idx
                break
        if match_idx is not None:
            agnostic_tp += 1
            unmatched_gold.remove(match_idx)
    agnostic_fp = len(pred_entities) - agnostic_tp
    agnostic_fn = len(unmatched_gold)

    # Type-aware matching
    unmatched_gold_typed = list(range(len(gold_entities)))
    typed_tp = 0
    for pred in pred_entities:
        match_idx = None
        for g_idx in unmatched_gold_typed:
            g = gold_entities[g_idx]
            if lenient_match(pred["text"], g["text"]) and pred["type"].lower() == g["type"].lower():
                match_idx = g_idx
                break
        if match_idx is not None:
            typed_tp += 1
            unmatched_gold_typed.remove(match_idx)
    typed_fp = len(pred_entities) - typed_tp
    typed_fn = len(unmatched_gold_typed)

    return (agnostic_tp, agnostic_fp, agnostic_fn), (typed_tp, typed_fp, typed_fn)


def evaluate_doc_pairs(predicted_triples: list, gold_pairs: list[tuple[str, str]]):
    """Evaluate relation-agnostic entity pairs against gold relation pairs for one document."""
    unmatched_gold = list(range(len(gold_pairs)))
    tp = 0
    for t in predicted_triples:
        match_idx = None
        for g_idx in unmatched_gold:
            span1, span2 = gold_pairs[g_idx]
            if (lenient_match(t.head, span1) and lenient_match(t.tail, span2)) or \
               (lenient_match(t.head, span2) and lenient_match(t.tail, span1)):
                match_idx = g_idx
                break
        if match_idx is not None:
            tp += 1
            unmatched_gold.remove(match_idx)
    fp = len(predicted_triples) - tp
    fn = len(unmatched_gold)
    return tp, fp, fn


def update_all_runs_csv(row: dict):
    """Upsert extraction row into results/all_runs.csv."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    fieldnames = [
        "system_id", "system", "config", "lazy", "n",
        "acc", "acc_lo", "acc_hi",
        "acc_lookup", "acc_multihop", "acc_aggregation", "acc_cross_paper", "acc_unanswerable",
        "acc_table", "acc_manual",
        "abstain_rate_unanswerable", "false_abstain_rate_answerable",
        "evidence_hit", "mean_steps", "mean_latency", "mean_lazy_triggers",
        "total_nodes", "total_edges", "avg_degree", "graph_density",
        "ent_f1", "ent_p", "ent_r", "pair_f1", "pair_p", "pair_r", "triples_per_doc",
    ]

    if ALL_RUNS_CSV.exists():
        with open(ALL_RUNS_CSV, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                for fn in reader.fieldnames:
                    if fn not in fieldnames:
                        fieldnames.append(fn)
            rows = list(reader)

    replaced = False
    for i, r in enumerate(rows):
        if r.get("system_id") == row["system_id"]:
            r.update(row)
            replaced = True
            break
    if not replaced:
        rows.append(row)

    with open(ALL_RUNS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def evaluate_config(cfg_path: Path, docs: list[dict]) -> dict:
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    config_id = cfg.get("config_id")
    prompt_profile_name = cfg.get("prompt_profile", "R7")
    profile = PROFILES.get(prompt_profile_name, PROFILES["R7"])

    runs = int(cfg.get("runs", 3))
    vote_fraction = float(cfg.get("vote_fraction", 0.5))
    cap = int(cfg.get("cap", 0))
    enforce_signatures = bool(cfg.get("enforce_signatures", False))
    allow_dynamic = bool(cfg.get("allow_dynamic", False))
    drop_generic = bool(cfg.get("drop_generic", False))
    relation_subset = cfg.get("relation_subset")
    if relation_subset is not None:
        relation_subset = set(relation_subset)

    trunc = int(cfg.get("trunc", settings.SECTION_TEXT_LIMIT))
    temperature = float(cfg.get("temperature", 0.6))
    model = cfg.get("model", settings.LLM_MODEL)

    tot_agnostic = [0, 0, 0]  # tp, fp, fn
    tot_typed = [0, 0, 0]     # tp, fp, fn
    tot_pair = [0, 0, 0]      # tp, fp, fn
    total_triples = 0
    all_rel_types = set()

    for doc in docs:
        doc_key = doc["doc_key"]
        cached_runs = get_runs(
            paper_id="scierc",
            section_id=doc_key,
            prompt_profile=prompt_profile_name,
            trunc=trunc,
            temperature=temperature,
            model=model,
            max_runs=runs,
        )

        if cached_runs:
            triples = filter_runs(
                cached_runs,
                paper_id="scierc",
                section_id=doc_key,
                vote_fraction=vote_fraction,
                profile=profile,
                allow_dynamic=allow_dynamic,
                enforce_signatures=enforce_signatures,
                cap=cap,
                drop_generic=drop_generic,
            )
            if relation_subset is not None:
                triples = [t for t in triples if t.relation in relation_subset]
        else:
            triples = []

        total_triples += len(triples)
        for t in triples:
            all_rel_types.add(t.relation)

        gold_entities, gold_pairs = extract_gold_items(doc)
        agnostic, typed = evaluate_doc_entities(triples, gold_entities)
        for i in range(3):
            tot_agnostic[i] += agnostic[i]
            tot_typed[i] += typed[i]

        pair_tp, pair_fp, pair_fn = evaluate_doc_pairs(triples, gold_pairs)
        tot_pair[0] += pair_tp
        tot_pair[1] += pair_fp
        tot_pair[2] += pair_fn

    ent_p, ent_r, ent_f1 = compute_prf(*tot_agnostic)
    typed_p, typed_r, typed_f1 = compute_prf(*tot_typed)
    pair_p, pair_r, pair_f1 = compute_prf(*tot_pair)
    triples_per_doc = round(total_triples / len(docs), 2) if docs else 0.0

    metrics = {
        "config_id": config_id,
        "n_docs": len(docs),
        "total_triples": total_triples,
        "triples_per_doc": triples_per_doc,
        "distinct_relation_types": sorted(list(all_rel_types)),
        "ent_p": ent_p,
        "ent_r": ent_r,
        "ent_f1": ent_f1,
        "ent_p_typed": typed_p,
        "ent_r_typed": typed_r,
        "ent_f1_typed": typed_f1,
        "pair_p": pair_p,
        "pair_r": pair_r,
        "pair_f1": pair_f1,
    }

    out_dir = RESULTS_DIR / config_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "extraction_metrics.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    csv_row = {
        "system_id": f"extract_{config_id}",
        "system": "extraction",
        "config": config_id,
        "n": len(docs),
        "ent_f1": ent_f1,
        "ent_p": ent_p,
        "ent_r": ent_r,
        "pair_f1": pair_f1,
        "pair_p": pair_p,
        "pair_r": pair_r,
        "triples_per_doc": triples_per_doc,
    }
    update_all_runs_csv(csv_row)

    logger.info(
        "[%s] ent_F1=%.3f (P=%.3f R=%.3f) pair_F1=%.3f (P=%.3f R=%.3f) triples/doc=%.1f",
        config_id, ent_f1, ent_p, ent_r, pair_f1, pair_p, pair_r, triples_per_doc
    )
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Evaluate configs against SciERC gold annotations.")
    parser.add_argument("configs", nargs="+", help="Paths to config YAML files")
    parser.add_argument("--n", type=int, default=40, help="Number of SciERC docs (default: 40)")
    args = parser.parse_args()

    docs = load_scierc_docs(SCIERC_TEST_PATH, n=args.n)
    logger.info("Loaded %d SciERC evaluation documents.", len(docs))

    for cfg_str in args.configs:
        cfg_path = Path(cfg_str)
        if not cfg_path.is_absolute():
            cfg_path = PROJECT_ROOT / cfg_path
        if not cfg_path.exists():
            logger.error("Config not found: %s", cfg_path)
            continue
        evaluate_config(cfg_path, docs)


if __name__ == "__main__":
    main()
