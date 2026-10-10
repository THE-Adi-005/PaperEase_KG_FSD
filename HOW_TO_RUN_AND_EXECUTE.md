# How to Run and Execute the KG Paper Assistant

This guide provides end-to-end instructions on how to set up, run, and execute the Knowledge-Graph-Grounded Research Paper QA System on your local Windows machine **without Docker**. 

## 1. System Requirements Check

Before starting, ensure you have the following installed on your machine. 

### Required Software:
1. **Python 3.10+** (Required for the Backend and NLP tools)
   - *Status on your system:* Installed (Python 3.13.14) ✅
2. **Node.js (v18+) & npm** (Required for the React Frontend)
   - *Status on your system:* Installed (Node v22.17.1, npm 10.9.2) ✅
3. **Java JDK 17 or higher** (Required to run Neo4j natively)
   - *Status on your system:* Please verify by running `java -version` in your terminal. If not installed, download from [Oracle JDK 17](https://www.oracle.com/java/technologies/javase/jdk17-archive-downloads.html).

> [!NOTE]
> **Docker is NOT required** for this setup, as we have replaced the heavy GROBID container with native Python parsing and will run Neo4j directly on Windows.

---

## 2. End-to-End Setup Instructions

Follow these exact steps in order.

### Step 1: Set up Neo4j (Graph Database)

Since we are running natively on Windows without Docker, you need to download and run the Neo4j server manually.

1. **Download:** Go to the [Neo4j Download Center](https://neo4j.com/deployment-center/) and download the **Neo4j Community Edition (ZIP)** for Windows.
2. **Extract:** Extract the ZIP file to a folder (e.g., `C:\neo4j`).
3. **Install APOC Plugin:**
   - Download the **APOC plugin** `.jar` file that matches your Neo4j version from the [APOC GitHub Releases](https://github.com/neo4j/apoc/releases).
   - Place this `.jar` file inside the `plugins` folder of your extracted Neo4j directory (e.g., `C:\neo4j\plugins`).
4. **Configure Security:**
   - Open the `conf/neo4j.conf` file in a text editor.
   - Add the following line at the bottom to allow APOC procedures: 
     `dbms.security.procedures.unrestricted=apoc.*`
5. **Run the Database:**
   - Open PowerShell or Terminal.
   - Navigate to the bin folder: `cd C:\neo4j\bin`
   - Run the server: `.\neo4j.bat console`
6. **Set up Credentials:**
   - Open your browser and go to **http://localhost:7474**
   - Log in with the default username `neo4j` and password `neo4j`.
   - It will prompt you to change the password. Change it to **`kg_paper_2025`**.

### Step 2: Set up the Backend (FastAPI + AI)

Open a **new** PowerShell window (leave Neo4j running in the first one).

1. **Navigate to the Backend:**
   ```powershell
   cd c:\Users\amma\ADITHYA_23001\FSD_project\backend
   ```
2. **Create a Virtual Environment:**
   ```powershell
   python -m venv venv
   ```
3. **Activate the Environment:**
   ```powershell
   .\venv\Scripts\activate
   ```
4. **Install Dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```
5. **Configure the Environment (.env):**
   - Open `c:\Users\amma\ADITHYA_23001\FSD_project\.env` in an editor.
   - If you are using **Groq** for fast AI processing (Highly Recommended), set:
     ```env
     LLM_BASE_URL=https://api.groq.com/openai/v1
     LLM_MODEL=llama3-8b-8192
     LLM_API_KEY=your_actual_groq_api_key_here
     ```
   - If you are using local **Ollama**, leave it as `http://localhost:11434/v1` and ensure Ollama is running (`ollama run qwen2.5:7b`).

6. **Start the Backend Server:**
   ```powershell
   uvicorn app.main:app --reload --port 8000
   ```
   *(Wait until you see "Application startup complete". The API is now running at http://localhost:8000)*

### Step 3: Set up the Frontend (React UI)

Open a **third** PowerShell window.

1. **Navigate to the Frontend:**
   ```powershell
   cd c:\Users\amma\ADITHYA_23001\FSD_project\frontend
   ```
2. **Install Node Packages:**
   ```powershell
   npm install
   ```
3. **Start the React Server:**
   ```powershell
   npm run dev
   ```
   *(This will start the UI on http://localhost:5173)*

---

## 3. How to Use the Application

Once all three services (Neo4j, Backend, Frontend) are running, open your browser to **http://localhost:5173**.

### Phase A: Ingesting a Paper (KG Construction)
1. In the UI, locate the **Paper Uploader** panel.
2. Select a research paper PDF and upload it.
3. **What happens under the hood:**
   - The Python backend reads the PDF using the `unstructured` and `pdfplumber` libraries.
   - It breaks the text into sections and extracts tables.
   - It sends the text to the LLM (Groq/Ollama) to extract factual "Entities" (Methods, Datasets, Metrics) and "Relations" (Uses, Reports).
   - It saves all this data as interconnected nodes in your local Neo4j database.

### Phase B: Question Answering (Reasoning)
1. Use the **Chat Panel** to ask a question (e.g., *"What dataset was evaluated on, and what was the accuracy?"*).
2. **What happens under the hood:**
   - The AI Agent starts a ReACT loop (Reasoning + Acting). 
   - Instead of just guessing, it generates Cypher queries to search the Neo4j graph.
   - It traverses the graph, looking at connected methods and metrics until it finds the facts needed.
   - The thought process ("Reasoning Trace") is streamed live to your screen.
   - The right side of the screen will render an interactive visual graph of the exact nodes the AI traversed to get your answer.
