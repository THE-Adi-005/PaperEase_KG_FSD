import { FileText, Check, Loader, AlertCircle } from 'lucide-react';

export default function PaperList({ papers, selectedIds, onSelect }) {
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
          <div className="paper-title">
            <FileText size={13} style={{ marginRight: 6, opacity: 0.5, verticalAlign: 'middle' }} />
            {paper.title}
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
    </div>
  );
}
