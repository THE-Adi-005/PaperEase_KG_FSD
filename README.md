# KG Paper Assistant

## Knowledge-Graph-Grounded Research Paper QA System

A full-stack application that builds knowledge graphs from research papers and answers questions using KG-grounded reasoning with full traceability.

**Based on:** Amayuelas et al., *"Grounding LLM Reasoning with Knowledge Graphs"* (NeurIPS 2025 Workshop)

### Key Features
- 📄 Upload research paper PDFs → automatic KG construction
- 🧠 Agent + CoT ReACT reasoning loop grounded in the KG
- ⚡ Query-driven lazy graph completion (novel contribution)
- 📊 Self-consistency extraction filtering
- 🔍 Live reasoning trace streaming (SSE)
- 🕸️ Interactive subgraph visualization (Cytoscape.js)
- 📈 Cross-paper comparison with per-claim attribution
- 📋 Table-to-triple structured extraction

---

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   React UI   │────▶│   FastAPI    │────▶│ LLM Provider │
│  (Vite)      │ SSE │   Backend    │ API │ (Groq/Ollama)│
│  Port 5173   │◀────│   Port 8000  │◀────│              │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                     ┌──────┼───────┐
                     ▼      ▼       ▼
               ┌─────────┐ ┌────────┐ ┌──────────┐
               │  Neo4j  │ │ Python │ │MiniLM-L6 │
               │  7687   │ │ Parser │ │  (CPU)   │
               └─────────┘ └────────┘ └──────────┘
```

## Setup & Execution
Please see [HOW_TO_RUN_AND_EXECUTE.md](HOW_TO_RUN_AND_EXECUTE.md) for detailed, step-by-step instructions on setting up the environment, installing dependencies, and running the application.

## Detailed Description
Please see [PROJECT_DESCRIPTION.md](PROJECT_DESCRIPTION.md) for a comprehensive overview of the architecture, workflow, and concepts used in this project.

## Project Structure

```
├── backend/           # FastAPI + services
│   ├── app/
│   │   ├── main.py           # App entry
│   │   ├── config.py         # Settings
│   │   ├── routers/          # API endpoints
│   │   ├── services/         # Core logic (Agent, LLM client, Neo4j)
│   │   ├── models/           # Pydantic + Neo4j schema
│   │   └── utils/            # Unstructured PDF & table parsers
├── frontend/          # React + Vite
│   └── src/
│       ├── components/       # UI components
│       └── hooks/            # SSE streaming
├── eval/              # Evaluation pipeline
└── HOW_TO_RUN_AND_EXECUTE.md # Run instructions
```
