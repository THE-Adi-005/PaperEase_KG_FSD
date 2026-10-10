import { useState, useEffect, useRef } from 'react';
import { queryDual } from '../utils/api';
import ReasoningTrace from './ReasoningTrace';

export default function DualComparison({ selectedPaperIds, initialQuestion }) {
  const [question, setQuestion] = useState(initialQuestion || '');
  const [kgState, setKgState] = useState({ steps: [], answer: null, error: null });
  const [naiveState, setNaiveState] = useState({ steps: [], answer: null, error: null });
  const [isStreaming, setIsStreaming] = useState(false);
  
  // Auto-run if initialQuestion is provided
  useEffect(() => {
    if (initialQuestion && selectedPaperIds.length > 0) {
      handleRunQuery(initialQuestion);
    }
  }, [initialQuestion]);

  const handleRunQuery = async (qToRun) => {
    const q = qToRun || question;
    if (!q.trim() || selectedPaperIds.length === 0) return;
    
    setIsStreaming(true);
    setKgState({ steps: [], answer: null, error: null });
    setNaiveState({ steps: [], answer: null, error: null });
    
    try {
      const response = await fetch(queryDual(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: q,
          paper_ids: selectedPaperIds,
          mode: 'compare'
        }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let eventType = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            try {
              const data = JSON.parse(dataStr);
              
              if (eventType.startsWith('kg:')) {
                const subEvent = eventType.replace('kg:', '');
                updateState(setKgState, subEvent, data);
              } else if (eventType.startsWith('naive:')) {
                const subEvent = eventType.replace('naive:', '');
                updateState(setNaiveState, subEvent, data);
              }
            } catch (e) {
              // ignore parse error
            }
          }
        }
      }
    } catch (err) {
      setKgState(prev => ({ ...prev, error: err.message }));
      setNaiveState(prev => ({ ...prev, error: err.message }));
    } finally {
      setIsStreaming(false);
    }
  };

  const updateState = (setStateFn, type, data) => {
    setStateFn(prev => {
      if (type === 'answer') return { ...prev, answer: data };
      if (type === 'error') return { ...prev, error: data.message };
      if (['thought', 'action', 'observation', 'lazy'].includes(type)) {
        return { ...prev, steps: [...prev.steps, { type, ...data }] };
      }
      return prev;
    });
  };

  const calculateMetrics = () => {
    if (!kgState.answer || !naiveState.answer) return null;
    
    // Estimate Context Extracted
    // For KG, only count successful node retrievals (ignore error messages and empty hops)
    const kgChars = kgState.steps.filter(s => s.type === 'observation').reduce((acc, curr) => {
      const text = curr.text || '';
      if (text.includes('Found nodes:') || text.includes('Neighbors of') || text.includes('has')) {
        return acc + text.length;
      }
      return acc;
    }, 0);
    
    const naiveContextStr = naiveState.steps.find(s => s.text?.includes('Sending'))?.text || '';
    const naiveCharsMatch = naiveContextStr.match(/(\d+(?:,\d+)?)\s+characters/);
    const naiveChars = naiveCharsMatch ? parseInt(naiveCharsMatch[1].replace(',', ''), 10) : 2500;

    let efficiency = 0;
    if (naiveChars > 0 && kgChars < naiveChars) {
      efficiency = ((1 - (kgChars / naiveChars)) * 100).toFixed(1);
    }
    
    // Multi-hop Depth
    const kgHops = kgState.steps.filter(s => s.type === 'action').length;

    return { kgChars, naiveChars, efficiency, kgHops };
  };

  const metrics = calculateMetrics();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Top Bar */}
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-card)', display: 'flex', gap: 12 }}>
        <input 
          className="chat-input"
          style={{ flex: 1 }}
          value={question}
          onChange={e => setQuestion(e.target.value)}
          placeholder="Ask a comparison question..."
          onKeyDown={e => e.key === 'Enter' && handleRunQuery()}
          disabled={isStreaming}
        />
        <button 
          className="action-btn primary"
          onClick={() => handleRunQuery()}
          disabled={!question.trim() || isStreaming || selectedPaperIds.length === 0}
        >
          {isStreaming ? 'Running...' : 'Run Dual Test'}
        </button>
      </div>

      {metrics && (
        <div style={{ padding: '12px 20px', background: 'rgba(168, 85, 247, 0.05)', borderBottom: '1px solid var(--border-subtle)', display: 'flex', gap: 30, justifyContent: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Context Efficiency</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--accent-purple)' }}>
              {metrics.efficiency > 0 ? `${metrics.efficiency}% reduction` : '0% reduction (High Exploration)'}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>({metrics.kgChars} chars vs {metrics.naiveChars} chars)</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Multi-hop Depth</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--accent-purple)' }}>{metrics.kgHops} Graph Hops</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>(vs 0 in Naive flat retrieval)</div>
          </div>
        </div>
      )}

      {/* Split Panels */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        
        {/* Left: KG Grounded */}
        <div style={{ flex: 1, borderRight: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '12px 20px', background: 'rgba(168, 85, 247, 0.1)', color: 'var(--accent-purple)', fontWeight: 600, borderBottom: '1px solid rgba(168, 85, 247, 0.2)' }}>
            🧠 KG-Grounded Agent
          </div>
          
          <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
            {kgState.answer ? (
              <div className="message-bubble assistant" style={{ marginBottom: 20, maxWidth: '100%' }}>
                <div className="message-text">{kgState.answer.text}</div>
                <div style={{ marginTop: 12, display: 'flex', gap: 12, fontSize: '0.75rem', color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)', paddingTop: 8 }}>
                  <span>⏱ {kgState.answer.latency_ms || '>2000'}ms</span>
                  <span>⚙ {kgState.answer.steps_used} Steps</span>
                  <span>⚡ {kgState.answer.lazy_completion_count} Lazy Extracts</span>
                </div>
              </div>
            ) : null}
            
            <ReasoningTrace steps={kgState.steps} isStreaming={isStreaming && !kgState.answer && !naiveState.answer} />
            
            {kgState.error && <div style={{ color: 'var(--accent-rose)' }}>{kgState.error}</div>}
          </div>
        </div>

        {/* Right: Naive RAG */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '12px 20px', background: 'rgba(59, 130, 246, 0.1)', color: 'var(--accent-blue)', fontWeight: 600, borderBottom: '1px solid rgba(59, 130, 246, 0.2)' }}>
            📄 Naive RAG Baseline
          </div>
          
          <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
            {naiveState.answer ? (
              <div className="message-bubble assistant" style={{ marginBottom: 20, maxWidth: '100%', background: 'rgba(59, 130, 246, 0.05)' }}>
                <div className="message-text">{naiveState.answer.text}</div>
                <div style={{ marginTop: 12, display: 'flex', gap: 12, fontSize: '0.75rem', color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)', paddingTop: 8 }}>
                  <span>⏱ {naiveState.answer.latency_ms || '---'}ms</span>
                  <span>⚙ {naiveState.answer.steps_used} Steps</span>
                  <span>📄 Huge Context Chunk</span>
                </div>
              </div>
            ) : null}
            
            <ReasoningTrace steps={naiveState.steps} isStreaming={isStreaming && !naiveState.answer && !kgState.answer} />
            
            {naiveState.error && <div style={{ color: 'var(--accent-rose)' }}>{naiveState.error}</div>}
          </div>
        </div>

      </div>
    </div>
  );
}
