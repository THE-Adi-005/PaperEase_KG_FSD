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
│   React UI   │────▶│   FastAPI    │────▶│   Ollama     │
│  (Vite)      │ SSE │   Backend    │ API │  qwen2.5:7b  │
│  Port 5173   │◀────│   Port 8000  │◀────│  Port 11434  │
└──────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────┼───────┐
                    ▼      ▼       ▼
              ┌─────────┐ ┌──────┐ ┌──────────┐
              │  Neo4j  │ │GROBID│ │MiniLM-L6 │
              │  7687   │ │ 8070 │ │  (CPU)   │
              └─────────┘ └──────┘ └──────────┘
```

## Prerequisites

1. **Docker Desktop** (for Neo4j + GROBID)
   - Requires WSL2 on Windows: `wsl --install` (admin PowerShell, then reboot)
   - Download: https://www.docker.com/products/docker-desktop/

2. **Ollama** (for LLM inference)
   - Download: https://ollama.com/download
   - After install: `ollama pull qwen2.5:7b`

3. **Python 3.11+** and **Node.js 18+**

## Quick Start

```bash
# 1. Start Neo4j + GROBID
docker-compose up -d

# 2. Start Ollama (separate terminal or on Machine A)
ollama serve
# In another terminal: ollama pull qwen2.5:7b

# 3. Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 4. Frontend
cd frontend
npm install
npm run dev

# 5. Open http://localhost:5173
```

## Environment Configuration

Copy `.env.example` to `.env` and adjust:
```env
# For split setup (LLM on Machine A):
OLLAMA_BASE_URL=http://<machine-a-ip>:11434/v1
```

## Evaluation

```bash
python eval/evaluate.py --qa_file eval/qa_sets/grounding_paper.json
```

## Project Structure

```
├── backend/           # FastAPI + services
│   ├── app/
│   │   ├── main.py           # App entry
│   │   ├── config.py         # Settings
│   │   ├── routers/          # API endpoints
│   │   ├── services/         # Core logic
│   │   │   ├── agent.py      # ReACT reasoning
│   │   │   ├── kg_builder.py # KG construction
│   │   │   └── lazy_completion.py  # Novel contribution
│   │   ├── models/           # Pydantic + Neo4j schema
│   │   └── utils/            # TEI + table parsers
├── frontend/          # React + Vite
│   └── src/
│       ├── components/       # UI components
│       └── hooks/            # SSE streaming
├── eval/              # Evaluation pipeline
└── docker-compose.yml # Infrastructure
```
