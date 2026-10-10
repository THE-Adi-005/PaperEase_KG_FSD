import { Check, Clock, AlertCircle, FileText, Eye, Loader } from 'lucide-react';
import { useState } from 'react';
import ExtractedDataModal from './ExtractedDataModal';

export default function PaperList({ papers, selectedIds, onSelect }) {
  const [viewingPaper, setViewingPaper] = useState(null);

  if (!papers || papers.length === 0) {
    return (
      <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
        No papers uploaded yet
      </div>
    );
  }

  const toggleSelect = (id) => {
    if (selectedIds.includes(id)) {
      onSelect(selectedIds.filter(x => x !== id));
    } else {
      onSelect([...selectedIds, id]);
    }
  };

  const statusIcon = (status) => {
    switch (status) {
      case 'complete': return <Check size={12} style={{ color: 'var(--accent-green)' }} />;
      case 'failed': return <AlertCircle size={12} style={{ color: 'var(--accent-rose)' }} />;
      case 'parsing':
      case 'extracting':
      case 'linking':
        return <Loader size={12} className="loading-spinner" style={{ color: 'var(--accent-amber)' }} />;
      default: return null;
    }
  };

  return (
    <div>
      {papers.map(paper => (
        <div
          key={paper.id}
          className={`paper-card ${selectedIds.includes(paper.id) ? 'selected' : ''}`}
          onClick={() => toggleSelect(paper.id)}
        >
          <div className="paper-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6, width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', minWidth: 0, flex: 1, overflow: 'hidden' }}>
              <FileText size={13} style={{ marginRight: 6, opacity: 0.5, flexShrink: 0 }} />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={paper.title}>
                {paper.title}
              </span>
            </div>
            <button 
              title="View Extracted Graph Data"
              style={{ background: 'none', border: 'none', color: 'var(--accent-blue)', cursor: 'pointer', padding: 4, flexShrink: 0, display: 'flex', alignItems: 'center' }}
              onClick={(e) => { e.stopPropagation(); setViewingPaper(paper); }}
            >
              <Eye size={14} />
            </button>
          </div>
          <div className="paper-meta">
            {statusIcon(paper.status)}
            <span className={`status-badge ${paper.status}`}>{paper.status}</span>
            {paper.section_count > 0 && <span>{paper.section_count} sections</span>}
            {paper.status === 'extracting' && paper.progress_pct > 0 && (
              <div className="progress-bar" style={{ flex: 1, maxWidth: 80 }}>
                <div className="progress-fill" style={{ width: `${paper.progress_pct}%` }} />
              </div>
            )}
          </div>
        </div>
      ))}
      
      {viewingPaper && (
        <ExtractedDataModal 
          paperId={viewingPaper.id} 
          paperTitle={viewingPaper.title} 
          onClose={() => setViewingPaper(null)} 
        />
      )}
    </div>
  );
}
