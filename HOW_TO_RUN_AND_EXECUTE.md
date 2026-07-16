# How to Run and Execute the KG Paper Assistant

This guide explains how to set up the project natively (without Docker), how the execution pipeline works, and how to interact with it.

---

## 1. Native Setup Guide (No Docker)

Because you are running this natively, you need to set up the four core services directly on your machine.

### Prerequisites
1. **Python 3.10+** (For the FastAPI Backend)
2. **Node.js & npm** (For the React Frontend)
3. **Java JDK 17** (Required for Neo4j and GROBID)

### Service 1: Ollama (LLM)
1. Download **Ollama** from `ollama.com`.
2. Open a terminal and run: `ollama run qwen2.5:7b` (This downloads and starts the local AI model).

### Service 2: Neo4j (Graph Database)
1. Download **Neo4j Community Edition** (ZIP) for Windows from the Neo4j Download Center.
2. Extract the folder.
3. Download the **APOC plugin** (`.jar` file) from the APOC GitHub releases and put it in the `plugins` folder.
4. Edit `conf/neo4j.conf` and add: `dbms.security.procedures.unrestricted=apoc.*`
5. Run the server: Open terminal in the `bin` folder and run `neo4j.bat console`.
6. Open `http://localhost:7474`, login with `neo4j` / `neo4j`, and change the password to `kg_paper_2025`.

### Service 3: GROBID (PDF Parser)
1. Download **GROBID 0.8.x** (ZIP) from their GitHub releases.
2. Extract the folder.
3. Open a terminal in the folder and run: `./gradlew run`. (Wait for it to fully start on port 8070).

### Service 4: The Application (Backend + Frontend)
1. **Backend**: Open terminal in `FSD_project/backend`.
   - `python -m venv venv`
   - `.\venv\Scripts\activate`
   - `pip install -r requirements.txt`
2. **Frontend**: Open terminal in `FSD_project/frontend`.
   - `npm install`
3. **Run**: Open terminal in `FSD_project` and run `.\start.ps1`.

---

## 2. Execution Pipeline (How it works)

The application is a Full-Stack system that converts unstructured PDFs into a queryable Knowledge Graph.

### Phase A: Data Ingestion (Input)
1. **User Input**: You open the React app (`http://localhost:5173`) and use the **Paper Uploader** panel to select and upload a research paper (PDF).
2. **Parsing (GROBID)**: The FastAPI backend sends the PDF to GROBID, which reads the file and returns a structured XML file containing the Title, Authors, Abstract, Sections, and References.
3. **Knowledge Extraction (Ollama)**: The backend sends each section of the text to the local LLM (Ollama). The LLM is prompted to extract "Entities" (Methods, Datasets, Metrics) and "Relations" (Uses, Reports) from the text.
4. **Storage (Neo4j)**: The extracted entities and relations are saved as nodes and edges in the Neo4j graph database.

### Phase B: Question Answering (Interaction)
1. **User Input**: In the React app, you use the **Chat Panel** to ask a question (e.g., "What dataset was used in this paper?").
2. **Agent Loop (ReACT)**: The backend sends your question to the LLM agent. Instead of guessing the answer, the Agent has "Tools" it can use to search the Neo4j database. 
3. **Graph Traversal**: The Agent searches for keywords, looks at connected nodes, and traverses the graph until it finds the facts needed to answer your question.
4. **Output**: The answer is streamed back to the frontend along with a **Reasoning Trace** (showing you exactly which nodes and sections of the paper it looked at to get the answer). You will also see a visual representation of the graph on the right side of the screen.
