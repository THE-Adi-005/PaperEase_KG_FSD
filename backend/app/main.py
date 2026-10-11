"""FastAPI application — main entry point.

Lifespan manages Neo4j driver and embedding model lifecycle.
CORS is configured for the Vite dev server.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # ── Startup ──
    logger.info("Starting KG Paper Assistant backend...")

    # Connect Neo4j
    from app.services.neo4j_client import neo4j_service
    await neo4j_service.connect()
    logger.info("Neo4j connected")

    # Pre-load embedding model (CPU, ~90MB download on first run)
    from app.services.embeddings import embedding_service
    embedding_service.load_model()
    logger.info("Embedding model loaded")

    yield

    # ── Shutdown ──
    await neo4j_service.close()
    logger.info("Shutdown complete")


app = FastAPI(
    title="KG Paper Assistant",
    description="Knowledge-Graph-Grounded Research Paper QA System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve extracted figures as static files
figures_path = Path(settings.FIGURES_DIR)
figures_path.mkdir(parents=True, exist_ok=True)
app.mount("/figures", StaticFiles(directory=str(figures_path)), name="figures")

# ── Register routers ──
from app.routers import health, papers, query, demo, eval, grounding, ablation, experiments

app.include_router(health.router, tags=["Health"])
app.include_router(papers.router, prefix="/api", tags=["Papers"])
app.include_router(query.router, prefix="/api", tags=["Query"])
app.include_router(demo.router, prefix="/api/demo", tags=["Demo"])
app.include_router(eval.router, prefix="/api/eval", tags=["Evaluation"])
app.include_router(grounding.router, prefix="/api/grounding", tags=["Grounding"])
app.include_router(ablation.router, prefix="/api/eval/ablation", tags=["Ablation"])
app.include_router(experiments.router, tags=["Experiments"])
