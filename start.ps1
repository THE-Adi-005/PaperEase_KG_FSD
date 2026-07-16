Write-Host "Starting KG Paper Assistant..." -ForegroundColor Cyan

# 1. Start Backend in background
Write-Host "Starting FastAPI Backend on port 8000..." -ForegroundColor Yellow
$backendProcess = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "cd backend; .\venv\Scripts\activate; uvicorn app.main:app --reload --port 8000" -PassThru

# 2. Wait a moment for backend to initialize
Start-Sleep -Seconds 3

# 3. Start Frontend in background
Write-Host "Starting React Frontend on port 5173..." -ForegroundColor Yellow
$frontendProcess = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev" -PassThru

Write-Host "Servers are starting in separate windows!" -ForegroundColor Green
Write-Host "Make sure you have Docker (Neo4j, GROBID) and Ollama running." -ForegroundColor Cyan
Write-Host ""
Write-Host "Frontend: http://localhost:5173"
Write-Host "Backend API: http://localhost:8000/docs"
