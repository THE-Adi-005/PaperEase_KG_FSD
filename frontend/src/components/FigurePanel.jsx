import { Image, Table2 } from 'lucide-react';

export default function FigurePanel({ figures = [], tables = [] }) {
  if (figures.length === 0 && tables.length === 0) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', height: '100%', color: 'var(--text-muted)',
        gap: 8, fontSize: '0.85rem',
      }}>
        <Image size={28} />
        <span>Figures & tables will appear here</span>
      </div>
    );
  }

  return (
    <div>
      {figures.map(fig => (
        <div key={fig.id} className="figure-card">
          {fig.image_path && (
            <img
              src={`http://localhost:8000${fig.image_path}`}
              alt={fig.caption || fig.label}
              loading="lazy"
            />
          )}
          <div className="figure-label">{fig.label}</div>
          {fig.caption && <div className="figure-caption">{fig.caption}</div>}
        </div>
      ))}

      {tables.map(tbl => (
        <div key={tbl.id} className="figure-card">
          <div className="figure-label">
            <Table2 size={13} style={{ marginRight: 6, verticalAlign: 'middle' }} />
            {tbl.label}
          </div>
          {tbl.caption && <div className="figure-caption">{tbl.caption}</div>}
          {tbl.headers && tbl.headers.length > 0 && tbl.rows && tbl.rows.length > 0 && (
            <table className="data-table">
              <thead>
                <tr>
                  {tbl.headers.map((h, i) => <th key={i}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {tbl.rows.slice(0, 20).map((row, ri) => (
                  <tr key={ri}>
                    {row.map((cell, ci) => <td key={ci}>{cell}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ))}
    </div>
  );
}
