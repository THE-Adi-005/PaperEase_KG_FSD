import { useState, useMemo } from 'react';
import { Image, Table2, Search, FileText, Layers, ExternalLink } from 'lucide-react';

export default function FigurePanel({ figures = [], tables = [] }) {
  const [filterType, setFilterType] = useState('all'); // 'all' | 'tables' | 'figures'
  const [search, setSearch] = useState('');

  const filteredFigures = useMemo(() => {
    if (filterType === 'tables') return [];
    return figures.filter(fig => {
      if (!search.trim()) return true;
      const q = search.toLowerCase();
      return (fig.label || '').toLowerCase().includes(q) ||
             (fig.caption || '').toLowerCase().includes(q) ||
             (fig.paperTitle || '').toLowerCase().includes(q);
    });
  }, [figures, filterType, search]);

  const filteredTables = useMemo(() => {
    if (filterType === 'figures') return [];
    return tables.filter(tbl => {
      if (!search.trim()) return true;
      const q = search.toLowerCase();
      const inHeaders = (tbl.headers || []).some(h => h.toLowerCase().includes(q));
      return (tbl.label || '').toLowerCase().includes(q) ||
             (tbl.caption || '').toLowerCase().includes(q) ||
             (tbl.paperTitle || '').toLowerCase().includes(q) ||
             inHeaders;
    });
  }, [tables, filterType, search]);

  if (figures.length === 0 && tables.length === 0) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', height: '100%', color: 'var(--text-muted)',
        gap: 12, padding: 30, textAlign: 'center',
      }}>
        <div style={{ padding: 14, background: 'rgba(168, 85, 247, 0.1)', borderRadius: '50%', color: 'var(--accent-purple)' }}>
          <Table2 size={32} />
        </div>
        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>No Figures or Tables Loaded</div>
        <p style={{ fontSize: '0.8rem', maxWidth: 280, margin: 0 }}>
          Select one or more papers from the sidebar to inspect extracted benchmark tables and model architecture figures.
        </p>
      </div>
    );
  }

  const renderArchitectureVisual = (fig) => {
    const isTransformer = (fig.label || '').toLowerCase().includes('transformer');
    const isBert = (fig.label || '').toLowerCase().includes('bert');
    const isGpt = (fig.label || '').toLowerCase().includes('gpt') || (fig.label || '').toLowerCase().includes('few-shot');

    return (
      <div style={{
        background: 'linear-gradient(135deg, #0f172a, #1e1b4b)',
        padding: '18px',
        borderRadius: '8px',
        marginBottom: '12px',
        border: '1px solid rgba(168, 85, 247, 0.2)',
      }}>
        {isTransformer ? (
          <div style={{ display: 'flex', gap: 12, justifyContent: 'space-around', alignItems: 'center', fontSize: '0.72rem' }}>
            {/* Encoder */}
            <div style={{ flex: 1, background: 'rgba(59, 130, 246, 0.12)', border: '1px solid #3b82f6', borderRadius: 8, padding: 10, textAlign: 'center' }}>
              <div style={{ fontWeight: 700, color: '#60a5fa', marginBottom: 6 }}>ENCODER (N=6)</div>
              <div style={{ background: 'rgba(255,255,255,0.05)', padding: 4, borderRadius: 4, marginBottom: 4 }}>Multi-Head Attention</div>
              <div style={{ background: 'rgba(255,255,255,0.05)', padding: 4, borderRadius: 4 }}>Feed Forward (Linear)</div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: 4 }}>Add & Norm</div>
            </div>
            <div style={{ color: 'var(--accent-purple)', fontWeight: 700 }}>──▶</div>
            {/* Decoder */}
            <div style={{ flex: 1, background: 'rgba(168, 85, 247, 0.12)', border: '1px solid #a855f7', borderRadius: 8, padding: 10, textAlign: 'center' }}>
              <div style={{ fontWeight: 700, color: '#c084fc', marginBottom: 6 }}>DECODER (N=6)</div>
              <div style={{ background: 'rgba(255,255,255,0.05)', padding: 4, borderRadius: 4, marginBottom: 4 }}>Masked Self-Attention</div>
              <div style={{ background: 'rgba(255,255,255,0.05)', padding: 4, borderRadius: 4, marginBottom: 4 }}>Cross-Attention</div>
              <div style={{ background: 'rgba(255,255,255,0.05)', padding: 4, borderRadius: 4 }}>Feed Forward</div>
            </div>
          </div>
        ) : isBert ? (
          <div style={{ fontSize: '0.72rem', textAlign: 'center' }}>
            <div style={{ fontWeight: 700, color: '#38bdf8', marginBottom: 8 }}>BERT BIDIRECTIONAL ENCODER</div>
            <div style={{ display: 'flex', gap: 6, justifyContent: 'center', marginBottom: 8 }}>
              {['[CLS]', 'Token 1', 'Token 2', '[SEP]', 'Token 3', '[SEP]'].map((t, idx) => (
                <span key={idx} style={{ background: 'rgba(56, 189, 248, 0.15)', border: '1px solid rgba(56,189,248,0.4)', padding: '2px 8px', borderRadius: 4 }}>
                  {t}
                </span>
              ))}
            </div>
            <div style={{ padding: 6, background: 'rgba(168, 85, 247, 0.15)', border: '1px solid #a855f7', borderRadius: 6, color: '#e2e8f0' }}>
              Deep Bidirectional Self-Attention (L=12 / 24, H=768 / 1024)
            </div>
          </div>
        ) : isGpt ? (
          <div style={{ fontSize: '0.72rem', textAlign: 'center' }}>
            <div style={{ fontWeight: 700, color: '#4ade80', marginBottom: 8 }}>IN-CONTEXT FEW-SHOT DEMONSTRATION</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, textAlign: 'left', background: 'rgba(0,0,0,0.3)', padding: 8, borderRadius: 6 }}>
              <div><span style={{ color: '#4ade80' }}>Input:</span> Q: Translate English to French. cheese =&gt; A: fromage</div>
              <div><span style={{ color: '#4ade80' }}>Input:</span> Q: sea otter =&gt; A: loutre de mer</div>
              <div><span style={{ color: '#fbbf24' }}>Prompt:</span> Q: peppermint =&gt; <span style={{ color: '#60a5fa', fontWeight: 600 }}>A: menthe poivrée</span></div>
            </div>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: 12, color: 'var(--text-muted)', fontSize: '0.75rem' }}>
            Architecture diagram & schematic layout
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ padding: '16px', height: '100%', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Top Filter Bar */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 4, background: 'var(--bg-panel)', padding: 4, borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
          <button
            onClick={() => setFilterType('all')}
            style={{
              background: filterType === 'all' ? 'var(--accent-purple)' : 'transparent',
              color: filterType === 'all' ? '#fff' : 'var(--text-secondary)',
              border: 'none', borderRadius: 6, padding: '4px 10px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
            }}
          >
            All ({figures.length + tables.length})
          </button>
          <button
            onClick={() => setFilterType('tables')}
            style={{
              background: filterType === 'tables' ? 'var(--accent-blue)' : 'transparent',
              color: filterType === 'tables' ? '#fff' : 'var(--text-secondary)',
              border: 'none', borderRadius: 6, padding: '4px 10px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
            }}
          >
            Tables ({tables.length})
          </button>
          <button
            onClick={() => setFilterType('figures')}
            style={{
              background: filterType === 'figures' ? 'var(--accent-teal)' : 'transparent',
              color: filterType === 'figures' ? '#fff' : 'var(--text-secondary)',
              border: 'none', borderRadius: 6, padding: '4px 10px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
            }}
          >
            Figures ({figures.length})
          </button>
        </div>

        {/* Search */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          background: 'var(--bg-panel)', padding: '4px 10px', borderRadius: 6,
          border: '1px solid var(--border-subtle)', minWidth: 160,
        }}>
          <Search size={12} color="var(--text-muted)" />
          <input
            type="text"
            placeholder="Filter tables/figures..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ background: 'transparent', border: 'none', outline: 'none', color: 'var(--text-primary)', fontSize: '0.75rem', width: '100%' }}
          />
        </div>
      </div>

      {/* Figures Section */}
      {filteredFigures.length > 0 && (
        <div>
          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--accent-teal)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Image size={14} /> Model Diagrams & Figures ({filteredFigures.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {filteredFigures.map(fig => (
              <div key={fig.id} className="figure-card" style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: 10, padding: 14 }}>
                {fig.paperTitle && (
                  <div style={{ fontSize: '0.7rem', color: 'var(--accent-purple)', fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <FileText size={11} /> {fig.paperTitle}
                  </div>
                )}
                {fig.image_path ? (
                  <img
                    src={`http://localhost:8000${fig.image_path}`}
                    alt={fig.caption || fig.label}
                    loading="lazy"
                    style={{ width: '100%', borderRadius: 6, maxHeight: 300, objectFit: 'contain', background: '#0a0e1a' }}
                  />
                ) : (
                  renderArchitectureVisual(fig)
                )}
                <div className="figure-label" style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-primary)', marginTop: 8 }}>
                  {fig.label}
                </div>
                {fig.caption && (
                  <div className="figure-caption" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.4 }}>
                    {fig.caption}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tables Section */}
      {filteredTables.length > 0 && (
        <div>
          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--accent-blue)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Table2 size={14} /> Benchmark & Evaluation Tables ({filteredTables.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {filteredTables.map(tbl => (
              <div key={tbl.id} className="figure-card" style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)', borderRadius: 10, padding: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div className="figure-label" style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Table2 size={13} color="var(--accent-blue)" />
                    {tbl.label}
                  </div>
                  {tbl.paperTitle && (
                    <span style={{ fontSize: '0.68rem', color: 'var(--accent-purple)', background: 'rgba(168, 85, 247, 0.1)', padding: '2px 8px', borderRadius: 10, border: '1px solid rgba(168, 85, 247, 0.2)' }}>
                      {tbl.paperTitle.slice(0, 30)}...
                    </span>
                  )}
                </div>

                {tbl.caption && (
                  <div className="figure-caption" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 10, lineHeight: 1.4 }}>
                    {tbl.caption}
                  </div>
                )}

                {tbl.headers && tbl.headers.length > 0 ? (
                  <div style={{ overflowX: 'auto', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                    <table className="data-table" style={{ width: '100%', fontSize: '0.75rem', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ background: 'rgba(17, 24, 39, 0.9)', borderBottom: '1px solid var(--border-subtle)', textAlign: 'left' }}>
                          {tbl.headers.map((h, i) => (
                            <th key={i} style={{ padding: '8px 10px', color: 'var(--text-secondary)', fontWeight: 600 }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {(tbl.rows && tbl.rows.length > 0) ? (
                          tbl.rows.slice(0, 25).map((row, ri) => (
                            <tr key={ri} style={{ borderBottom: '1px solid rgba(148, 163, 184, 0.06)', background: ri % 2 === 0 ? 'rgba(255,255,255,0.01)' : 'transparent' }}>
                              {row.map((cell, ci) => (
                                <td key={ci} style={{ padding: '7px 10px', color: ci === 0 ? 'var(--text-primary)' : 'var(--text-secondary)', fontWeight: ci === 0 ? 600 : 400 }}>
                                  {cell}
                                </td>
                              ))}
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={tbl.headers.length} style={{ padding: '12px', textAlign: 'center', color: 'var(--text-muted)' }}>
                              Table headers identified ({tbl.headers.join(', ')}).
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
