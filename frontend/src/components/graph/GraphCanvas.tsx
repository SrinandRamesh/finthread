import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import fcose from 'cytoscape-fcose';
import type { GraphOut, GraphNode, GraphEdge } from '../../types/contract';

cytoscape.use(fcose);

function nodeColor(level: string) {
  if (level === 'high') return '#F8E1D9';
  if (level === 'medium') return '#FBEBD0';
  if (level === 'low') return '#E4EDDD';
  return '#F1ECE4';
}

function nodeTextColor(level: string) {
  if (level === 'high') return '#C0502F';
  if (level === 'medium') return '#D9962B';
  if (level === 'low') return '#5E7F4F';
  return '#A79B8B';
}

interface Props {
  graph: GraphOut;
  highlightIds?: Set<string>;
  onNodeClick?: (node: GraphNode) => void;
  onEdgeClick?: (edge: GraphEdge) => void;
}

export default function GraphCanvas({ graph, highlightIds, onNodeClick, onEdgeClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const nodes = graph.nodes.map(n => ({
      data: {
        id: n.id,
        label: n.label,
        risk_level: n.risk_level,
        is_suspicious: n.is_suspicious,
        total_in: n.total_in,
        total_out: n.total_out,
        raw: n,
      },
    }));

    const edges = graph.edges.map(e => ({
      data: {
        id: e.id,
        source: e.source,
        target: e.target,
        amount: e.amount,
        is_suspicious: e.is_suspicious,
        patterns: e.patterns,
        raw: e,
      },
    }));

    const cy = cytoscape({
      container: containerRef.current,
      elements: { nodes, edges },
      style: [
        {
          selector: 'node',
          style: {
            'background-color': (el: any) => nodeColor(el.data('risk_level')),
            'border-color': (el: any) => el.data('is_suspicious') ? '#B8862F' : '#E7DAC3',
            'border-width': (el: any) => el.data('is_suspicious') ? 3 : 1,
            'width': (el: any) => Math.max(24, Math.min(60, 20 + Math.log10(el.data('total_in') + el.data('total_out') + 1) * 10)),
            'height': (el: any) => Math.max(24, Math.min(60, 20 + Math.log10(el.data('total_in') + el.data('total_out') + 1) * 10)),
            'label': '',
            'color': (el: any) => nodeTextColor(el.data('risk_level')),
            'font-size': 10,
            'font-family': 'Manrope, sans-serif',
          } as any,
        },
        {
          selector: 'node:selected',
          style: {
            'border-color': '#B8862F',
            'border-width': 3,
          },
        },
        {
          selector: 'node.highlight',
          style: {
            'border-color': '#B8862F',
            'border-width': 3,
            'label': 'data(label)',
            'opacity': 1,
          },
        },
        {
          selector: 'node.faded',
          style: { 'opacity': 0.15 },
        },
        {
          selector: 'edge',
          style: {
            'width': (el: any) => Math.max(1, Math.min(6, Math.log10(el.data('amount') + 1))),
            'line-color': (el: any) => el.data('is_suspicious') ? '#C0502F' : '#D8CBB5',
            'target-arrow-color': (el: any) => el.data('is_suspicious') ? '#C0502F' : '#D8CBB5',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'opacity': 0.8,
          } as any,
        },
        {
          selector: 'edge.highlight',
          style: {
            'line-color': '#B8862F',
            'target-arrow-color': '#B8862F',
            'opacity': 1,
          },
        },
        {
          selector: 'edge.faded',
          style: { 'opacity': 0.1 },
        },
      ],
      layout: { name: 'fcose', animate: true } as any,
    });

    cy.on('tap', 'node', evt => {
      onNodeClick?.(evt.target.data('raw'));
    });

    cy.on('tap', 'edge', evt => {
      onEdgeClick?.(evt.target.data('raw'));
    });

    cyRef.current = cy;
    return () => { cy.destroy(); };
  }, [graph]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    if (!highlightIds || highlightIds.size === 0) {
      cy.elements().removeClass('highlight faded');
      return;
    }
    cy.nodes().forEach(n => {
      if (highlightIds.has(n.id())) {
        n.addClass('highlight'); n.removeClass('faded');
      } else {
        n.addClass('faded'); n.removeClass('highlight');
      }
    });
    cy.edges().forEach(e => {
      if (highlightIds.has(e.id())) {
        e.addClass('highlight'); e.removeClass('faded');
      } else {
        e.addClass('faded'); e.removeClass('highlight');
      }
    });
  }, [highlightIds]);

  return <div ref={containerRef} style={{ width: '100%', height: '100%', background: '#FBF6EC', borderRadius: 14 }} />;
}