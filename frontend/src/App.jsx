import { useState, useEffect, useCallback, useRef } from 'react';
import Header from './components/Header';
import SidebarNavigation from './components/SidebarNavigation';
import ChatPanel from './components/ChatPanel';
import ReasoningTrace from './components/ReasoningTrace';
import GraphViewer from './components/GraphViewer';
import FigurePanel from './components/FigurePanel';
import ArchitecturePanel from './components/ArchitecturePanel';
import ExperimentsPanel from './components/ExperimentsPanel';
import CompareOutputsPanel from './components/CompareOutputsPanel';
import BenchmarkCatalogModal from './components/BenchmarkCatalogModal';
import { useSSE } from './hooks/useSSE';
import { getPapers, getPaperFigures, getPaperTables, queryPapers, queryCompareAll } from './utils/api';

export default function App() {
  const [papers, setPapers] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [rightTab, setRightTab] = useState('compare'); // Default active tab: "Compare Outputs"
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [figures, setFigures] = useState([]);
  const [tables, setTables] = useState([]);
  const [recentQueries, setRecentQueries] = useState([
    'How does the self-attention mechanism in the Transformer compute attention weights?',
    'What dataset is used to evaluate the language model in the GPT paper?',
    'What is the GLUE score of T5-11B reported in the paper?',
    'Between GPT and BERT, which uses causal unidirectional attention versus bidirectional conditioning?',
  ]);
  
  // 100-Question Benchmark Catalog Modal & Active Turn Inspector State
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
    // Record into recents if unique
    setRecentQueries(prev => {
      const filtered = prev.filter(q => q.toLowerCase() !== question.toLowerCase());
      return [question, ...filtered].slice(0, 10);
    });

    const mode = selectedIds.length > 1 ? 'compare' : 'single';
    const body = {
      question,
      paper_ids: selectedIds.length > 0 ? selectedIds : papers.map(p => p.id),
      mode,
    };

    const url = queryPapers(question, selectedIds, mode);
    body.pipeline = 'multi'; // Always 4-model multi-pipeline

    await startQuery(url, body);
  };

  // Re-compute score handler for the button in CompareOutputsPanel
  const handleRecomputeScore = async (question) => {
    try {
      const data = await queryCompareAll(question, selectedIds);
      const modelsList = Array.isArray(data.models) ? data.models : Object.values(data.models || {});
      const turnResult = {
        question,
        loading: false,
        matched_benchmark: data.matched_benchmark,
        is_unseen: data.is_unseen,
        ground_truth: data.ground_truth,
        models: modelsList,
        why_ours_wins: data.why_ours_wins,
      };
      setActiveTurn(turnResult);
    } catch (err) {
      console.error('Failed to recompute scores:', err);
    }
  };

  // Handler when a user selects a question from the 100-question benchmark catalog modal
  const handleSelectFromCatalog = (questionItem) => {
    setIsCatalogOpen(false);
    if (questionItem.paper_ids && questionItem.paper_ids.length > 0) {
      setSelectedIds(questionItem.paper_ids);
    }
    setCatalogQuery(questionItem.question);
    setRightTab('compare'); // Always switch right panel to Compare Outputs
  };

  const handleNewResearchQuery = () => {
    setCatalogQuery('');
    // Focus or trigger prompt
    const inputEl = document.querySelector('.chat-input textarea, .chat-input input');
    if (inputEl) {
      inputEl.focus();
    }
  };

  const handleSelectSidebarTab = (tab) => {
    if (tab === 'arena') {
      // Focus center panel
      const inputEl = document.querySelector('.chat-input textarea, .chat-input input');
      if (inputEl) inputEl.focus();
    } else if (tab === 'provenance') {
      setRightTab('compare');
    } else {
      setRightTab(tab);
    }
  };

  return (
    <>
      <Header 
        onToggleSidebar={() => setIsSidebarOpen(prev => !prev)}
        isSidebarOpen={isSidebarOpen}
        onOpenCatalog={() => setIsCatalogOpen(true)} 
      />
      
      {/* 100-Question Benchmark Modal */}
      <BenchmarkCatalogModal
        isOpen={isCatalogOpen}
        onClose={() => setIsCatalogOpen(false)}
        onSelectQuestion={handleSelectFromCatalog}
      />

      <div className="app-layout">
        {/* ── Left Consensus-Style Sidebar with Hamburger Toggle ── */}
        <SidebarNavigation
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
          activeTab={rightTab === 'compare' ? 'provenance' : rightTab}
          onSelectTab={handleSelectSidebarTab}
          onOpenCatalog={() => setIsCatalogOpen(true)}
          onNewQuery={handleNewResearchQuery}
          papers={papers}
          selectedIds={selectedIds}
          onSelectPapers={setSelectedIds}
          onUploadPaper={handleUpload}
          recentQueries={recentQueries}
          onSelectRecentQuery={(q) => {
            setCatalogQuery(q);
            setRightTab('compare');
          }}
        />

        {/* ── Center Panel (Simultaneous 4-Model Arena) ── */}
        <main className="center-panel" style={{ padding: 0 }}>
          {/* Top section: Removed the 3 bars, now clean 4-output informative banner */}
          <div className="arena-header-banner">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span className="arena-badge-pill">
                ⚔️ 4-MODEL SIMULTANEOUS ARENA
              </span>
              <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                Direct LLM, Standard Vector RAG, Naive KG Agent, and Our Proposed KG Agent evaluated simultaneously against Ground Truth
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
              <span style={{ 
                fontSize: '0.68rem', 
                color: '#15803d', 
                fontWeight: 700, 
                background: '#dcfce7', 
                border: '1px solid #bbf7d0',
                padding: '2px 8px', 
                borderRadius: 12,
                display: 'flex',
                alignItems: 'center',
                gap: 4
              }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981' }} />
                4 Outputs in All Cases
              </span>
            </div>
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
                Graph Reasoning Stream: <strong>{steps.length} steps recorded</strong>
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

        {/* ── Right Panel: "Compare Outputs" as Primary Section ── */}
        <aside className="right-panel">
          <div className="panel-tabs">
            <button
              className={`panel-tab ${rightTab === 'compare' ? 'active' : ''}`}
              onClick={() => setRightTab('compare')}
              title="Compare all 4 model outputs side-by-side with Ground Truth scoring and tracing"
            >
              ⚔️ Compare Outputs
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
              title="100-Question Benchmark Leaderboard, Sweeps & Ablations"
            >
              100-Q Leaderboard
            </button>
            <button
              className={`panel-tab ${rightTab === 'architecture' ? 'active' : ''}`}
              onClick={() => setRightTab('architecture')}
              title="System architecture specifications and agent topology"
            >
              Architecture
            </button>
          </div>

          <div className="panel-content" style={{ padding: rightTab === 'graph' ? 0 : undefined }}>
            {rightTab === 'compare' && (
              <CompareOutputsPanel 
                activeTurn={activeTurn} 
                onRecomputeScore={handleRecomputeScore}
              />
            )}
            {rightTab === 'graph' && (
              <GraphViewer subgraph={subgraph} selectedPaperIds={selectedIds} useNaive={false} />
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
