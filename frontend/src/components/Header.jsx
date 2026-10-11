import { useState, useEffect } from 'react';
import { Menu, PanelLeftClose, PanelLeft, Share2, BookOpen, User, CheckCircle2 } from 'lucide-react';
import { checkHealth } from '../utils/api';

export default function Header({ onToggleSidebar, isSidebarOpen, onOpenCatalog }) {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    const check = async () => {
      const h = await checkHealth();
      setHealth(h);
    };
    check();
    const interval = setInterval(check, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="app-header">
      <div className="header-brand">
        <button
          className="hamburger-btn"
          onClick={onToggleSidebar}
          title={isSidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          aria-label="Toggle navigation menu"
        >
          {isSidebarOpen ? <PanelLeftClose size={19} /> : <Menu size={20} />}
        </button>

        <div className="logo-icon" style={{ cursor: 'pointer' }} onClick={() => window.location.reload()}>
          <Share2 size={19} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <h1 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
            PaperEase <span style={{ color: 'var(--accent-blue)', fontWeight: 600, fontSize: '0.85rem' }}>Research AI</span>
          </h1>
        </div>
      </div>
      
      <div className="header-status">

        <div className="status-dot" title="Neo4j Knowledge Graph: 1,546 Nodes & 1,634 Relationships">
          <div className={`dot ${health?.neo4j ? 'active' : ''}`} />
          <span>Neo4j</span>
        </div>
        <div className="status-dot" title="Ollama Local LLM Inference Engine: Qwen 2.5 7B">
          <div className={`dot ${health?.ollama ? 'active' : ''}`} />
          <span>Ollama</span>
        </div>
        <div className="status-dot" title="Qdrant Vector Database: 768-dim Dense Storage">
          <div className="dot active" />
          <span>Vector DB</span>
        </div>

        <div className="user-profile-badge" style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 10px',
          background: '#eff6ff',
          borderRadius: 20,
          border: '1px solid #bfdbfe',
          marginLeft: 8,
          fontSize: '0.74rem',
          fontWeight: 600,
          color: 'var(--accent-blue)',
        }}>
          <div style={{
            width: 20,
            height: 20,
            borderRadius: '50%',
            background: 'var(--accent-blue)',
            color: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.65rem',
            fontWeight: 700,
          }}>
            A
          </div>
          <span>Adithya R</span>
        </div>
      </div>
    </header>
  );
}
