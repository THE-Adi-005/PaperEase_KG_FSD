import { useState, useEffect, useCallback } from 'react';

const API = 'http://localhost:8000/api/experiments';

function fmt(v, decimals = 3) {
  if (v === undefined || v === null || v === '') return '--';
  const n = parseFloat(v);
  if (isNaN(n)) return '--';
  return n.toFixed(decimals);
}

function pct(v) {
  if (v === undefined || v === null || v === '') return '--';
  const n = parseFloat(v);
  if (isNaN(n)) return '--';
  return (n * 100).toFixed(1) + '%';
}

// ── Simple bar chart (pure SVG) ──────────────────────────────────────────────
function BarChart({ rows, xKey, yKey, title, color = '#a78bfa' }) {
  if (!rows || rows.length === 0) return null;
  const valid = rows.filter(r => r[yKey] !== undefined && r[yKey] !== '' && !isNaN(parseFloat(r[yKey])));
  if (valid.length === 0) return <div style={{ color: 'var(--text-secondary)', fontSize: '0.78rem', padding: '8px' }}>No data yet</div>;

  const maxY = Math.max(...valid.map(r => parseFloat(r[yKey])));
  const W = 320, H = 120, pad = { top: 12, right: 8, bottom: 32, left: 36 };
  const barW = Math.max(8, (W - pad.left - pad.right) / valid.length - 4);
  const scaleY = (v) => H - pad.bottom - ((parseFloat(v) / (maxY || 1)) * (H - pad.top - pad.bottom));

  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>{title}</div>
      <svg width={W} height={H} style={{ overflow: 'visible' }}>
        {valid.map((r, i) => {
          const x = pad.left + i * ((W - pad.left - pad.right) / valid.length);
          const y = scaleY(r[yKey]);
          const h = H - pad.bottom - y;
          return (
            <g key={i}>
              <rect x={x} y={y} width={barW} height={h} fill={color} rx={2} opacity={0.85} />
              <text x={x + barW / 2} y={H - pad.bottom + 12} textAnchor="middle"
                style={{ fontSize: '0.55rem', fill: 'var(--text-secondary)' }}>
                {String(r[xKey]).replace('kg_', '').replace('_nolazy', '').slice(0, 10)}
              </text>
              <text x={x + barW / 2} y={y - 3} textAnchor="middle"
                style={{ fontSize: '0.55rem', fill: '#e2e8f0' }}>
                {fmt(r[yKey], 2)}
              </text>
            </g>
          );
        })}
        <line x1={pad.left} y1={pad.top} x2={pad.left} y2={H - pad.bottom} stroke="var(--border-subtle)" />
        <line x1={pad.left} y1={H - pad.bottom} x2={W - pad.right} y2={H - pad.bottom} stroke="var(--border-subtle)" />
        <text x={pad.left - 4} y={pad.top + 4} textAnchor="end" style={{ fontSize: '0.52rem', fill: 'var(--text-secondary)' }}>
          {fmt(maxY, 2)}
        </text>
        <text x={pad.left - 4} y={H - pad.bottom} textAnchor="end" style={{ fontSize: '0.52rem', fill: 'var(--text-secondary)' }}>0</text>
      </svg>
    </div>
  );
}

