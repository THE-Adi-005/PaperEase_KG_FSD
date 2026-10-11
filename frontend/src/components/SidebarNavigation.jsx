import { useState } from 'react';
import { 
  Plus, 
  Home, 
  BookOpen, 
  Network, 
  FileText, 
  Layers, 
  GitCompare, 
  History, 
  Database, 
  UploadCloud, 
  CheckCircle2, 
  ChevronRight, 
  ChevronDown,
  Sparkles,
  ExternalLink,
  Flame,
  Search,
  Settings
} from 'lucide-react';
import PaperUploader from './PaperUploader';
import PaperList from './PaperList';

export default function SidebarNavigation({
  isOpen,
  onClose,
  activeTab,
  onSelectTab,
  onOpenCatalog,
  onNewQuery,
  papers = [],
  selectedIds = [],
  onSelectPapers,
  onUploadPaper,
  recentQueries = [],
  onSelectRecentQuery
}) {
  const [showPapers, setShowPapers] = useState(true);
  const [showRecents, setShowRecents] = useState(true);
  const [paperSearch, setPaperSearch] = useState('');

  const filteredPapers = papers.filter(p => 
    (p.title || p.id).toLowerCase().includes(paperSearch.toLowerCase())
  );

  return (
    <aside className={`consensus-sidebar ${isOpen ? 'open' : 'collapsed'}`}>
      {/* ── + New Research Query Button ── */}
      <div className="sidebar-action-wrap">
        <button
          className="new-query-btn"
          onClick={onNewQuery}
          title="Start a fresh research inquiry across the knowledge graph"
        >
          <Plus size={16} />
          {isOpen && <span>New Research Query</span>}
        </button>
      </div>

      {/* ── Core Navigation Links ── */}
      <div className="sidebar-nav-group">
        <button
          className={`sidebar-nav-item ${activeTab === 'arena' ? 'active' : ''}`}
          onClick={() => onSelectTab('arena')}
          title="Research Arena (4-Model Simultaneous Execution)"
        >
          <Home size={17} />
          {isOpen && <span>Research Arena</span>}
        </button>

        <button
          className="sidebar-nav-item"
          onClick={onOpenCatalog}
          title="Browse 100-Question Multi-Tier Benchmark Catalog"
        >
          <BookOpen size={17} />
          {isOpen && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
              <span>100-Q Benchmark</span>
              <span className="sidebar-badge">100</span>
            </div>
          )}
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'provenance' ? 'active' : ''}`}
          onClick={() => onSelectTab('provenance')}
          title="Compare Outputs: Head-to-Head 4-Model Evaluation"
        >
          <GitCompare size={17} />
          {isOpen && <span>Compare Outputs</span>}
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'graph' ? 'active' : ''}`}
          onClick={() => onSelectTab('graph')}
          title="Interactive Cytoscape.js Knowledge Graph"
        >
          <Network size={17} />
          {isOpen && <span>Knowledge Graph</span>}
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'figures' ? 'active' : ''}`}
          onClick={() => onSelectTab('figures')}
          title="Extracted Benchmark Tables & Diagrams"
        >
          <FileText size={17} />
          {isOpen && <span>Figures &amp; Tables</span>}
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'experiments' ? 'active' : ''}`}
          onClick={() => onSelectTab('experiments')}
          title="Ablation Studies & Empirical Leaderboard"
        >
          <Layers size={17} />
          {isOpen && <span>Ablations &amp; Sweeps</span>}
        </button>
      </div>

      {/* ── Library: Verified Papers (Collapsible) ── */}
      {isOpen && (
        <div className="sidebar-section-container">
          <div 
            className="sidebar-section-header"
            onClick={() => setShowPapers(prev => !prev)}
          >
            <span>Verified Papers ({papers.length})</span>
            {showPapers ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </div>

          {showPapers && (
            <div className="sidebar-papers-list">
              <div style={{ marginBottom: 8 }}>
                <PaperUploader onUpload={onUploadPaper} />
              </div>
              <PaperList
                papers={filteredPapers}
                selectedIds={selectedIds}
                onSelect={onSelectPapers}
              />
            </div>
          )}
        </div>
      )}

      {/* ── Recent Research Queries ── */}
      {isOpen && recentQueries.length > 0 && (
        <div className="sidebar-section-container">
          <div 
            className="sidebar-section-header"
            onClick={() => setShowRecents(prev => !prev)}
          >
            <span>Recent Queries</span>
            {showRecents ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </div>

          {showRecents && (
            <div className="recent-queries-list">
              {recentQueries.slice(0, 5).map((q, idx) => (
                <button
                  key={idx}
                  className="recent-query-item"
                  onClick={() => onSelectRecentQuery(q)}
                  title={q}
                >
                  <History size={12} style={{ flexShrink: 0 }} />
                  <span className="truncate">{q}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── User Profile & System Status Footer ── */}
      <div className="sidebar-footer">
        <div className="sidebar-user-card">
          <div className="sidebar-avatar">A</div>
          {isOpen && (
            <div className="sidebar-user-info">
              <div className="user-name">Adithya R</div>
              <div className="user-plan">Academic Researcher</div>
            </div>
          )}
        </div>

        {isOpen && (
          <div className="sidebar-db-status">
            <div className="status-indicator-row">
              <span className="status-bullet active" />
              <span>Neo4j: 1,546 Nodes</span>
            </div>
            <div className="status-indicator-row">
              <span className="status-bullet active" />
              <span>Ollama: Qwen 2.5 7B</span>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
