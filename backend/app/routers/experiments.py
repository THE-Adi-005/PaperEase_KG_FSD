"""Experiments router — read-only access to QA run results.

Endpoints:
    GET /api/experiments                             — all rows of all_runs.csv
    GET /api/experiments/{system_id}                — metrics + graph stats for one run
    GET /api/experiments/{system_id}/predictions    — paginated predictions.jsonl
"""

import csv
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/experiments", tags=["experiments"])

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # project root
_RESULTS = _REPO_ROOT / "results"


def _load_csv() -> list[dict]:
    p = _RESULTS / "all_runs.csv"
    if not p.exists():
        return []
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def _load_json(path: Path) -> Optional[dict]:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


@router.get("")
async def list_experiments():
    """Return all rows of all_runs.csv as a list of dicts."""
    rows = _load_csv()
    # Coerce numeric columns where possible
    numeric = {
        "n", "acc", "acc_lo", "acc_hi",
        "acc_lookup", "acc_multihop", "acc_aggregation",
        "acc_cross_paper", "acc_unanswerable", "acc_table", "acc_manual",
        "abstain_rate_unanswerable", "false_abstain_rate_answerable",
        "evidence_hit", "mean_steps", "mean_latency", "mean_lazy_triggers",
        "total_nodes", "total_edges", "avg_degree", "graph_density",
    }
    result = []
    for row in rows:
        out = {}
        for k, v in row.items():
            if k in numeric and v not in (None, ""):
                try:
                    out[k] = float(v)
                except ValueError:
                    out[k] = v
            else:
                out[k] = v
        result.append(out)
    return {"experiments": result, "count": len(result)}


@router.get("/{system_id}")
async def get_experiment(system_id: str):
    """Return metrics.json + graph_stats.json for a specific system_id."""
    qa_dir = _RESULTS / "qa" / system_id
    if not qa_dir.exists():
        raise HTTPException(status_code=404, detail=f"No results found for system_id='{system_id}'")

    metrics = _load_json(qa_dir / "metrics.json")
    if metrics is None:
        raise HTTPException(status_code=404, detail="metrics.json not found")

    # Try to find graph_stats.json — config is encoded in system_id: kg_<config>_nolazy
    graph_stats = None
    parts = system_id.split("_")
    if len(parts) >= 3 and parts[0] == "kg":
        # config = parts[1:-1] joined
        config = "_".join(parts[1:-1])
        graph_stats = _load_json(_RESULTS / config / "graph_stats.json")

    # Extraction metrics if present
    extraction_metrics = _load_json(qa_dir / "extraction_metrics.json")

    return {
        "system_id": system_id,
        "metrics": metrics,
        "graph_stats": graph_stats,
        "extraction_metrics": extraction_metrics,
    }


@router.get("/{system_id}/predictions")
async def get_predictions(
    system_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Return paginated rows from predictions.jsonl."""
    pred_path = _RESULTS / "qa" / system_id / "predictions.jsonl"
    if not pred_path.exists():
        raise HTTPException(status_code=404, detail="predictions.jsonl not found")

    rows = []
    with open(pred_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    total = len(rows)
    page = rows[offset: offset + limit]
    return {
        "system_id": system_id,
        "total": total,
        "offset": offset,
        "limit": limit,
        "predictions": page,
    }
