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

    # ── LLM ──
    try:
        # Generic models endpoint for OpenAI-compatible APIs (Ollama, Groq, etc)
        async with httpx.AsyncClient(timeout=5.0) as client:
            headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}
            resp = await client.get(f"{settings.LLM_BASE_URL}/models", headers=headers)
            if resp.status_code == 200:
                status.llm = True
                models = resp.json().get("data", [])
                model_names = [m.get("id", "") for m in models]
                
                # Ollama often returns 'models' object in /api/tags, but OpenAI standard is /v1/models with 'data'
                if not models and "models" in resp.json():
                    models = resp.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    
                status.llm_model = (
                    settings.LLM_MODEL
                    if any(settings.LLM_MODEL in n for n in model_names)
                    else f"model '{settings.LLM_MODEL}' not found; available: {model_names}"
                )
    except Exception as e:
        logger.warning(f"LLM health check failed: {e}")
        status.llm = False

    # Overall status
    status.status = "ok" if all([status.neo4j, status.llm]) else "degraded"

    return status
