import { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import PaperUploader from './components/PaperUploader';
import PaperList from './components/PaperList';
import ChatPanel from './components/ChatPanel';
import ReasoningTrace from './components/ReasoningTrace';
import GraphViewer from './components/GraphViewer';
import FigurePanel from './components/FigurePanel';
import ArchitecturePanel from './components/ArchitecturePanel';
import ExperimentsPanel from './components/ExperimentsPanel';
import ProvenanceInspector from './components/ProvenanceInspector';
import BenchmarkCatalogModal from './components/BenchmarkCatalogModal';
import { useSSE } from './hooks/useSSE';
import { getPapers, getPaperFigures, getPaperTables, queryPapers, queryNaive, comparePapers } from './utils/api';

export default function App() {
  const [papers, setPapers] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [rightTab, setRightTab] = useState('provenance'); // Option A: Side-by-side failure vs graph traversal is default
  const [queryModeView, setQueryModeView] = useState('multi'); // 'multi' | 'single' | 'naive'
  const useNaive = queryModeView === 'naive';
  const [figures, setFigures] = useState([]);
  const [tables, setTables] = useState([]);
  
  // 80-Question Benchmark Catalog Modal & Active Turn Inspector State
  const [isCatalogOpen, setIsCatalogOpen] = useState(false);
  const [catalogQuery, setCatalogQuery] = useState('');
  const [activeTurn, setActiveTurn] = useState(null);
  const [showTrace, setShowTrace] = useState(false);

  const { steps, answer, subgraph, trace, isStreaming, error, startQuery } = useSSE();

  // Fetch verified structured papers on mount and periodically
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

  // Fetch figures/tables when selection changes or papers load
  useEffect(() => {
    const idsToFetch = selectedIds.length > 0 ? selectedIds : papers.map(p => p.id);
    if (idsToFetch.length === 0) {
      setFigures([]);
      setTables([]);
      return;
    }

    Promise.all(idsToFetch.map(async (pid) => {
      const p = papers.find(x => x.id === pid);
      const title = p ? p.title : pid;
      const [figs, tbls] = await Promise.all([
        getPaperFigures(pid).catch(() => []),
        getPaperTables(pid).catch(() => []),
      ]);
      return {
        figs: (figs || []).map(f => ({ ...f, paperTitle: title, paperId: pid })),
        tbls: (tbls || []).map(t => ({ ...t, paperTitle: title, paperId: pid })),
      };
    })).then(results => {
      setFigures(results.flatMap(r => r.figs));
      setTables(results.flatMap(r => r.tbls));
    });
  }, [selectedIds, papers]);

  const handleUpload = (result) => {
    fetchPapers();
  };

  const handleSendQuery = async (question) => {
    const mode = selectedIds.length > 1 ? 'compare' : 'single';
    let url;
    const body = {
      question,
      paper_ids: selectedIds.length > 0 ? selectedIds : papers.map(p => p.id),
      mode,
    };

    if (queryModeView === 'naive') {
      url = queryNaive();
    } else if (mode === 'compare') {
      url = comparePapers();
      body.pipeline = queryModeView === 'single' ? 'single' : 'multi';
    } else {
      url = queryPapers(question, selectedIds, mode);
      body.pipeline = queryModeView === 'single' ? 'single' : 'multi';
    }

    await startQuery(url, body);
  };

  // Handler when a user selects a question from the 80-question benchmark catalog modal
  const handleSelectFromCatalog = (questionItem) => {
    setIsCatalogOpen(false);
    if (questionItem.paper_ids && questionItem.paper_ids.length > 0) {
      setSelectedIds(questionItem.paper_ids);
    }
    // Set external query to trigger 4-model evaluation in ChatPanel
    setCatalogQuery(questionItem.question);
    // Switch right panel to Provenance Inspector (Option A) to display live comparison & failure reasons
    setRightTab('provenance');
  };

  return (
    <>
      <Header onOpenCatalog={() => setIsCatalogOpen(true)} />
      
      {/* 80-Question Benchmark Modal */}
      <BenchmarkCatalogModal
        isOpen={isCatalogOpen}
        onClose={() => setIsCatalogOpen(false)}
        onSelectQuestion={handleSelectFromCatalog}
      />

      <div className="app-layout">
        {/* ── Left Sidebar (Only Verified Structured Papers) ── */}
        <aside className="sidebar">
          <div className="sidebar-section">
            <div className="sidebar-title">Upload Paper</div>
            <PaperUploader onUpload={handleUpload} />
          </div>

          <div className="sidebar-section" style={{ flex: 1, overflowY: 'auto' }}>
            <div className="sidebar-title">
              Verified Papers ({papers.length})
              {selectedIds.length > 0 && (
                <span style={{ float: 'right', color: 'var(--accent-blue)', fontWeight: 600 }}>
                  {selectedIds.length} active
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

        {/* ── Center Panel (Simultaneous 4-Model Arena) ── */}
        <main className="center-panel" style={{ padding: 0 }}>
          <div className="mode-toggle-bar">
            <div className="mode-toggle">
              <button
                className={`mode-btn ${queryModeView === 'multi' ? 'active kg' : ''}`}
                onClick={() => setQueryModeView('multi')}
                title="Simultaneous 4-Model Evaluation: Direct LLM, Vector RAG, Naive KG, and Our Schema-Constrained KG Agent"
              >
                ⚔️ 4-Model Simultaneous Arena
              </button>
              <button
                className={`mode-btn ${queryModeView === 'single' ? 'active kg' : ''}`}
                onClick={() => setQueryModeView('single')}
                title="Single ReACT agent with dynamic Cypher traversal"
              >
                ⚡ Single-Agent Stream
              </button>
              <button
                className={`mode-btn ${queryModeView === 'naive' ? 'active naive' : ''}`}
                onClick={() => setQueryModeView('naive')}
                title="Naive text chunk retrieval baseline"
              >
                📄 Naive RAG Stream
              </button>
            </div>
            <span className="mode-hint" style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>
              Simultaneously running Direct LLM, Vector RAG, Naive KG &amp; Our Proposed KG Agent with Ground Truth scoring
            </span>
          </div>

          <ChatPanel
            selectedPaperIds={selectedIds}
            onSendQuery={handleSendQuery}
            answer={answer}
            isStreaming={isStreaming}
            onTurnEvaluated={(turnResult) => {
              setActiveTurn(turnResult);
            }}
            externalQuery={catalogQuery}
          />

          {steps && steps.length > 0 && (
            <div style={{
              padding: '8px 18px',
              background: '#f8fafc',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                Single-Agent Reasoning Stream: <strong>{steps.length} steps recorded</strong>
              </div>
              <button
                className="action-btn outline"
                onClick={() => setShowTrace(prev => !prev)}
                style={{ fontSize: '0.72rem', padding: '4px 12px' }}
              >
                {showTrace ? '✕ Hide Reasoning Trace' : `🔍 View Reasoning Trace (${steps.length} steps)`}
              </button>
            </div>
          )}

          {showTrace && steps && steps.length > 0 && (
            <ReasoningTrace steps={steps} isStreaming={isStreaming} />
          )}

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

        {/* ── Right Panel (Inspector, Graph, Tables & Ablations) ── */}
        <aside className="right-panel">
          <div className="panel-tabs">
            <button
              className={`panel-tab ${rightTab === 'provenance' ? 'active' : ''}`}
              onClick={() => setRightTab('provenance')}
              title="Side-by-side failure analysis: What RAG retrieved vs what our KG traversed"
            >
              ⚔️ RAG vs KG Provenance
            </button>
            <button
              className={`panel-tab ${rightTab === 'graph' ? 'active' : ''}`}
              onClick={() => setRightTab('graph')}
              title="Interactive Knowledge Graph visualization with entity reasoning"
            >
              Knowledge Graph
            </button>
            <button
              className={`panel-tab ${rightTab === 'figures' ? 'active' : ''}`}
              onClick={() => setRightTab('figures')}
              title="Extracted benchmark tables and model diagrams"
            >
              Figures &amp; Tables
            </button>
            <button
              className={`panel-tab ${rightTab === 'experiments' ? 'active' : ''}`}
              onClick={() => setRightTab('experiments')}
              title="80-Question Benchmark Leaderboard, Sweeps & Ablations"
            >
              80-Q Benchmark &amp; Ablations
            </button>
            <button
              className={`panel-tab ${rightTab === 'architecture' ? 'active' : ''}`}
              onClick={() => setRightTab('architecture')}
              title="System architecture specifications and agent topology"
            >
              Architecture &amp; Pipeline
            </button>
          </div>

          <div className="panel-content" style={{ padding: rightTab === 'graph' ? 0 : undefined }}>
            {rightTab === 'provenance' && (
              <ProvenanceInspector activeTurn={activeTurn} />
            )}
            {rightTab === 'graph' && (
              <GraphViewer subgraph={subgraph} selectedPaperIds={selectedIds} useNaive={useNaive} />
            )}
            {rightTab === 'figures' && (
              <FigurePanel figures={figures} tables={tables} />
            )}
            {rightTab === 'experiments' && (
              <ExperimentsPanel />
            )}
            {rightTab === 'architecture' && (
              <ArchitecturePanel />
            )}
          </div>
        </aside>
      </div>
    </>
  );
}
