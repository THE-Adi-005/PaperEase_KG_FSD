import { useState, useEffect, useMemo } from 'react';
import { X, Search, BookOpen, Layers, CheckCircle2, ArrowRight, Zap, Target, Flame } from 'lucide-react';
import { getBenchmarkQuestions, getUnseenQuestions } from '../utils/api';

const PAPER_LABELS = {
  "1e6c7c12": "GPT (Radford 2018)",
  "b7f9484b": "XLNet (Yang 2019)",
  "f7d92af0": "Statistical Inference",
  "680a27f3": "EVOPAT (Patent System)",
  "demo_attention_2017": "Attention Is All You Need",
  "demo_bert_2018": "BERT (Devlin 2018)",
  "demo_gpt3_2020": "GPT-3 (Brown 2020)",
  "demo_roberta_2019": "RoBERTa (Liu 2019)",
  "demo_t5_2020": "T5 (Raffel 2020)",
  "demo_electra_2020": "ELECTRA (Clark 2020)",
};

export default function BenchmarkCatalogModal({ isOpen, onClose, onSelectQuestion }) {
  const [questions, setQuestions] = useState([]);
  const [unseenQuestions, setUnseenQuestions] = useState([]);
  const [activeTab, setActiveTab] = useState('all'); // 'all' | 'unseen' | 'lookup' | 'multihop' | 'aggregation' | 'cross_paper'
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && questions.length === 0) {
      setLoading(true);
      Promise.all([
        getBenchmarkQuestions().catch(() => []),
        getUnseenQuestions().catch(() => []),
      ])
        .then(([bench, unseen]) => {
          setQuestions(bench || []);
          setUnseenQuestions(unseen || []);
        })
        .finally(() => setLoading(false));
    }
  }, [isOpen, questions.length]);

  const allCombined = useMemo(() => {
    return [...unseenQuestions, ...questions];
  }, [unseenQuestions, questions]);

  const filtered = useMemo(() => {
    let pool = allCombined;
    if (activeTab === 'unseen') {
      pool = unseenQuestions;
    } else if (activeTab !== 'all') {
      pool = questions.filter(q => q.type === activeTab);
    }

    if (!search.trim()) return pool;
    const term = search.toLowerCase();
    return pool.filter(q => {
      const qText = (q.question || '').toLowerCase();
      const gText = (q.gold_answers || []).join(' ').toLowerCase();
      const pText = (q.paper_ids || []).map(pid => PAPER_LABELS[pid] || pid).join(' ').toLowerCase();
      return qText.includes(term) || gText.includes(term) || pText.includes(term);
    });
  }, [allCombined, questions, unseenQuestions, activeTab, search]);

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(15, 23, 42, 0.45)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '24px',
    }}>
      <div style={{
        background: '#ffffff',
        borderRadius: '16px',
        width: '100%',
        maxWidth: '960px',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 20px 40px rgba(15, 23, 42, 0.2)',
        overflow: 'hidden',
        border: '1px solid var(--border-subtle)',
      }}>
        {/* Header */}
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%)',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              <BookOpen size={20} color="var(--accent-blue)" /> Questions Benchmark &amp; Real-Time Test Catalog
            </div>
            <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: 2 }}>
              Choose from the <strong>80 Gold Benchmark Questions</strong> or test with the <strong>16 Real-Time Unseen Test Set</strong> to evaluate live with BERTScore, Cosine, and BLEU.
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: '#ffffff',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '6px 10px',
              cursor: 'pointer',
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Filters & Search Toolbar */}
        <div style={{
          padding: '12px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 12,
          flexWrap: 'wrap',
          background: '#ffffff',
        }}>
          {/* Category Tabs */}
          <div style={{ display: 'flex', gap: 6, background: '#f1f5f9', padding: 4, borderRadius: 8, overflowX: 'auto' }}>
            {[
              { id: 'all', label: `All (${allCombined.length})` },
              { id: 'unseen', label: `🔥 Real-Time Unseen (${unseenQuestions.length || 16})` },
              { id: 'lookup', label: 'Lookup (20)' },
              { id: 'multihop', label: 'Multi-Hop (20)' },
              { id: 'aggregation', label: 'Aggregation (20)' },
              { id: 'cross_paper', label: 'Cross-Paper (20)' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  background: activeTab === tab.id ? 'var(--accent-blue)' : 'transparent',
                  color: activeTab === tab.id ? '#ffffff' : 'var(--text-secondary)',
                  border: 'none',
                  borderRadius: 6,
                  padding: '6px 12px',
                  fontSize: '0.74rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  whiteSpace: 'nowrap',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Search Input */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            background: '#f8fafc',
            border: '1px solid var(--border-subtle)',
            borderRadius: 8,
            padding: '6px 12px',
            width: 240,
          }}>
            <Search size={14} color="var(--text-muted)" />
            <input
              type="text"
              placeholder="Search questions, targets, papers..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                outline: 'none',
                fontSize: '0.75rem',
                width: '100%',
                color: 'var(--text-primary)',
              }}
            />
          </div>
        </div>

        {/* Question List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
              Loading questions dataset...
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
              No questions found matching your filter.
            </div>
          ) : (
            filtered.map((q, idx) => {
              const isUnseen = Boolean(q.unseen || q.id?.startsWith('u'));

              return (
                <div
                  key={q.id || idx}
                  style={{
                    background: isUnseen ? '#fffbeb' : '#ffffff',
                    border: `1px solid ${isUnseen ? '#fef08a' : 'var(--border-subtle)'}`,
                    borderRadius: 10,
                    padding: '14px 16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 8,
                    boxShadow: 'var(--shadow-sm)',
                    transition: 'border-color 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      {/* Tier Badge */}
                      <span style={{
                        fontSize: '0.66rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        padding: '2px 8px',
                        borderRadius: 6,
                        background: isUnseen ? '#fef3c7' : '#eff6ff',
                        color: isUnseen ? '#b45309' : 'var(--accent-blue)',
                        border: `1px solid ${isUnseen ? '#fde68a' : '#bfdbfe'}`,
                      }}>
                        {isUnseen ? '🔥 Live Unseen' : q.type}
                      </span>

                      {/* Paper Tags */}
                      {(q.paper_ids || []).map(pid => (
                        <span key={pid} style={{
                          fontSize: '0.65rem',
                          background: '#f1f5f9',
                          color: '#475569',
                          padding: '2px 8px',
                          borderRadius: 6,
                        }}>
                          {PAPER_LABELS[pid] || pid}
                        </span>
                      ))}
                    </div>

                    {/* Action Button */}
                    <button
                      className="action-btn primary"
                      onClick={() => onSelectQuestion(q)}
                      style={{
                        padding: '5px 12px',
                        fontSize: '0.74rem',
                        background: isUnseen ? 'linear-gradient(135deg, #d97706 0%, #b45309 100%)' : undefined,
                      }}
                    >
                      🚀 Run in Arena <ArrowRight size={12} />
                    </button>
                  </div>

                  <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {q.question}
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: 'var(--text-muted)', flexWrap: 'wrap', gap: 6 }}>
                    <div>
                      <strong style={{ color: '#15803d' }}>Gold Target: </strong>
                      {(q.gold_answers || []).join(' | ')}
                    </div>
                    {q.evidence && (
                      <div style={{ fontStyle: 'italic', maxWidth: '60%', textAlign: 'right' }}>
                        Source: {q.evidence}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
