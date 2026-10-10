import { useState, useRef, useEffect } from 'react';
import { Send, MessageSquare, Sparkles } from 'lucide-react';

export default function ChatPanel({ selectedPaperIds, onSendQuery, answer, isStreaming }) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, answer]);

  // Add answer as assistant message when it arrives
  useEffect(() => {
    if (answer && answer.text) {
      setMessages(prev => {
        // Avoid duplicates
        const last = prev[prev.length - 1];
        if (last && last.role === 'assistant' && last.text === answer.text) return prev;
        return [...prev, { role: 'assistant', text: answer.text, meta: answer }];
      });
    }
  }, [answer]);

  const handleSend = () => {
    const q = input.trim();
    if (!q || isStreaming || selectedPaperIds.length === 0) return;
    setMessages(prev => [...prev, { role: 'user', text: q }]);
    onSendQuery(q);
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="empty-icon">
              <Sparkles size={28} />
            </div>
            <h3>Ask about your papers</h3>
            <p>
              {selectedPaperIds.length === 0
                ? 'Upload and select a paper from the sidebar to get started'
                : `${selectedPaperIds.length} paper${selectedPaperIds.length > 1 ? 's' : ''} selected — ask any question`
              }
            </p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`message-bubble ${msg.role}`}>
              {msg.role === 'assistant' && msg.meta && (
                <div style={{ marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.68rem' }}>
                  {msg.meta.mode === 'multi_agent' ? (
                    <span style={{
                      background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.2), rgba(59, 130, 246, 0.2))',
                      color: '#c084fc',
                      border: '1px solid rgba(168, 85, 247, 0.4)',
                      padding: '2px 8px', borderRadius: 10, fontWeight: 600,
                    }}>
                      🤖 KG Multi-Agent (4-Stage Specialist Pipeline)
                    </span>
                  ) : msg.meta.mode === 'naive_rag' ? (
                    <span style={{
                      background: 'rgba(59, 130, 246, 0.15)',
                      color: 'var(--accent-blue)',
                      border: '1px solid rgba(59, 130, 246, 0.3)',
                      padding: '2px 8px', borderRadius: 10, fontWeight: 600,
                    }}>
                      📄 Naive RAG Baseline (Flat Retrieval)
                    </span>
                  ) : (
                    <span style={{
                      background: 'rgba(168, 85, 247, 0.15)',
                      color: 'var(--accent-purple)',
                      border: '1px solid rgba(168, 85, 247, 0.3)',
                      padding: '2px 8px', borderRadius: 10, fontWeight: 600,
                    }}>
                      ⚡ KG Single-Agent (ReACT)
                    </span>
                  )}
                </div>
              )}
              <div className="message-text">{msg.text}</div>
              {msg.meta && (
                <div style={{ marginTop: 8, fontSize: '0.7rem', color: 'var(--text-muted)', borderTop: '1px solid rgba(148, 163, 184, 0.1)', paddingTop: 6, display: 'flex', flexWrap: 'wrap', gap: 10 }}>
                  {msg.meta.mode === 'multi_agent' ? (
                    <>
                      <span>🎯 {msg.meta.pipeline_trace?.sub_questions || 0} sub-questions</span>
                      <span>🔍 {msg.meta.pipeline_trace?.total_evidence || 0} KG evidence</span>
                      <span>🛡️ {Math.round((msg.meta.pipeline_trace?.verification_confidence || 0) * 100)}% verified</span>
                      {msg.meta.pipeline_trace?.revision_loops > 0 && <span>🔄 {msg.meta.pipeline_trace.revision_loops} revision</span>}
                      {msg.meta.pipeline_trace?.total_duration_ms ? (
                        <span>⏱ {msg.meta.pipeline_trace.total_duration_ms}ms</span>
                      ) : msg.meta.latency_ms ? (
                        <span>⏱ {msg.meta.latency_ms}ms</span>
                      ) : null}
                    </>
                  ) : msg.meta.mode === 'naive_rag' ? (
                    <>
                      <span>0 Graph Hops</span>
                      <span>📦 {msg.meta.context_chars?.toLocaleString() || '10,000+'} raw chars context</span>
                      {msg.meta.latency_ms && <span>⏱ {msg.meta.latency_ms}ms</span>}
                    </>
                  ) : (
                    <>
                      <span>⚙ {msg.meta.steps_used} reasoning hops</span>
                      {msg.meta.lazy_completion_count > 0 && <span>⚡ {msg.meta.lazy_completion_count} lazy completions</span>}
                      {msg.meta.latency_ms && <span>⏱ {msg.meta.latency_ms}ms</span>}
                    </>
                  )}
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <div className="chat-input-wrapper">
          <MessageSquare size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
          <input
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              selectedPaperIds.length === 0
                ? 'Select a paper first...'
                : selectedPaperIds.length > 1
                  ? 'Ask a cross-paper question...'
                  : 'Ask about this paper...'
            }
            disabled={selectedPaperIds.length === 0 || isStreaming}
          />
          <button
            className="send-button"
            onClick={handleSend}
            disabled={!input.trim() || selectedPaperIds.length === 0 || isStreaming}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
