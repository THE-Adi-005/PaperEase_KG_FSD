import { useEffect, useState } from 'react';
import { Brain } from 'lucide-react';
import { checkHealth } from '../utils/api';

export default function Header() {
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
    <header className="header">
      <div className="header-logo">
        <div className="logo-icon">
          <Brain size={16} />
        </div>
        <h1>KG Paper Assistant</h1>
      </div>
      <div className="header-status">
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
