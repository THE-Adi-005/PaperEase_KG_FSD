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

export function comparePapers() {
  return `${API_BASE}/compare`;
}