// ── Prediction comparison row ─────────────────────────────────────────────────
function PredRow({ pred }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{
      borderBottom: '1px solid var(--border-subtle)',
      padding: '6px 0',
    }}>
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', cursor: 'pointer' }}
        onClick={() => setOpen(o => !o)}>
        <span style={{
          width: 16, height: 16, borderRadius: '50%', flexShrink: 0,
          background: pred.correct ? '#22c55e' : '#f43f5e',
          display: 'inline-block',
        }} />
        <span style={{ fontSize: '0.78rem', color: 'var(--text-primary)', flex: 1 }}>{pred.question}</span>
        <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
          {pred.type} | {pred.steps}s
        </span>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div style={{ marginTop: '6px', paddingLeft: '24px', fontSize: '0.75rem' }}>
          <div><span style={{ color: 'var(--text-secondary)' }}>Answer: </span>{pred.answer || '(empty)'}</div>
          <div><span style={{ color: 'var(--text-secondary)' }}>Gold: </span>{(pred.gold_answers || []).join(', ') || '—'}</div>
          {pred.trace && (
            <details style={{ marginTop: '4px' }}>
              <summary style={{ color: 'var(--text-secondary)', cursor: 'pointer' }}>Trace</summary>
              <pre style={{ fontSize: '0.65rem', color: '#94a3b8', whiteSpace: 'pre-wrap', maxHeight: '120px', overflowY: 'auto' }}>
                {pred.trace}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function ExperimentsPanel() {
  const [experiments, setExperiments] = useState([]);
  const [sortKey, setSortKey] = useState('acc');
  const [sortAsc, setSortAsc] = useState(false);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [preds, setPreds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(API);
      if (!res.ok) throw new Error(res.statusText);
      const data = await res.json();
      setExperiments(data.experiments || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const loadDetail = async (sid) => {
    setSelected(sid);
    setDetail(null);
    setPreds([]);
    try {
      const [det, pr] = await Promise.all([
        fetch(`${API}/${sid}`).then(r => r.ok ? r.json() : null),
        fetch(`${API}/${sid}/predictions?limit=50`).then(r => r.ok ? r.json() : null),
      ]);
      setDetail(det);
      setPreds(pr?.predictions || []);
    } catch (e) {
      console.error(e);
    }
  };

  const sorted = [...experiments].sort((a, b) => {
    const av = parseFloat(a[sortKey] ?? 0) || 0;
    const bv = parseFloat(b[sortKey] ?? 0) || 0;
    return sortAsc ? av - bv : bv - av;
  });

  const cols = [
    { key: 'system_id', label: 'System', fmt: v => v },
    { key: 'acc', label: 'Acc.', fmt: v => fmt(v) },
    { key: 'acc_lo', label: 'CI lo', fmt: v => fmt(v) },
    { key: 'acc_hi', label: 'CI hi', fmt: v => fmt(v) },
    { key: 'acc_cross_paper', label: 'Cross-paper', fmt: v => fmt(v) },
    { key: 'abstain_rate_unanswerable', label: 'Abstain%', fmt: pct },
    { key: 'evidence_hit', label: 'Ev.hit', fmt: v => fmt(v) },
    { key: 'mean_steps', label: 'Steps', fmt: v => fmt(v, 1) },
    { key: 'mean_latency', label: 'Lat(s)', fmt: v => fmt(v, 1) },
  ];

  const toggle = (k) => {
    if (sortKey === k) setSortAsc(a => !a);
    else { setSortKey(k); setSortAsc(false); }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.9rem' }}>Ablation Experiments</span>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{experiments.length} runs</span>
        <button
          id="experiments-refresh-btn"
          onClick={load}
          style={{ marginLeft: 'auto', fontSize: '0.72rem', padding: '3px 8px', borderRadius: '4px',
            background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', cursor: 'pointer', color: 'var(--text-secondary)' }}>
          ↻ Refresh
        </button>
      </div>

      {loading && <div style={{ padding: '12px', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Loading…</div>}
      {error && <div style={{ padding: '12px', color: 'var(--accent-rose)', fontSize: '0.8rem' }}>Error: {error}</div>}

      {!loading && experiments.length === 0 && !error && (
        <div style={{ padding: '16px', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
          No experiments yet. Run <code style={{ background: 'var(--bg-elevated)', padding: '2px 4px', borderRadius: '3px' }}>python -m eval.run_qa --system kg --config cfg_base --lazy off</code> to start.
        </div>
      )}

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Left: sortable table */}
        <div style={{ flex: 1, overflowY: 'auto', borderRight: '1px solid var(--border-subtle)' }}>
          {sorted.length > 0 && (
            <>
              {/* Charts */}
              <div style={{ padding: '12px 12px 0' }}>
                <BarChart rows={sorted.filter(r => r.config?.startsWith('cfg_r'))} xKey="config" yKey="acc"
                  title="Accuracy vs. relation-set size" color="#a78bfa" />
                <BarChart rows={sorted.filter(r => r.config?.startsWith('cfg_k'))} xKey="config" yKey="acc"
                  title="Accuracy vs. cap K" color="#34d399" />
              </div>
              {/* Table */}
              <div style={{ overflowX: 'auto', padding: '0 4px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.72rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      {cols.map(c => (
                        <th key={c.key}
                          id={`exp-col-${c.key}`}
                          onClick={() => toggle(c.key)}
                          style={{ padding: '6px 6px', textAlign: 'left', cursor: 'pointer',
                            color: sortKey === c.key ? 'var(--accent-purple)' : 'var(--text-secondary)',
                            whiteSpace: 'nowrap', fontWeight: 600 }}>
                          {c.label}{sortKey === c.key ? (sortAsc ? ' ↑' : ' ↓') : ''}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {sorted.map(row => (
                      <tr key={row.system_id}
                        id={`exp-row-${row.system_id}`}
                        onClick={() => loadDetail(row.system_id)}
                        style={{
                          cursor: 'pointer',
                          background: selected === row.system_id ? 'rgba(167,139,250,0.08)' : 'transparent',
                          borderBottom: '1px solid var(--border-subtle)',
                        }}>
                        {cols.map(c => (
                          <td key={c.key} style={{ padding: '5px 6px', whiteSpace: 'nowrap',
                            color: c.key === 'system_id' ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                            {c.fmt(row[c.key])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        {/* Right: detail pane */}
        {selected && (
          <div style={{ width: '320px', overflowY: 'auto', padding: '12px', fontSize: '0.75rem' }}>
            <div style={{ fontWeight: 600, marginBottom: '8px', color: 'var(--text-primary)' }}>
              {selected}
            </div>

            {detail?.graph_stats && (
              <div style={{ marginBottom: '12px' }}>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.68rem', marginBottom: '4px' }}>Graph stats</div>
                {Object.entries(detail.graph_stats).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>{k}</span>
                    <span>{typeof v === 'number' ? v.toLocaleString() : v}</span>
                  </div>
                ))}
              </div>
            )}

            {detail?.metrics && (
              <div style={{ marginBottom: '12px' }}>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.68rem', marginBottom: '4px' }}>Metrics</div>
                {Object.entries(detail.metrics)
                  .filter(([k]) => !['acc_by_type', 'acc_by_source'].includes(k))
                  .map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>{k}</span>
                      <span>{typeof v === 'number' ? v.toFixed(3) : String(v)}</span>
                    </div>
                  ))}
                {detail.metrics.acc_by_type && (
                  <>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.65rem', marginTop: '6px', marginBottom: '2px' }}>By type</div>
                    {Object.entries(detail.metrics.acc_by_type).map(([k, v]) => (
                      <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '1px 0', paddingLeft: '8px' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>{k}</span>
                        <span>{typeof v === 'number' ? v.toFixed(3) : v}</span>
                      </div>
                    ))}
                  </>
                )}
              </div>
            )}

            {preds.length > 0 && (
              <div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.68rem', marginBottom: '6px' }}>
                  Predictions ({preds.length})
                </div>
                {preds.map(p => <PredRow key={p.id} pred={p} />)}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
