# Project Description: KG Paper Assistant

## 1. What This Project Is About
The **KG Paper Assistant** is a Full-Stack application designed to solve a major problem in academic research: extracting, connecting, and reasoning over factual information across hundreds of complex research papers. 

Traditional Retrieval-Augmented Generation (RAG) systems simply chunk text and use vector search, which often leads to hallucinations and fails when asked complex, multi-hop comparative questions (e.g., "Which method achieved the highest accuracy on the MMLU dataset?"). 

This project solves that by dynamically constructing a **Knowledge Graph (KG)** from uploaded PDFs and using an AI Agent that actively traverses this graph to find answers. This grounds the AI in absolute facts, providing 100% traceability for its reasoning.

## 2. Core Capabilities
- **Automated Graph Construction:** Upload a PDF, and the system natively parses the text and tables, using an LLM to extract factual "Triples" (Head Entity -> Relation -> Tail Entity).
- **Agentic Reasoning (ReACT):** The AI doesn't just read text; it uses tools to generate Cypher queries and traverse the database step-by-step.
- **Cross-Paper Linking:** The system uses embeddings to identify when two different papers are talking about the same concept, linking them together to form a massive, interconnected web of knowledge.
- **Interpretability:** As the Agent thinks and searches, its reasoning trace is streamed live to the UI, alongside an interactive visual representation of the graph nodes it is currently looking at.

## 3. Architecture & Tech Stack

### The Backend (FastAPI / Python)
The brain of the operation. It exposes asynchronous APIs for uploading papers, querying the graph, and streaming Server-Sent Events (SSE) back to the frontend.
- **`unstructured` & `pdfplumber`:** Used to natively parse PDFs into clean text blocks and structured table data without relying on heavy external Java services.
- **Neo4j Graph Database:** Stores all extracted entities (Methods, Metrics, Datasets, Authors) and their relationships.
- **Groq / Ollama (LLM API):** The backend communicates with an OpenAI-compatible LLM endpoint to extract data during ingestion and to power the ReACT Agent during QA.
- **Sentence-Transformers:** Used locally on the CPU to generate embeddings for concepts. When a new concept is extracted, cosine similarity is used to link it (`SAME_AS`) to existing concepts in the database.

### The Frontend (React / Vite)
A fast, modern user interface.
- **UI Components:** Built with React, featuring a Paper Uploader, a chat-style QA interface, and a live reasoning trace log.
- **Cytoscape.js:** A graph visualization library used to render the specific sub-graph the AI Agent traversed to arrive at its answer.

## 4. End-to-End Workflow

### Phase 1: Ingestion & KG Construction
1. **Upload:** User uploads `paper.pdf` via the React frontend.
2. **Parsing:** The FastAPI backend receives the file. `unstructured` breaks it into Sections. `pdfplumber` extracts raw table grids.
3. **Extraction:** The text of each section is sent to the LLM with a strict prompt: *"Extract factual triples (e.g., [BERT, EVALUATED_ON, SQuAD])."* 
4. **Self-Consistency:** The extraction runs multiple times. Only facts the LLM agrees on multiple times are kept, filtering out hallucinations.
5. **Storage & Linking:** The triples are saved to Neo4j. Embeddings are generated to link identical concepts across different papers.

### Phase 2: Querying & Reasoning
1. **Ask a Question:** User asks, *"How does Paper A's method compare to Paper B?"*
2. **ReACT Loop:** The backend initializes an Agent. 
   - **Thought:** The Agent decides it needs to find Paper A's method.
   - **Action:** It uses the `RetrieveNode` tool.
   - **Observation:** The backend executes a Cypher query in Neo4j and returns the connected Method node.
3. **Lazy Graph Completion:** If the Agent hits a dead end (a sparse part of the graph), it triggers a fallback to read the raw text of the paper, extracts the missing relationship on the fly, updates the graph, and continues.
4. **Final Answer:** Once it gathers enough facts, it synthesizes a final answer and streams it to the frontend, along with the graph visualization of its journey.
