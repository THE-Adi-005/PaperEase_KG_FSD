"""Configuration loaded from .env file."""

from pydantic_settings import BaseSettings
from pathlib import Path
import os


class Settings(BaseSettings):
    # LLM Settings (Defaults to local Ollama, can be swapped to Groq/OpenRouter)
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    LLM_MODEL: str = "qwen2.5:7b"
    LLM_API_KEY: str = "ollama"  # placeholder, required by OpenAI client

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "kg_paper_2025"

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
    SECTION_TEXT_LIMIT: int = 3000  # Max chars per section for extraction

    # Schema profile & ablation knobs
    CONFIG_ID: str = "default"          # Default namespace for semantic entities & edges
    ENABLE_SAME_AS: bool = True         # Toggle cross-paper SAME_AS linking
    SCHEMA_PROFILE: str = "R7"          # Active profile: R3 | R5 | R7 | R10
    MAX_TRIPLES_PER_SECTION: int = 0    # 0 = uncapped; positive N caps triples per section
    VOTE_FRACTION: float = 0.5          # pass if count >= ceil(N * VOTE_FRACTION)
    ENFORCE_TYPE_SIGNATURES: bool = False  # Reject triples violating head/tail type constraints
    ALLOW_DYNAMIC_RELATIONS: bool = True   # Accept LLM relations not in active profile
    DROP_GENERIC: bool = False             # Drop triples where head or tail is a generic placeholder

    # Multi-agent pipeline config
    MULTI_AGENT_ENABLED: bool = True
    VERIFIER_CONFIDENCE_THRESHOLD: float = 0.6  # Below this → revision loop
    MAX_REVISION_LOOPS: int = 2  # Max re-retrieval attempts

    model_config = {
        "env_file": os.path.join(Path(__file__).resolve().parent.parent.parent, ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()

# Ensure directories exist
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.FIGURES_DIR).mkdir(parents=True, exist_ok=True)
