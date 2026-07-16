"""Configuration loaded from .env file."""

from pydantic_settings import BaseSettings
from pathlib import Path
import os


class Settings(BaseSettings):
    # LLM (Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL: str = "qwen2.5:7b"

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "kg_paper_2025"

    # GROBID
    GROBID_URL: str = "http://localhost:8070"

    # Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Paths (relative to backend/)
    UPLOAD_DIR: str = "./uploads"
    FIGURES_DIR: str = "./figures"

    # Agent config
    AGENT_MAX_STEPS: int = 8
    EXTRACTION_TEMPERATURE: float = 0.6
    EXTRACTION_RUNS: int = 2  # Self-consistency: run extraction N times
    SAME_AS_THRESHOLD: float = 0.85

    model_config = {
        "env_file": os.path.join(Path(__file__).resolve().parent.parent.parent, ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()

# Ensure directories exist
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.FIGURES_DIR).mkdir(parents=True, exist_ok=True)
