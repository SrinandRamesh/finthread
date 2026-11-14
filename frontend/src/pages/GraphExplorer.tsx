import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { getGraph, getPatterns } from '../api/endpoints';
import GraphCanvas from '../components/graph/GraphCanvas';
import type { GraphNode, GraphEdge, PatternType } from '../types/contract';
import { formatINR, formatDate } from '../lib/format';

const PATTERN_CHIPS: { type: PatternType; label: string }[] = [
  { type: 'FAN_IN', label: 'Fan-in' },
  { type: 'FAN_OUT', label: 'Fan-out' },
  { type: 'CYCLE', label: 'Cycle' },
  { type: 'PASS_THROUGH', label: 'Pass-through' },
];

export default function GraphExplorer() {
  const { data: graph, loading, error } = useApi(() => getGraph('scope=suspicious'));
  const [activePattern, setActivePattern] = useState<PatternType | null>(null);
  const [highlightIds, setHighlightIds] = useState<Set<string>>(new Set());
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);

  async function handlePatternChip(type: PatternType) {
    if (activePattern === type) {
      setActivePattern(null);
      setHighlightIds(new Set());
      return;
    }
    setActivePattern(type);
    try {
      const result = await getPatterns(`type=${type}`);
      const ids = new Set<string>();
      result.items.forEach(p => {
        p.accounts.forEach(a => ids.add(a));
        p.transaction_ids.forEach(t => ids.add(t));
      });
      setHighlightIds(ids);
    } catch (e) {
      setHighlightIds(new Set());
    }
  }

  if (loading) return <div style={{ padding: 32, fontFamily: 'Manrope, sans-serif', color: '#6B5A48' }}>Loading graph…</div>;
  if (error) return (
    <div style={{ padding: 32 }}>
      <div style={{ background: '#FFFDF8', border: '1px solid #E7DAC3', borderRadius: 14, padding: 32, maxWidth: 480 }}>
        <h2 style={{ fontFamily: 'Fraunces, serif', fontSize: 28, color: '#2A1F16', fontWeight: 600 }}>No graph data yet</h2>
        <p style={{ fontFamily: 'Manrope, sans-serif', color: '#6B5A48', marginTop: 8 }}>Load a dataset first from the Upload page.</p>
        <a href="/upload" style={{ display: 'inline-block', marginTop: 16, background: '#B8862F', color: '#FFFDF8', borderRadius: 10, padding: '10px 24px', fontFamily: 'Manrope, sans-serif', fontWeight: 600, fontSize: 14, textDecoration: 'none' }}>Go to Upload →</a>
      </div>
    </div>
  );

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 56px)', overflow: 'hidden' }}>

      {/* Left controls */}
      <div style={{ width: 220, background: '#FFFDF8', borderRight: '1px solid #E7DAC3', padding: 20, overflowY: 'auto', flexShrink: 0 }}>
        <div style={{ fontFamily: 'Manrope, sans-serif', fontWeight: 600, fontSize: 13, color: '#2A1F16', marginBottom: 12 }}>Pattern Highlights</div>
        {PATTERN_CHIPS.map(chip => (
          <button key={chip.type} onClick={() => handlePatternChip(chip.type)} style={{
            display: 'block', width: '100%', marginBottom: 8, padding: '8px 12px',
            background: activePattern === chip.type ? '#F3E2BC' : '#FBF6EC',
            border: activePattern === chip.type ? '1px solid #B8862F' : '1px solid #E7DAC3',
            borderRadius: 10, fontFamily: 'Manrope, sans-serif', fontSize: 13,
            color: activePattern === chip.type ? '#B8862F' : '#6B5A48',
            fontWeight: activePattern === chip.type ? 600 : 400,
            cursor: 'pointer', textAlign: 'left',
          }}>
            {chip.label}
          </button>
        ))}

        <div style={{ marginTop: 24, fontFamily: 'Manrope, sans-serif', fontSize: 12, color: '#A79B8B' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#F8E1D9', border: '1px solid #C0502F' }} />
            High risk
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#FBEBD0', border: '1px solid #D9962B' }} />
            Medium risk
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#E4EDDD', border: '1px solid #5E7F4F' }} />
            Low risk
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#F1ECE4', border: '1px solid #A79B8B' }} />
            None
          </div>
        </div>

        <div style={{ marginTop: 16, fontFamily: 'Manrope, sans-serif', fontSize: 12, color: '#A79B8B' }}>
          <b style={{ color: '#2A1F16' }}>Gold border</b> = suspicious<br />
          <b style={{ color: '#C0502F' }}>Red edge</b> = suspicious tx<br />
          Arrow = money direction
        </div>

        <div style={{ marginTop: 16, fontFamily: 'IBM Plex Mono, monospace', fontSize: 11, color: '#A79B8B' }}>
          {graph!.meta.node_count} nodes · {graph!.meta.edge_count} edges
          {graph!.meta.truncated && <div style={{ color: '#D9962B', marginTop: 4 }}>⚠ Graph truncated</div>}
        </div>
      </div>

      {/* Graph canvas */}
      <div style={{ flex: 1, position: 'relative' }}>
        <GraphCanvas
          graph={graph!}
          highlightIds={highlightIds}
          onNodeClick={n => { setSelectedNode(n); setSelectedEdge(null); }}
          onEdgeClick={e => { setSelectedEdge(e); setSelectedNode(null); }}
        />
      </div>

      {/* Right panel */}
      {(selectedNode || selectedEdge) && (
        <div style={{ width: 280, background: '#FFFDF8', borderLeft: '1px solid #E7DAC3', padding: 20, overflowY: 'auto', flexShrink: 0 }}>
          <button onClick={() => { setSelectedNode(null); setSelectedEdge(null); }} style={{ float: 'right', background: 'none', border: 'none', cursor: 'pointer', color: '#A79B8B', fontSize: 18 }}>×</button>

          {selectedNode && (
            <div>
              <div style={{ fontFamily: 'Fraunces, serif', fontSize: 20, fontWeight: 600, color: '#2A1F16' }}>{selectedNode.label}</div>
              <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {[
                  { label: 'Risk Level', value: selectedNode.risk_level.toUpperCase() },
                  { label: 'Risk Score', value: selectedNode.risk_score?.toFixed(1) ?? 'N/A' },
                  { label: 'Total In', value: formatINR(selectedNode.total_in) },
                  { label: 'Total Out', value: formatINR(selectedNode.total_out) },
                  { label: 'In Degree', value: selectedNode.in_degree },
                  { label: 'Out Degree', value: selectedNode.out_degree },
                ].map(r => (
                  <div key={r.label} style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'Manrope, sans-serif', fontSize: 13 }}>
                    <span style={{ color: '#6B5A48' }}>{r.label}</span>
                    <span style={{ color: '#2A1F16', fontWeight: 500 }}>{r.value}</span>
                  </div>
                ))}
              </div>
              {selectedNode.patterns.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <div style={{ fontFamily: 'Manrope, sans-serif', fontSize: 12, color: '#6B5A48', marginBottom: 6 }}>Patterns</div>
                  {selectedNode.patterns.map(p => (
                    <span key={p} style={{ display: 'inline-block', marginRight: 4, marginBottom: 4, background: '#F3E2BC', color: '#B8862F', borderRadius: 6, padding: '2px 8px', fontSize: 11, fontFamily: 'Manrope, sans-serif', fontWeight: 600 }}>{p}</span>
                  ))}
                </div>
              )}
              <a href={`/accounts/${selectedNode.id}`} style={{ display: 'block', marginTop: 16, textAlign: 'center', background: '#B8862F', color: '#FFFDF8', borderRadius: 10, padding: '10px', fontFamily: 'Manrope, sans-serif', fontWeight: 600, fontSize: 13, textDecoration: 'none' }}>
                Open account →
              </a>
            </div>
          )}

          {selectedEdge && (
            <div>
              <div style={{ fontFamily: 'Fraunces, serif', fontSize: 18, fontWeight: 600, color: '#2A1F16' }}>Transaction</div>
              <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {[
                  { label: 'ID', value: selectedEdge.id },
                  { label: 'From', value: selectedEdge.source },
                  { label: 'To', value: selectedEdge.target },
                  { label: 'Amount', value: formatINR(selectedEdge.amount) },
                  { label: 'Time', value: formatDate(selectedEdge.timestamp) },
                  { label: 'Channel', value: selectedEdge.channel ?? 'N/A' },
                ].map(r => (
                  <div key={r.label} style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'Manrope, sans-serif', fontSize: 13 }}>
                    <span style={{ color: '#6B5A48' }}>{r.label}</span>
                    <span style={{ color: '#2A1F16', fontWeight: 500, fontFamily: 'IBM Plex Mono, monospace', fontSize: 12 }}>{r.value}</span>
                  </div>
                ))}
              </div>
              {selectedEdge.cluster_id && (
                <a href={`/clusters/${selectedEdge.cluster_id}`} style={{ display: 'block', marginTop: 16, textAlign: 'center', background: '#B8862F', color: '#FFFDF8', borderRadius: 10, padding: '10px', fontFamily: 'Manrope, sans-serif', fontWeight: 600, fontSize: 13, textDecoration: 'none' }}>
                  View cluster →
                </a>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}