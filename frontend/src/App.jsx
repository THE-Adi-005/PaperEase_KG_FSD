import { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import PaperUploader from './components/PaperUploader';
import PaperList from './components/PaperList';
import ChatPanel from './components/ChatPanel';
import ReasoningTrace from './components/ReasoningTrace';
import GraphViewer from './components/GraphViewer';
import FigurePanel from './components/FigurePanel';
import { useSSE } from './hooks/useSSE';
import { getPapers, getPaperFigures, getPaperTables, queryPapers, comparePapers } from './utils/api';

export default function App() {
  const [papers, setPapers] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [rightTab, setRightTab] = useState('graph');
  const [figures, setFigures] = useState([]);
  const [tables, setTables] = useState([]);

  const { steps, answer, subgraph, isStreaming, error, startQuery } = useSSE();

  // Fetch papers on mount and periodically
  const fetchPapers = useCallback(async () => {
    try {
      const data = await getPapers();
      setPapers(data);
    } catch (err) {
      console.error('Failed to fetch papers:', err);
    }
  }, []);

  useEffect(() => {
    fetchPapers();
    const interval = setInterval(fetchPapers, 5000);
    return () => clearInterval(interval);
  }, [fetchPapers]);

  // Fetch figures/tables when selection changes
  useEffect(() => {
    if (selectedIds.length === 1) {
      const paperId = selectedIds[0];
      getPaperFigures(paperId).then(setFigures).catch(() => setFigures([]));
      getPaperTables(paperId).then(setTables).catch(() => setTables([]));
    } else {
      setFigures([]);
      setTables([]);
    }
  }, [selectedIds]);

  const handleUpload = (result) => {
    fetchPapers();
  };

  const handleSendQuery = async (question) => {
    const mode = selectedIds.length > 1 ? 'compare' : 'single';
    const url = mode === 'compare'
      ? comparePapers()
      : queryPapers(question, selectedIds, mode);

    await startQuery(url, {
      question,
      paper_ids: selectedIds,
      mode,
    });
  };

  return (
    <>
      <Header />
      <div className="app-layout">
        {/* ── Left Sidebar ── */}
        <aside className="sidebar">
          <div className="sidebar-section">
            <div className="sidebar-title">Upload Paper</div>
            <PaperUploader onUpload={handleUpload} />
          </div>

          <div className="sidebar-section" style={{ flex: 1, overflowY: 'auto' }}>
            <div className="sidebar-title">
              Papers ({papers.length})
              {selectedIds.length > 0 && (
                <span style={{ float: 'right', color: 'var(--accent-purple)', fontWeight: 500 }}>
                  {selectedIds.length} selected
                </span>
              )}
            </div>
            <PaperList
              papers={papers}
              selectedIds={selectedIds}
              onSelect={setSelectedIds}
            />
          </div>
        </aside>

        {/* ── Center Panel ── */}
        <main className="center-panel">
          <ChatPanel
            selectedPaperIds={selectedIds}
            onSendQuery={handleSendQuery}
            answer={answer}
            isStreaming={isStreaming}
          />
          <ReasoningTrace steps={steps} isStreaming={isStreaming} />
          {error && (
            <div style={{
              padding: '8px 16px', background: 'rgba(244,63,94,0.1)',
              borderTop: '1px solid rgba(244,63,94,0.3)',
              color: 'var(--accent-rose)', fontSize: '0.8rem',
            }}>
              Error: {error}
            </div>
          )}
        </main>

        {/* ── Right Panel ── */}
        <aside className="right-panel">
          <div className="panel-tabs">
            <button
              className={`panel-tab ${rightTab === 'graph' ? 'active' : ''}`}
              onClick={() => setRightTab('graph')}
            >
              Knowledge Graph
            </button>
            <button
              className={`panel-tab ${rightTab === 'figures' ? 'active' : ''}`}
              onClick={() => setRightTab('figures')}
            >
              Figures & Tables
            </button>
          </div>

          <div className="panel-content" style={{ padding: rightTab === 'graph' ? 0 : undefined }}>
            {rightTab === 'graph' && (
              <GraphViewer subgraph={subgraph} />
            )}
            {rightTab === 'figures' && (
              <FigurePanel figures={figures} tables={tables} />
            )}
          </div>
        </aside>
      </div>
    </>
  );
}
