import { useState, useEffect, useRef } from 'react';
import { Play, Sparkles, Database, Code2, Zap } from 'lucide-react';
import { seedDemoData, getDemoQuestions } from '../utils/api';

export default function DemoPanel({ onSelectQuestion, selectedPaperIds, refreshPapers }) {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);

  useEffect(() => {
    getDemoQuestions().then(setQuestions).catch(console.error);
  }, []);

  const handleSeed = async () => {
    setSeeding(true);
    try {
      await seedDemoData();
      await refreshPapers();
      alert("Success! 3 seminal AI papers (Transformer, BERT, GPT-3) have been seeded into the KG.");
    } catch (err) {
      alert("Failed to seed data: " + err.message);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="demo-panel" style={{ padding: 20, background: 'var(--bg-card)', borderRadius: 8, margin: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <Sparkles size={24} color="var(--accent-purple)" />
        <h2 style={{ margin: 0 }}>Meaningful Demo Mode</h2>
      </div>
      
      <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
        This demo proves how Knowledge-Graph grounding improves LLM reasoning by comparing it 
        side-by-side with standard Naive RAG.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 24 }}>
        
        {/* Left: Setup */}
        <div style={{ padding: 16, border: '1px solid var(--border-subtle)', borderRadius: 8 }}>
          <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Database size={16} /> 1. Prepare Data
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 16 }}>
            Click below to instantly populate the graph with realistic data from 3 classic AI papers, 
            skipping the slow PDF upload step.
          </p>
          <button 
            className="action-btn primary" 
            style={{ width: '100%', justifyContent: 'center' }}
            onClick={handleSeed}
            disabled={seeding}
          >
            {seeding ? "Seeding Graph..." : "Seed KG Demo Data"}
          </button>
        </div>

        {/* Right: Questions */}
        <div style={{ padding: 16, border: '1px solid var(--border-subtle)', borderRadius: 8 }}>
          <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Play size={16} /> 2. Run Comparison
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 16 }}>
            Select <strong>all 3 demo papers</strong> in the sidebar, then click a question below to run both RAG pipelines concurrently.
          </p>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {questions.map(q => (
              <button 
                key={q.id}
                className="action-btn outline"
                style={{ textAlign: 'left', display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}
                onClick={() => onSelectQuestion(q.text)}
                disabled={selectedPaperIds.length === 0}
              >
                <div style={{ fontWeight: 500 }}>"{q.text}"</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--accent-blue)', marginTop: 4 }}>
                  Highlight: {q.highlights}
                </div>
              </button>
            ))}
          </div>
          
          {selectedPaperIds.length === 0 && (
            <div style={{ fontSize: '0.8rem', color: 'var(--accent-rose)', marginTop: 12 }}>
              ⚠ Please select at least one paper from the sidebar first.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
