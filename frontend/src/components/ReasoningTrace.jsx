import { useRef, useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, Brain, Wrench, Eye, Zap } from 'lucide-react';

const STEP_CONFIG = {
  thought: { icon: Brain, label: '💭 Thought', className: 'thought' },
  action: { icon: Wrench, label: '🔧 Action', className: 'action' },
  observation: { icon: Eye, label: '👁 Observation', className: 'observation' },
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
          Reasoning Trace ({steps.length} steps)
          {isStreaming && <span className="pulse" style={{ marginLeft: 8 }}>● Live</span>}
        </span>
        {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
      </div>

      {!collapsed && (
        <div className="reasoning-steps" ref={scrollRef}>
          {steps.map((step, i) => {
            const config = STEP_CONFIG[step.type] || STEP_CONFIG.thought;
            const Icon = config.icon;

            let content = '';
            if (step.type === 'thought') content = step.text;
            else if (step.type === 'action') content = `${step.name}[${step.input}]`;
            else if (step.type === 'observation') content = step.text;
            else if (step.type === 'lazy') content = `Re-extracted ${step.new_triples} triples — ${step.reason}`;

            return (
              <div key={i} className={`reason-step ${config.className}`}>
                <div className="step-icon">
                  <Icon size={11} />
                </div>
                <div className="step-content">
                  <span style={{ color: 'var(--text-muted)', marginRight: 6, fontSize: '0.7rem' }}>
                    Step {step.step}
                  </span>
                  {content}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
