import { useRef, useEffect, useState } from 'react';
import { 
  ChevronDown, ChevronUp, Brain, Wrench, Eye, Zap, 
  Target, ShieldCheck, AlertCircle, RefreshCw, GitFork, CheckCircle2
} from 'lucide-react';

const STEP_CONFIG = {
  thought: { icon: Brain, label: '💭 Thought', className: 'thought' },
  planning: { icon: Target, label: '🎯 Planner Agent', className: 'planning' },
  action: { icon: Wrench, label: '🔧 Action', className: 'action' },
  observation: { icon: Eye, label: '👁 Observation', className: 'observation' },
  reasoning: { icon: GitFork, label: '🧠 Reasoner Agent', className: 'reasoning' },
  verifying: { icon: ShieldCheck, label: '🛡️ Verifier Agent', className: 'verifying' },
  revision: { icon: RefreshCw, label: '🔄 Revision Loop', className: 'revision' },
  lazy: { icon: Zap, label: '⚡ Lazy Completion', className: 'lazy' },
};

export default function ReasoningTrace({ steps, isStreaming }) {
  const [collapsed, setCollapsed] = useState(false);
  const scrollRef = useRef();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [steps]);

  if (!steps || steps.length === 0) return null;

  return (
    <div className="reasoning-trace">
      <div className="reasoning-header" onClick={() => setCollapsed(!collapsed)}>
        <span>
          Traceable Reasoning ({steps.length} events)
          {isStreaming && <span className="pulse" style={{ marginLeft: 8 }}>● Live Agents</span>}
        </span>
        {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
      </div>

      {!collapsed && (
        <div className="reasoning-steps" ref={scrollRef}>
          {steps.map((step, i) => {
            const config = STEP_CONFIG[step.type] || STEP_CONFIG.thought;
            const Icon = config.icon;

            return (
              <div key={i} className={`reason-step ${config.className}`}>
                <div className="step-icon">
                  <Icon size={11} />
                </div>
                <div className="step-content">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem', fontWeight: 600 }}>
                      {config.label}
                    </span>
                    {step.step && (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>
                        #{step.step}
                      </span>
                    )}
                  </div>

                  {/* Planner Agent Decomposition */}
                  {step.type === 'planning' && step.sub_questions && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4 }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                        Decomposed question into {step.count || step.sub_questions.length} retrieval targets:
                      </div>
                      {step.sub_questions.map((sq, idx) => (
                        <div key={idx} style={{
                          background: 'rgba(14, 165, 233, 0.08)',
                          border: '1px solid rgba(14, 165, 233, 0.25)',
                          borderRadius: 6, padding: '4px 8px', fontSize: '0.72rem',
                          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        }}>
                          <span>{sq.text}</span>
                          <span style={{
                            fontSize: '0.62rem', background: 'rgba(14, 165, 233, 0.2)',
                            color: '#38bdf8', padding: '1px 6px', borderRadius: 4, fontFamily: 'monospace'
                          }}>
                            {sq.retrieval_strategy}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Reasoner Agent Synthesis */}
                  {step.type === 'reasoning' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4 }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                        Synthesized {step.step_count || (step.reasoning_steps?.length || 0)} grounded reasoning steps with graph paths
                      </div>
                      {step.reasoning_steps?.slice(0, 3).map((rs, idx) => (
                        <div key={idx} style={{
                          background: 'rgba(168, 85, 247, 0.08)',
                          border: '1px solid rgba(168, 85, 247, 0.25)',
                          borderRadius: 6, padding: '4px 8px', fontSize: '0.7rem',
                        }}>
                          <div style={{ fontWeight: 600, color: '#c084fc' }}>Step {rs.step_number}: {rs.claim}</div>
                          {rs.graph_path?.length > 0 && (
                            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'monospace', marginTop: 2 }}>
                              🔗 {rs.graph_path.join(' → ')}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Verifier Agent Fact-Check */}
                  {step.type === 'verifying' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{
                          fontSize: '0.75rem', fontWeight: 700,
                          color: step.passed ? '#34d399' : '#fb7185',
                        }}>
                          Confidence: {Math.round((step.confidence_score || 0) * 100)}%
                        </span>
                        <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                          ({step.verified_claims?.length || 0} claims verified against KG provenance)
                        </span>
                      </div>
                      {step.revision_suggested && (
                        <div style={{ fontSize: '0.68rem', color: '#fb7185' }}>
                          ⚠️ Confidence below threshold — triggering retrieval revision loop
                        </div>
                      )}
                    </div>
                  )}

                  {/* Revision Loop */}
                  {step.type === 'revision' && (
                    <div style={{ fontSize: '0.72rem', color: '#fb7185', marginTop: 2 }}>
                      Loop #{step.loop}: {step.reason}
                    </div>
                  )}

                  {/* Standard ReACT & Tool Steps */}
                  {step.type === 'thought' && (
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>{step.text}</div>
                  )}
                  {step.type === 'action' && (
                    <div style={{ fontSize: '0.72rem', color: 'var(--accent-amber)', fontFamily: 'monospace' }}>
                      {step.name}[{step.input}]
                    </div>
                  )}
                  {step.type === 'observation' && (
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{step.text}</div>
                  )}
                  {step.type === 'lazy' && (
                    <div style={{ fontSize: '0.72rem', color: 'var(--accent-purple)' }}>
                      Re-extracted {step.new_triples} triples — {step.reason}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
