const API_BASE = 'http://localhost:8000/api';

export async function uploadPaper(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  return res.json();
}

export async function getPapers() {
  const res = await fetch(`${API_BASE}/papers`);
  if (!res.ok) throw new Error(`Failed to fetch papers`);
  return res.json();
}

export async function getPaperGraph(paperId) {
  const res = await fetch(`${API_BASE}/paper/${paperId}/graph`);
  if (!res.ok) throw new Error(`Failed to fetch graph`);
  return res.json();
}

export async function getPaperFigures(paperId) {
  const res = await fetch(`${API_BASE}/paper/${paperId}/figures`);
  if (!res.ok) throw new Error(`Failed to fetch figures`);
  return res.json();
}

export async function getPaperTables(paperId) {
  const res = await fetch(`${API_BASE}/paper/${paperId}/tables`);
  if (!res.ok) throw new Error(`Failed to fetch tables`);
  return res.json();
}

export async function getPaperStatus(paperId) {
  const res = await fetch(`${API_BASE}/paper/${paperId}/status`);
  if (!res.ok) throw new Error(`Failed to fetch status`);
  return res.json();
}

export async function checkHealth() {
  try {
    const res = await fetch('http://localhost:8000/health');
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export function queryPapers(question, paperIds, mode = 'single') {
  return `${API_BASE}/query`;
}

export function queryNaive() {
  return `${API_BASE}/query-naive`;
}

export function comparePapers() {
  return `${API_BASE}/compare`;
}

export function queryDual() {
  return `${API_BASE}/query-dual`;
}

export async function seedDemoData() {
  const res = await fetch(`${API_BASE}/demo/seed`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to seed demo data');
  return res.json();
}

export async function getDemoQuestions() {
  const res = await fetch(`${API_BASE}/demo/questions`);
  if (!res.ok) throw new Error('Failed to fetch demo questions');
  return res.json();
}

export async function getGraphStats() {
  const res = await fetch(`${API_BASE}/demo/stats`);
  if (!res.ok) throw new Error('Failed to fetch graph stats');
  return res.json();
}

export async function getPaperTriples(paperId) {
  const res = await fetch(`${API_BASE}/paper/${paperId}/triples`);
  if (!res.ok) throw new Error('Failed to fetch paper triples');
  return res.json();
}

export async function getLiveMetrics() {
  const res = await fetch(`${API_BASE}/eval/metrics`);
  if (!res.ok) throw new Error('Failed to fetch live evaluation metrics');
  return res.json();
}

export async function runLiveBenchmark(sampleLimit = 3) {
  const res = await fetch(`${API_BASE}/eval/run-benchmark`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sample_limit: sampleLimit }),
  });
  if (!res.ok) throw new Error('Failed to run live benchmark');
  return res.json();
}

export async function getGroundingStatements(category = null) {
  const url = category 
    ? `${API_BASE}/grounding/statements?category=${category}`
    : `${API_BASE}/grounding/statements`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch grounding statements');
  return res.json();
}

export async function getGroundingBibtex() {
  const res = await fetch(`${API_BASE}/grounding/bibtex`);
  if (!res.ok) throw new Error('Failed to fetch BibTeX');
  return res.json();
}

export async function getAblationExperiments() {
  const res = await fetch(`${API_BASE}/eval/ablation/available`);
  if (!res.ok) throw new Error('Failed to fetch ablation experiments');
  return res.json();
}

export async function runAblationExperiment(experimentName, paperId = null) {
  const res = await fetch(`${API_BASE}/eval/ablation/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ experiment: experimentName, paper_id: paperId }),
  });
  if (!res.ok) throw new Error('Failed to run ablation experiment');
  return res.json();
}

export async function getAblationGraphStats(paperId = null) {
  const url = paperId 
    ? `${API_BASE}/eval/ablation/graph-stats?paper_id=${paperId}`
    : `${API_BASE}/eval/ablation/graph-stats`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch ablation graph stats');
  return res.json();
}
