import { useEffect, useRef, useState } from 'react';
import { Network } from 'lucide-react';

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

export default function GraphViewer({ subgraph }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    if (!subgraph || !subgraph.nodes || subgraph.nodes.length === 0) {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
      return;
    }

    // Dynamically import cytoscape (it's large)
    import('cytoscape').then(({ default: cytoscape }) => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }

      const elements = [];

      // Add nodes
      subgraph.nodes.forEach(node => {
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
      subgraph.edges.forEach(edge => {
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
              'border-opacity': 0.4,
              'text-valign': 'bottom',
              'text-margin-y': 6,
            },
          },
          {
            selector: 'edge',
            style: {
              'width': 1.5,
              'line-color': 'rgba(148, 163, 184, 0.25)',
              'target-arrow-color': 'rgba(148, 163, 184, 0.4)',
              'target-arrow-shape': 'triangle',
              'arrow-scale': 0.7,
              'curve-style': 'bezier',
              'label': 'data(label)',
              'font-size': '7px',
              'font-family': 'Inter, sans-serif',
              'color': 'rgba(148, 163, 184, 0.5)',
              'text-rotation': 'autorotate',
              'text-margin-y': -8,
            },
          },
          {
            selector: 'node:selected',
            style: {
              'border-width': 3,
              'border-color': '#a855f7',
              'border-opacity': 1,
            },
          },
          {
            selector: 'edge:selected',
            style: {
              'width': 2.5,
              'line-color': '#a855f7',
            },
          },
        ],
        layout: {
          name: 'cose',
          animate: true,
          animationDuration: 800,
          nodeRepulsion: 8000,
          idealEdgeLength: 100,
          gravity: 0.5,
          padding: 30,
        },
        userPanningEnabled: true,
        userZoomingEnabled: true,
        boxSelectionEnabled: false,
      });

      cy.on('tap', 'node', (evt) => {
        const node = evt.target;
        setSelectedNode({
          id: node.data('id'),
          label: node.data('label'),
          type: node.data('type'),
        });
      });

      cy.on('tap', (evt) => {
        if (evt.target === cy) setSelectedNode(null);
      });

      cyRef.current = cy;
    });

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [subgraph]);

  const hasData = subgraph && subgraph.nodes && subgraph.nodes.length > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="graph-container" ref={containerRef}>
        {!hasData && (
          <div className="graph-empty">
            <Network size={28} />
            <span>Ask a question to see the reasoning subgraph</span>
          </div>
        )}
      </div>

      {hasData && (
        <div style={{ padding: '8px 12px', display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {Object.entries(NODE_COLORS).slice(0, 7).map(([type, color]) => (
            <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.65rem', color: 'var(--text-muted)' }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
              {type}
            </div>
          ))}
        </div>
      )}

      {selectedNode && (
        <div style={{
          padding: '8px 12px',
          borderTop: '1px solid var(--border-subtle)',
          fontSize: '0.75rem',
          color: 'var(--text-secondary)',
        }}>
          <strong style={{ color: NODE_COLORS[selectedNode.type] || '#fff' }}>
            {selectedNode.label}
          </strong>
          <span style={{ marginLeft: 6, color: 'var(--text-muted)' }}>({selectedNode.type})</span>
        </div>
      )}
    </div>
  );
}
