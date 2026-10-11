"""QA evaluation runner — eval/run_qa.py

Usage:
    python -m eval.run_qa --system rag
    python -m eval.run_qa --system kg --config cfg_base --lazy off
    python -m eval.run_qa --system kg --config cfg_base --lazy on
    python -m eval.run_qa --system kg --config cfg_r3 --lazy off --limit 20

Outputs per system_id:
    results/qa/<system_id>/predictions.jsonl   (one JSON per line, appended)
    results/qa/<system_id>/metrics.json        (aggregate stats)
    results/all_runs.csv                       (one row per system_id, updated)
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Repo / sys.path setup ────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from eval.corpus import get_eval_papers
from eval.scoring import is_correct, is_abstain, evidence_hit, bootstrap_ci

_RESULTS_DIR = _REPO_ROOT / "results"
_ALL_RUNS_CSV = _RESULTS_DIR / "all_runs.csv"

_ALL_RUNS_COLS = [
    "system_id", "system", "config", "lazy", "n",
    "acc", "acc_lo", "acc_hi",
    "acc_lookup", "acc_multihop", "acc_aggregation", "acc_cross_paper", "acc_unanswerable",
    "acc_table", "acc_manual",
    "abstain_rate_unanswerable", "false_abstain_rate_answerable",
    "evidence_hit", "mean_steps", "mean_latency", "mean_lazy_triggers",
    "total_nodes", "total_edges", "avg_degree", "graph_density",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_qa_set(path: Path) -> list[dict]:
    with open(path) as f:
        qs = json.load(f)
    return qs


def _stratified_sample(qs: list[dict], limit: int, seed: int = 0) -> list[dict]:
    """Stable stratified sample by type."""
    by_type: dict[str, list] = defaultdict(list)
    for q in qs:
        by_type[q.get("type", "other")].append(q)
    rng = random.Random(seed)
    for lst in by_type.values():
        lst.sort(key=lambda q: q.get("id", ""))
        rng.shuffle(lst)
    types = sorted(by_type.keys())
    result = []
    i = 0
    while len(result) < limit:
        t = types[i % len(types)]
        lst = by_type[t]
        idx = len(result) // len(types)
        if idx < len(lst):
            result.append(lst[idx])
        i += 1
        if i > limit * len(types) * 2:
            break
    return result[:limit]


def _load_graph_stats(config: Optional[str]) -> dict:
    if not config:
        return {}
    p = _RESULTS_DIR / config / "graph_stats.json"
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return {}


def _upsert_csv(row: dict):
    """Insert or update a row in all_runs.csv by system_id."""
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    if _ALL_RUNS_CSV.exists():
        with open(_ALL_RUNS_CSV, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    # Replace existing row or append
    replaced = False
    for i, r in enumerate(rows):
        if r.get("system_id") == row["system_id"]:
            rows[i] = {c: row.get(c, r.get(c, "")) for c in _ALL_RUNS_COLS}
            replaced = True
            break
    if not replaced:
        rows.append({c: row.get(c, "") for c in _ALL_RUNS_COLS})
    with open(_ALL_RUNS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_ALL_RUNS_COLS)
        writer.writeheader()
        writer.writerows(rows)


# ── Core runner ───────────────────────────────────────────────────────────────

async def run_system(
    system: str,
    config: Optional[str],
    lazy: bool,
    qa_questions: list[dict],
    max_steps: int,
    out_dir: Path,
) -> dict:
    """Run all questions through the system, write predictions.jsonl, return raw results."""
    from app.services.neo4j_client import neo4j_service
    await neo4j_service.connect()

    out_dir.mkdir(parents=True, exist_ok=True)
    pred_path = out_dir / "predictions.jsonl"

    # Load already-done question ids for resumability
    done_ids: set[str] = set()
    if pred_path.exists():
        with open(pred_path) as f:
            for line in f:
                try:
                    done_ids.add(json.loads(line)["id"])
                except Exception:
                    pass
    if done_ids:
        logger.info(f"Resuming: {len(done_ids)} questions already done")

    results = []
    with open(pred_path, "a") as pred_f:
        for q in qa_questions:
            qid = q.get("id", "")
            if qid in done_ids:
                # Re-load from file for metrics
                continue

            paper_ids = q.get("paper_ids", [])
            question = q["question"]
            gold = q.get("gold_answers", [])
            answerable = q.get("answerable", True)
            qtype = q.get("type", "other")
            qsource = q.get("source", "manual")

            t0 = time.perf_counter()
            answer = ""
            steps = 0
            observations = []
            n_lazy = 0
            trace = ""

            try:
                if system == "rag":
                    from eval.rag_baseline import answer_rag
                    res = await answer_rag(question, paper_ids)
                    answer = res["answer"]
                    steps = 1
                    observations = res.get("contexts", [])
                    latency = res.get("latency_s", time.perf_counter() - t0)
                else:
                    from app.services.agent import run_agent_eval
                    res = await run_agent_eval(
                        question=question,
                        paper_ids=paper_ids,
                        config_id=config,
                        max_steps=max_steps,
                        lazy_completion=lazy,
                        persist_lazy=False,
                        temperature=0.0,
                    )
                    answer = res["answer"]
                    steps = res["steps"]
                    observations = res["observations"]
                    n_lazy = res["n_lazy_triggers"]
                    trace = res["trace"]
                    latency = time.perf_counter() - t0
            except Exception as e:
                logger.error(f"Question {qid} failed: {e}")
                answer = "Not found in the papers."
                latency = time.perf_counter() - t0

            obs_text = " ".join(str(o) for o in observations)
            correct = is_correct(answer, gold, answerable)
            abstained = is_abstain(answer)
            ev_hit = evidence_hit(obs_text, gold) if gold else False

            row = {
                "id": qid,
                "type": qtype,
                "source": qsource,
                "paper_ids": paper_ids,
                "question": question,
                "gold_answers": gold,
                "answerable": answerable,
                "answer": answer,
                "correct": correct,
                "abstained": abstained,
                "evidence_hit": ev_hit,
                "steps": steps,
                "latency_s": round(latency, 3),
                "n_lazy_triggers": n_lazy,
                "trace": trace,
            }
            pred_f.write(json.dumps(row) + "\n")
            pred_f.flush()
            results.append(row)
            logger.info(
                f"[{qid}] correct={correct} abstained={abstained} steps={steps} lat={latency:.1f}s"
            )

    # Load ALL predictions (including resumed ones) for metrics
    all_preds = []
    with open(pred_path) as f:
        for line in f:
            try:
                all_preds.append(json.loads(line))
            except Exception:
                pass

    await neo4j_service.close()
    return _compute_metrics(all_preds)


def _compute_metrics(preds: list[dict]) -> dict:
    """Compute aggregate metrics from predictions list."""
    if not preds:
        return {}

    correct_flags = [int(p["correct"]) for p in preds]
    acc, acc_lo, acc_hi = bootstrap_ci(correct_flags)

    by_type: dict[str, list] = defaultdict(list)
    by_source: dict[str, list] = defaultdict(list)
    for p in preds:
        by_type[p.get("type", "other")].append(int(p["correct"]))
        by_source[p.get("source", "manual")].append(int(p["correct"]))

    # Abstain rates
    unanswerable = [p for p in preds if not p.get("answerable", True)]
    answerable = [p for p in preds if p.get("answerable", True)]
    abstain_rate_unan = (
        sum(1 for p in unanswerable if p["abstained"]) / len(unanswerable)
        if unanswerable else 0.0
    )
    false_abstain_rate = (
        sum(1 for p in answerable if p["abstained"]) / len(answerable)
        if answerable else 0.0
    )

    ev_flags = [int(p.get("evidence_hit", False)) for p in preds if p.get("gold_answers")]
    ev_hit = sum(ev_flags) / len(ev_flags) if ev_flags else 0.0

    mean_steps = sum(p.get("steps", 0) for p in preds) / len(preds)
    mean_latency = sum(p.get("latency_s", 0.0) for p in preds) / len(preds)
    mean_lazy = sum(p.get("n_lazy_triggers", 0) for p in preds) / len(preds)

    return {
        "n": len(preds),
        "acc": round(acc, 4),
        "acc_lo": round(acc_lo, 4),
        "acc_hi": round(acc_hi, 4),
        "acc_by_type": {t: round(sum(v)/len(v), 4) for t, v in by_type.items()},
        "acc_by_source": {s: round(sum(v)/len(v), 4) for s, v in by_source.items()},
        "abstain_rate_unanswerable": round(abstain_rate_unan, 4),
        "false_abstain_rate_answerable": round(false_abstain_rate, 4),
        "evidence_hit": round(ev_hit, 4),
        "mean_steps": round(mean_steps, 2),
        "mean_latency": round(mean_latency, 2),
        "mean_lazy_triggers": round(mean_lazy, 3),
    }


# ── Main ─────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="QA evaluation runner")
    parser.add_argument("--system", choices=["kg", "rag"], required=True)
    parser.add_argument("--config", type=str, default=None,
                        help="config_id for KG system (e.g. cfg_base)")
    parser.add_argument("--lazy", choices=["on", "off"], default="off",
                        help="Enable lazy completion (KG only)")
    parser.add_argument("--qa", type=str, default=None,
                        help="Path to QA set JSON (default: eval/qa_set.json)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max questions (stratified sample, seed 0)")
    parser.add_argument("--max-steps", type=int, default=6,
                        help="Max agent steps per question (default 6)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    # Resolve QA file
    qa_path = Path(args.qa) if args.qa else _REPO_ROOT / "eval" / "qa_set.json"
    if not qa_path.exists():
        logger.error(f"QA file not found: {qa_path}")
        sys.exit(1)

    qa_all = _load_qa_set(qa_path)
    if args.limit:
        qa_questions = _stratified_sample(qa_all, args.limit)
    else:
        qa_questions = qa_all

    lazy = args.lazy == "on"
    config = args.config if args.system == "kg" else None
    system_id = "rag" if args.system == "rag" else f"kg_{config}_{'lazy' if lazy else 'nolazy'}"

    out_dir = _RESULTS_DIR / "qa" / system_id
    logger.info(f"system_id={system_id}  questions={len(qa_questions)}  out={out_dir}")

    metrics = await run_system(
        system=args.system,
        config=config,
        lazy=lazy,
        qa_questions=qa_questions,
        max_steps=args.max_steps,
        out_dir=out_dir,
    )

    # Write metrics.json
    metrics_path = out_dir / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Wrote metrics to {metrics_path}")

    # Load graph stats
    gs = _load_graph_stats(config)

    # Upsert all_runs.csv row
    by_type = metrics.get("acc_by_type", {})
    by_source = metrics.get("acc_by_source", {})
    csv_row = {
        "system_id": system_id,
        "system": args.system,
        "config": config or "",
        "lazy": "on" if lazy else "off",
        "n": metrics.get("n", 0),
        "acc": metrics.get("acc", ""),
        "acc_lo": metrics.get("acc_lo", ""),
        "acc_hi": metrics.get("acc_hi", ""),
        "acc_lookup": by_type.get("lookup", ""),
        "acc_multihop": by_type.get("multihop", ""),
        "acc_aggregation": by_type.get("aggregation", ""),
        "acc_cross_paper": by_type.get("cross_paper", ""),
        "acc_unanswerable": by_type.get("unanswerable", ""),
        "acc_table": by_type.get("table", ""),
        "acc_manual": by_source.get("manual", ""),
        "abstain_rate_unanswerable": metrics.get("abstain_rate_unanswerable", ""),
        "false_abstain_rate_answerable": metrics.get("false_abstain_rate_answerable", ""),
        "evidence_hit": metrics.get("evidence_hit", ""),
        "mean_steps": metrics.get("mean_steps", ""),
        "mean_latency": metrics.get("mean_latency", ""),
        "mean_lazy_triggers": metrics.get("mean_lazy_triggers", ""),
        "total_nodes": gs.get("total_nodes", ""),
        "total_edges": gs.get("total_edges", ""),
        "avg_degree": gs.get("avg_degree", ""),
        "graph_density": gs.get("graph_density", ""),
    }
    _upsert_csv(csv_row)
    logger.info(f"Updated {_ALL_RUNS_CSV}")

    # Summary line
    print(
        f"\n[{system_id}] n={metrics.get('n')} acc={metrics.get('acc'):.3f} "
        f"[{metrics.get('acc_lo'):.3f},{metrics.get('acc_hi'):.3f}] "
        f"ev_hit={metrics.get('evidence_hit'):.3f} "
        f"steps={metrics.get('mean_steps'):.1f} "
        f"lat={metrics.get('mean_latency'):.1f}s"
    )


if __name__ == "__main__":
    asyncio.run(main())
