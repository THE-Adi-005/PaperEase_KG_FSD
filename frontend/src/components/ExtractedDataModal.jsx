import { useState, useEffect, useMemo } from 'react';
import { getPaperTriples } from '../utils/api';
import { X, Network, Loader, Search, Filter, Layers, Database, Sparkles } from 'lucide-react';

const TYPE_COLORS = {
  Paper: '#a855f7',
  Method: '#3b82f6',
  Concept: '#8b5cf6',
  Dataset: '#22c55e',
  Metric: '#f59e0b',
  Author: '#64748b',
  Section: '#475569',
  Figure: '#14b8a6',
  Table: '#06b6d4',
  Default: '#64748b',
};

export default function ExtractedDataModal({ paperId, paperTitle, onClose }) {
  const [triples, setTriples] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [categoryFilter, setCategoryFilter] = useState('domain'); // 'domain' | 'structural' | 'all'
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const fetchTriples = async () => {
      try {
        const data = await getPaperTriples(paperId);
        setTriples(data.triples || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchTriples();
  }, [paperId]);

  const domainCount = useMemo(() => triples.filter(t => t.category === 'domain').length, [triples]);
  const structuralCount = useMemo(() => triples.filter(t => t.category === 'structural').length, [triples]);

  const filteredTriples = useMemo(() => {
    return triples.filter(t => {
      // Category check
      if (categoryFilter === 'domain' && t.category !== 'domain') return false;
      if (categoryFilter === 'structural' && t.category !== 'structural') return false;

      // Search query check
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const headMatch = (t.head || '').toLowerCase().includes(q);
        const relMatch = (t.relation || '').toLowerCase().includes(q);
        const tailMatch = (t.tail || '').toLowerCase().includes(q);
        const typeMatch = (t.head_type || '').toLowerCase().includes(q) || (t.tail_type || '').toLowerCase().includes(q);
        return headMatch || relMatch || tailMatch || typeMatch;
      }
      return true;
    });
  }, [triples, categoryFilter, searchQuery]);

  const renderBadge = (type) => {
    const color = TYPE_COLORS[type] || TYPE_COLORS.Default;
    return (
      <span style={{
        display: 'inline-block',
        fontSize: '0.65rem',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.04em',
        padding: '2px 8px',
        borderRadius: 12,
        background: `${color}18`,
        color: color,
        border: `1px solid ${color}40`,
      }}>
        {type}
      </span>
    );
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(5, 8, 16, 0.85)',
      backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1100, padding: 32,
    }}>
      <div style={{
        background: '#0c1021',
        borderRadius: 14,
        width: '100%', maxWidth: 960,
        height: '90vh', maxHeight: 780,
        display: 'flex', flexDirection: 'column',
        boxShadow: '0 25px 60px -10px rgba(0,0,0,0.8), 0 0 0 1px rgba(168, 85, 247, 0.25)',
        overflow: 'hidden',
      }}>
        {/* Modal Header */}
        <div style={{
          padding: '18px 24px',
          background: '#111827',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-primary)' }}>
              <Network color="var(--accent-purple)" size={22} />
              Extracted Knowledge Graph Triples
            </h2>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 4 }}>
              Zero-shot extraction for: <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{paperTitle}</span>
            </div>
          </div>
          <button
            className="action-btn outline"
            onClick={onClose}
            style={{ padding: '6px 10px', borderRadius: 8, cursor: 'pointer' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Toolbar: Category Filters & Search */}
        <div style={{
          padding: '12px 24px',
          background: '#0e1426',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          gap: 16, flexWrap: 'wrap',
        }}>
          {/* Tabs */}
          <div style={{ display: 'flex', gap: 6, background: '#131b31', padding: 4, borderRadius: 8 }}>
            <button
              onClick={() => setCategoryFilter('domain')}
              style={{
                background: categoryFilter === 'domain' ? 'var(--accent-purple)' : 'transparent',
                color: categoryFilter === 'domain' ? '#ffffff' : 'var(--text-secondary)',
                border: 'none', borderRadius: 6, padding: '6px 12px', fontSize: '0.75rem',
                fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                transition: 'all 0.15s ease',
              }}
            >
              <Sparkles size={13} />
              Scientific Domain KG ({domainCount})
            </button>
            <button
              onClick={() => setCategoryFilter('structural')}
              style={{
                background: categoryFilter === 'structural' ? 'var(--accent-blue)' : 'transparent',
                color: categoryFilter === 'structural' ? '#ffffff' : 'var(--text-secondary)',
                border: 'none', borderRadius: 6, padding: '6px 12px', fontSize: '0.75rem',
                fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                transition: 'all 0.15s ease',
              }}
            >
              <Layers size={13} />
              Structure & Provenance ({structuralCount})
            </button>
            <button
              onClick={() => setCategoryFilter('all')}
              style={{
                background: categoryFilter === 'all' ? '#334155' : 'transparent',
                color: categoryFilter === 'all' ? '#ffffff' : 'var(--text-secondary)',
                border: 'none', borderRadius: 6, padding: '6px 12px', fontSize: '0.75rem',
                fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                transition: 'all 0.15s ease',
              }}
            >
              <Database size={13} />
              All Triples ({triples.length})
            </button>
          </div>

          {/* Search Box */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            background: '#131b31', padding: '6px 12px', borderRadius: 8,
            border: '1px solid var(--border-subtle)', minWidth: 240, flex: 1, maxWidth: 360,
          }}>
            <Search size={14} style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search head, relation, tail, or type..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{
                background: 'transparent', border: 'none', outline: 'none',
                color: 'var(--text-primary)', fontSize: '0.78rem', width: '100%',
              }}
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 0 }}
              >
                <X size={12} />
              </button>
            )}
          </div>
        </div>

        {/* Content Table */}
        <div style={{ padding: '0 24px', flex: 1, overflowY: 'auto', background: '#0c1021' }}>
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 260, color: 'var(--text-muted)', gap: 10 }}>
              <Loader className="loading-spinner" size={20} /> Fetching extracted knowledge triples from Neo4j...
            </div>
          ) : error ? (
            <div style={{ margin: '24px 0', color: 'var(--accent-rose)', padding: 16, background: 'rgba(244,63,94,0.1)', borderRadius: 8, border: '1px solid rgba(244,63,94,0.3)' }}>
              Error: {error}
            </div>
          ) : filteredTriples.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '60px 20px' }}>
              <div style={{ marginBottom: 8, fontSize: '1.2rem' }}>🔍</div>
              No triples matched the current filter ({categoryFilter}) or search query.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', marginTop: 12 }}>
              <thead>
                <tr style={{
                  position: 'sticky', top: 0,
                  background: '#111827',
                  borderBottom: '2px solid rgba(148, 163, 184, 0.15)',
                  textAlign: 'left',
                  zIndex: 2,
                }}>
                  <th style={{ padding: '12px 14px', color: 'var(--text-secondary)', width: '30%' }}>Head Entity</th>
                  <th style={{ padding: '12px 14px', color: 'var(--text-secondary)', width: '12%' }}>Head Type</th>
                  <th style={{ padding: '12px 14px', color: 'var(--accent-purple)', width: '16%' }}>Relationship</th>
                  <th style={{ padding: '12px 14px', color: 'var(--text-secondary)', width: '30%' }}>Tail Entity</th>
                  <th style={{ padding: '12px 14px', color: 'var(--text-secondary)', width: '12%' }}>Tail Type</th>
                </tr>
              </thead>
              <tbody>
                {filteredTriples.map((t, i) => (
                  <tr
                    key={i}
                    style={{
                      borderBottom: '1px solid rgba(148, 163, 184, 0.08)',
                      background: i % 2 === 0 ? 'rgba(17, 24, 39, 0.4)' : 'transparent',
                    }}
                  >
                    <td style={{ padding: '12px 14px', fontWeight: 600, color: 'var(--text-primary)', wordBreak: 'break-word' }}>
                      {t.head}
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      {renderBadge(t.head_type)}
                    </td>
                    <td style={{ padding: '12px 14px', color: 'var(--accent-purple)', fontSize: '0.72rem', fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
                      ── {t.relation} ──▶
                    </td>
                    <td style={{ padding: '12px 14px', fontWeight: 600, color: 'var(--text-primary)', wordBreak: 'break-word' }}>
                      {t.tail}
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      {renderBadge(t.tail_type)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Modal Footer */}
        <div style={{
          padding: '12px 24px',
          background: '#111827',
          borderTop: '1px solid var(--border-subtle)',
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            Showing <strong>{filteredTriples.length}</strong> of <strong>{triples.length}</strong> graph edges stored in Neo4j with source attribution.
          </div>
          <div style={{ color: 'var(--accent-purple)', fontWeight: 500 }}>
            Provenanced Zero-Shot Graph
          </div>
        </div>
      </div>
    </div>
  );
}
