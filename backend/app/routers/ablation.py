"""Ablation experiment API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from app.services.ablation_runner import (
    run_ablation_experiment,
    get_experiment_status,
    get_available_experiments,
    collect_graph_stats,
)
from dataclasses import asdict

router = APIRouter()


class AblationRequest(BaseModel):
    experiment: str  # e.g. "extraction_runs", "extraction_temperature"
    paper_id: Optional[str] = None


@router.get("/available")
async def list_experiments():
    """List all available ablation experiments with their configurations."""
    return get_available_experiments()


@router.post("/run")
async def run_experiment(request: AblationRequest):
    """Run an ablation experiment (non-destructive — collects stats only).

    For a full destructive ablation (rebuild graph + QA eval), use /run-full.
    """
    try:
        result = await run_ablation_experiment(
            experiment_name=request.experiment,
            paper_id=request.paper_id,
        )
        return asdict(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Experiment failed: {str(e)}")


@router.get("/status")
async def experiment_status():
    """Check the status of a running ablation experiment."""
    return get_experiment_status()


@router.get("/graph-stats")
async def get_graph_stats(paper_id: Optional[str] = Query(None)):
    """Get current graph topology statistics."""
    stats = await collect_graph_stats(paper_id)
    return asdict(stats)
