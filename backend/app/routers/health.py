"""Health check endpoint — verifies Neo4j, Ollama, and GROBID connectivity."""

from fastapi import APIRouter
import httpx
import logging

from app.config import settings
from app.models.schemas import HealthStatus

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """Check connectivity to all backend services."""
    status = HealthStatus()

    # ── Neo4j ──
    try:
        from app.services.neo4j_client import neo4j_service
        result = await neo4j_service.verify_connectivity()
        status.neo4j = result
    except Exception as e:
        logger.warning(f"Neo4j health check failed: {e}")
        status.neo4j = False

    # ── Ollama ──
    try:
        # Use the base Ollama URL (not /v1) for model listing
        ollama_base = settings.OLLAMA_BASE_URL.replace("/v1", "")
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{ollama_base}/api/tags")
            if resp.status_code == 200:
                status.ollama = True
                models = resp.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                status.ollama_model = (
                    settings.OLLAMA_MODEL
                    if any(settings.OLLAMA_MODEL in n for n in model_names)
                    else f"model '{settings.OLLAMA_MODEL}' not found; available: {model_names}"
                )
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        status.ollama = False

    # ── GROBID ──
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.GROBID_URL}/api/isalive")
            status.grobid = resp.status_code == 200
    except Exception as e:
        logger.warning(f"GROBID health check failed: {e}")
        status.grobid = False

    # Overall status
    status.status = "ok" if all([status.neo4j, status.ollama, status.grobid]) else "degraded"

    return status
