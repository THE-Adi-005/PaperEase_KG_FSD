import { useState, useEffect } from 'react';
import { Share2, BookOpen } from 'lucide-react';
import { checkHealth } from '../utils/api';

export default function Header({ onOpenCatalog }) {
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
        <div className="logo-icon">
          <Share2 size={20} />
        </div>
        <h1>KG Paper Assistant</h1>
      </div>
      
      <div className="header-status">
        <button 
          className="action-btn primary"
          onClick={onOpenCatalog}
          style={{ marginRight: 16 }}
          title="Browse & Run from 80 Gold Benchmark Questions"
        >
          <BookOpen size={14} /> 📋 Sample Questions (80)
        </button>

        <div className="status-dot">
          <div className={`dot ${health?.neo4j ? 'active' : ''}`} />
          Neo4j
        </div>
        <div className="status-dot">
          <div className={`dot ${health?.ollama ? 'active' : ''}`} />
          Ollama
        </div>
        <div className="status-dot">
          <div className={`dot ${health?.grobid ? 'active' : ''}`} />
          GROBID
        </div>
      </div>
    </header>
  );
}
