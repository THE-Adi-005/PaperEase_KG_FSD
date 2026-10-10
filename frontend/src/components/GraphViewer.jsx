import { useEffect, useRef, useState } from 'react';
import { Network, Sparkles, Layers, Info, HelpCircle } from 'lucide-react';
import { getPaperGraph } from '../utils/api';

// Node type → color mapping
const NODE_COLORS = {
  Paper: '#a855f7',
  Method: '#3b82f6',
  Concept: '#8b5cf6',
  Dataset: '#22c55e',
  Metric: '#f59e0b',
  Author: '#64748b',
  Section: '#475569',
  Figure: '#14b8a6',
  Table: '#06b6d4',
  Citation: '#94a3b8',
  Unknown: '#64748b',
};

export default function GraphViewer({ subgraph, selectedPaperIds = [], useNaive = false }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [paperGraph, setPaperGraph] = useState(null);
  const [loadingPaperGraph, setLoadingPaperGraph] = useState(false);

  // If no reasoning subgraph is active, fetch the selected paper's full knowledge graph
  useEffect(() => {
    if (subgraph && subgraph.nodes && subgraph.nodes.length > 0) {
      setPaperGraph(null);
      return;
    }

    if (selectedPaperIds.length > 0) {
      setLoadingPaperGraph(true);
      getPaperGraph(selectedPaperIds[0])
        .then(data => {
          setPaperGraph(data);
        })
        .catch(() => setPaperGraph(null))
        .finally(() => setLoadingPaperGraph(false));
    } else {
      setPaperGraph(null);
    }
  }, [subgraph, selectedPaperIds]);

  const activeGraph = (subgraph && subgraph.nodes && subgraph.nodes.length > 0)
    ? subgraph
    : paperGraph;

  const isReasoningTrace = Boolean(subgraph && subgraph.nodes && subgraph.nodes.length > 0);

  useEffect(() => {
    if (!activeGraph || !activeGraph.nodes || activeGraph.nodes.length === 0) {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
      return;
    }

    // Dynamically import cytoscape
    import('cytoscape').then(({ default: cytoscape }) => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }

      const elements = [];

      // Add nodes
      activeGraph.nodes.forEach(node => {
        elements.push({
          data: {
            id: node.id,
            label: node.label || node.id,
            type: node.type,
            color: NODE_COLORS[node.type] || NODE_COLORS.Unknown,
            ...node.properties,
          },
        });
      });

      // Add edges
      activeGraph.edges.forEach(edge => {
        elements.push({
          data: {
            id: edge.id || `${edge.source}-${edge.target}`,
            source: edge.source,
            target: edge.target,
            label: edge.type,
            ...edge.properties,
          },
        });
      });

      const cy = cytoscape({
        container: containerRef.current,
        elements,
        style: [
          {
            selector: 'node',
            style: {
              'background-color': 'data(color)',
              'label': 'data(label)',
              'font-size': '9px',
              'font-family': 'Inter, sans-serif',
              'color': '#e2e8f0',
              'text-outline-color': '#0a0e1a',
              'text-outline-width': 2,
              'width': 28,
              'height': 28,
              'border-width': 2,
              'border-color': 'data(color)',
              'border-opacity': 0.5,
              'text-valign': 'bottom',
              'text-margin-y': 6,
            },
          },
          {
            selector: 'edge',
            style: {
              'width': 1.5,
              'line-color': 'rgba(148, 163, 184, 0.3)',
              'target-arrow-color': 'rgba(148, 163, 184, 0.5)',
              'target-arrow-shape': 'triangle',
              'arrow-scale': 0.7,
              'curve-style': 'bezier',
              'label': 'data(label)',
              'font-size': '7px',
              'font-family': 'JetBrains Mono, monospace',
              'color': 'rgba(148, 163, 184, 0.7)',
              'text-rotation': 'autorotate',
              'text-background-opacity': 0.8,
              'text-background-color': '#0a0e1a',
              'text-background-padding': '2px',
            },
          },
          {
            selector: 'node:selected',
            style: {
              'border-width': 3,
              'border-color': '#ffffff',
              'border-opacity': 1,
            },
          },
          {
            selector: 'edge[label = "SAME_AS"]',
            style: {
              'line-color': '#a855f7',
              'target-arrow-color': '#a855f7',
              'line-style': 'dashed',
              'width': 2,
            },
          },
        ],
        layout: {
          name: 'cose',
          animate: false,
          padding: 30,
          nodeRepulsion: 4500,
          idealEdgeLength: 60,
        },
      });

      cy.on('tap', 'node', (evt) => {
        const node = evt.target;
        setSelectedNode(node.data());
      });

      cy.on('tap', (evt) => {
        if (evt.target === cy) {
          setSelectedNode(null);
        }
      });

      cyRef.current = cy;
    });

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [activeGraph]);

  const hasData = activeGraph && activeGraph.nodes && activeGraph.nodes.length > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Mode / Status Header */}
      <div style={{
        padding: '8px 14px',
        background: 'var(--bg-panel)',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '0.75rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {isReasoningTrace ? (
            <span style={{ color: 'var(--accent-purple)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
              <Sparkles size={12} /> Active Reasoning Traversal Subgraph
            </span>
          ) : hasData ? (
            <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 4 }}>
              <Layers size={12} /> Paper Knowledge Graph ({activeGraph.nodes.length} nodes, {activeGraph.edges.length} edges)
            </span>
          ) : (
            <span style={{ color: 'var(--text-muted)' }}>Knowledge Graph</span>
          )}
        </div>

        {useNaive && (
          <span style={{
            fontSize: '0.65rem',
            background: 'rgba(59, 130, 246, 0.15)',
            color: 'var(--accent-blue)',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            padding: '2px 8px',
            borderRadius: 10,
            fontWeight: 600,
          }}>
            Naive Baseline Mode
          </span>
        )}
      </div>

      {/* Main Graph Canvas */}
      <div className="graph-container" ref={containerRef} style={{ flex: 1, position: 'relative' }}>
        {!hasData && (
          <div className="graph-empty">
            {loadingPaperGraph ? (
              <span>Loading Knowledge Graph...</span>
            ) : useNaive ? (
              <div style={{ textAlign: 'center', padding: 24, maxWidth: 300 }}>
                <div style={{ marginBottom: 8, fontSize: '1.4rem' }}>📄</div>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>Naive RAG Baseline</div>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: 0, lineHeight: 1.4 }}>
                  Naive RAG retrieves flat document chunks without exploring graph relationships. Switch to <strong>🧠 KG-Grounded</strong> mode to watch the agent traverse entities in real time.
                </p>
              </div>
            ) : (
              <>
                <Network size={32} style={{ opacity: 0.4 }} />
                <span>Select a paper or ask a question to explore its Knowledge Graph</span>
              </>
            )}
          </div>
        )}
      </div>

      {/* Legend */}
      {hasData && (
        <div style={{
          padding: '8px 12px',
          background: 'rgba(11, 15, 25, 0.8)',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          flexWrap: 'wrap',
          gap: 10,
        }}>
          {Object.entries(NODE_COLORS).slice(0, 7).map(([type, color]) => (
            <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.65rem', color: 'var(--text-muted)' }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
              {type}
            </div>
          ))}
        </div>
      )}

      {/* Node Inspector on Click */}
      {selectedNode && (
        <div style={{
          padding: '10px 14px',
          borderTop: '1px solid var(--border-subtle)',
          background: 'var(--bg-panel)',
          fontSize: '0.75rem',
          color: 'var(--text-secondary)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div>
            <strong style={{ color: NODE_COLORS[selectedNode.type] || '#fff', fontSize: '0.8rem' }}>
              {selectedNode.label}
            </strong>
            <span style={{ marginLeft: 6, color: 'var(--text-muted)' }}>[{selectedNode.type}]</span>
          </div>
          {selectedNode.score && (
            <span style={{ fontSize: '0.68rem', color: 'var(--accent-purple)' }}>
              Relevance: {Number(selectedNode.score).toFixed(2)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
