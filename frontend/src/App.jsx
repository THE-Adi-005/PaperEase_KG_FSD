import { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import PaperUploader from './components/PaperUploader';
import PaperList from './components/PaperList';
import ChatPanel from './components/ChatPanel';
import ReasoningTrace from './components/ReasoningTrace';
import GraphViewer from './components/GraphViewer';
import FigurePanel from './components/FigurePanel';
import DemoPanel from './components/DemoPanel';
import DualComparison from './components/DualComparison';
import ArchitecturePanel from './components/ArchitecturePanel';
import { useSSE } from './hooks/useSSE';
import { getPapers, getPaperFigures, getPaperTables, queryPapers, queryNaive, comparePapers } from './utils/api';

export default function App() {
  const [papers, setPapers] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [rightTab, setRightTab] = useState('graph');
  const [queryModeView, setQueryModeView] = useState('multi'); // 'multi' | 'single' | 'naive' | 'dual'
  const useNaive = queryModeView === 'naive';
  const [figures, setFigures] = useState([]);
  const [tables, setTables] = useState([]);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [demoQuestion, setDemoQuestion] = useState('');

  const { steps, answer, subgraph, trace, isStreaming, error, startQuery } = useSSE();

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
      paper_ids: selectedIds,
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

  return (
    <>
      <Header isDemoMode={isDemoMode} setIsDemoMode={setIsDemoMode} />
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
        <main className="center-panel" style={{ padding: 0 }}>
          {isDemoMode ? (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              {!demoQuestion ? (
                <DemoPanel 
                  onSelectQuestion={q => setDemoQuestion(q)} 
                  selectedPaperIds={selectedIds} 
                  refreshPapers={fetchPapers}
                />
              ) : (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                  <div style={{ padding: '8px 20px', background: 'var(--bg-panel)', borderBottom: '1px solid var(--border-subtle)' }}>
                    <button className="action-btn outline" onClick={() => setDemoQuestion('')}>← Back to Demo Menu</button>
                  </div>
                  <DualComparison selectedPaperIds={selectedIds} initialQuestion={demoQuestion} />
                </div>
              )}
            </div>
          ) : (
            <>
              <div className="mode-toggle-bar">
                <div className="mode-toggle">
                  <button
                    className={`mode-btn ${queryModeView === 'multi' ? 'active kg' : ''}`}
                    onClick={() => setQueryModeView('multi')}
                    title="Traceable 4-Agent Pipeline: Planner → Retriever → Reasoner → Verifier"
                  >
                    🤖 KG Multi-Agent
                  </button>
                  <button
                    className={`mode-btn ${queryModeView === 'single' ? 'active kg' : ''}`}
                    onClick={() => setQueryModeView('single')}
                    title="Legacy single ReACT agent with dynamic Cypher traversal"
                  >
                    ⚡ KG Single-Agent
                  </button>
                  <button
                    className={`mode-btn ${queryModeView === 'naive' ? 'active naive' : ''}`}
                    onClick={() => setQueryModeView('naive')}
                    title="Simple text retrieval + LLM (no graph reasoning)"
                  >
                    📄 Naive RAG
                  </button>
                  <button
                    className={`mode-btn ${queryModeView === 'dual' ? 'active' : ''}`}
                    onClick={() => setQueryModeView('dual')}
                    style={{
                      background: queryModeView === 'dual' ? 'linear-gradient(135deg, #a855f7 0%, #3b82f6 100%)' : 'transparent',
                      color: queryModeView === 'dual' ? '#fff' : 'var(--text-secondary)',
                    }}
                    title="Run both side-by-side and compare answers and metrics live"
                  >
                    ⚔️ Dual A/B Test
                  </button>
                </div>
                {queryModeView === 'multi' && (
                  <span className="mode-hint" style={{ color: 'var(--accent-purple)' }}>
                    4 specialist agents: Planner, Retriever, Reasoner, and Verifier with provenance fact-checking
                  </span>
                )}
                {queryModeView === 'single' && (
                  <span className="mode-hint">Single ReACT loop with lazy graph traversal</span>
                )}
                {queryModeView === 'naive' && (
                  <span className="mode-hint">Baseline mode — no Knowledge Graph reasoning</span>
                )}
                {queryModeView === 'dual' && (
                  <span className="mode-hint" style={{ color: 'var(--accent-purple)' }}>
                    Live A/B comparison on the same question with real-time metrics
                  </span>
                )}
              </div>

              {queryModeView === 'dual' ? (
                <DualComparison selectedPaperIds={selectedIds} />
              ) : (
                <>
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
                </>
              )}
            </>
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
            <button
              className={`panel-tab ${rightTab === 'architecture' ? 'active' : ''}`}
              onClick={() => setRightTab('architecture')}
            >
              Architecture & Metrics
            </button>
          </div>

          <div className="panel-content" style={{ padding: rightTab === 'graph' ? 0 : undefined }}>
            {rightTab === 'graph' && (
              <GraphViewer subgraph={subgraph} selectedPaperIds={selectedIds} useNaive={useNaive} />
            )}
            {rightTab === 'figures' && (
              <FigurePanel figures={figures} tables={tables} />
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
