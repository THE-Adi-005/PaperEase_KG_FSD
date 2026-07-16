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
              <div className="message-text">{msg.text}</div>
              {msg.meta && msg.meta.steps_used && (
                <div style={{ marginTop: 8, fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  {msg.meta.steps_used} reasoning steps
                  {msg.meta.lazy_completion_count > 0 &&
                    ` • ${msg.meta.lazy_completion_count} lazy completions`}
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
