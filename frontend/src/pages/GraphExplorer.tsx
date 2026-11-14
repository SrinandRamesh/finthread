import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
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

  if (loading) return <div style={{ padding: 32, fontFamily: 'Manrope, sans-serif', color: '#585F7E' }}>Loading graph…</div>;
  if (error) return (
    <div style={{ padding: 32 }}>
      <div style={{ background: '#F8F8FD', border: '1px solid #D5D4EC', borderRadius: 14, padding: 32, maxWidth: 480 }}>
        <h2 style={{ fontFamily: 'Fraunces, serif', fontSize: 28, color: '#1C2541', fontWeight: 600 }}>No graph data yet</h2>
        <p style={{ fontFamily: 'Manrope, sans-serif', color: '#585F7E', marginTop: 8 }}>Load a dataset first from the Upload page.</p>
        <a href="/upload" style={{ display: 'inline-block', marginTop: 16, background: '#4677D2', color: '#F8F8FD', borderRadius: 10, padding: '10px 24px', fontFamily: 'Manrope, sans-serif', fontWeight: 600, fontSize: 14, textDecoration: 'none' }}>Go to Upload →</a>
      </div>
    </div>
  );

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 60px)', overflow: 'hidden' }}>

      {/* Left controls */}
      <div style={{ width: 220, background: '#F8F8FD', borderRight: '1px solid #D5D4EC', padding: 20, overflowY: 'auto', flexShrink: 0 }}>
        <div style={{ fontFamily: 'Manrope, sans-serif', fontWeight: 600, fontSize: 13, color: '#1C2541', marginBottom: 12 }}>Pattern Highlights</div>
        {PATTERN_CHIPS.map((chip, i) => {
          const on = activePattern === chip.type;
          return (
            <motion.button key={chip.type} onClick={() => handlePatternChip(chip.type)} whileHover={{ x: 3 }} whileTap={{ scale: 0.97 }}
              initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4, delay: 0.05 * i }}
              style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: 10, width: '100%', marginBottom: 8, padding: '10px 12px', background: 'transparent', border: `1px solid ${on ? '#4677D2' : '#D5D4EC'}`, borderRadius: 12, fontFamily: 'Manrope, sans-serif', fontSize: 13, color: on ? '#E9E8F8' : '#585F7E', fontWeight: on ? 700 : 500, cursor: 'pointer', textAlign: 'left', overflow: 'hidden' }}>
              {on && <motion.span layoutId="chipFill" transition={{ type: 'spring', stiffness: 380, damping: 32 }} style={{ position: 'absolute', inset: 0, background: '#4677D2' }} />}
              <span style={{ position: 'relative', width: 8, height: 8, borderRadius: 4, background: on ? '#FF9475' : '#C8CAE4' }} />
              <span style={{ position: 'relative' }}>{chip.label}</span>
            </motion.button>
          );
        })}
        <AnimatePresence>
          {activePattern && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} style={{ fontFamily: 'Manrope, sans-serif', fontSize: 12, color: '#4677D2', background: '#DCE7FB', borderRadius: 10, padding: '8px 10px', overflow: 'hidden' }}>
              Highlighting {Math.round(highlightIds.size / 2)}+ accounts and transfers
            </motion.div>
          )}
        </AnimatePresence>

        <div style={{ marginTop: 24, fontFamily: 'Manrope, sans-serif', fontSize: 12, color: '#9EA2BC' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#FFE7DE', border: '1px solid #EC6C4E' }} />
            High risk
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#FCEED6', border: '1px solid #E39B32' }} />
            Medium risk
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#DCF0EA', border: '1px solid #3B9A84' }} />
            Low risk
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ECEBF6', border: '1px solid #9EA2BC' }} />
            None
          </div>
        </div>

        <div style={{ marginTop: 16, fontFamily: 'Manrope, sans-serif', fontSize: 12, color: '#9EA2BC' }}>
          <b style={{ color: '#4677D2' }}>Teal border</b> = suspicious<br />
          <b style={{ color: '#EC6C4E' }}>Coral edge</b> = suspicious transfer<br />
          Arrow = money direction
        </div>

        <div style={{ marginTop: 16, fontFamily: 'IBM Plex Mono, monospace', fontSize: 11, color: '#9EA2BC' }}>
          {graph!.meta.node_count} nodes · {graph!.meta.edge_count} edges
          {graph!.meta.truncated && <div style={{ color: '#E39B32', marginTop: 4 }}>⚠ Graph truncated</div>}
        </div>
      </div>

      {/* Graph canvas */}
      <div style={{ flex: 1, position: 'relative', backgroundColor: '#F3F2FB', backgroundImage: 'radial-gradient(#D5D4EC 1px, transparent 1px)', backgroundSize: '22px 22px' }}>
        <GraphCanvas
          graph={graph!}
          highlightIds={highlightIds}
          onNodeClick={n => { setSelectedNode(n); setSelectedEdge(null); }}
          onEdgeClick={e => { setSelectedEdge(e); setSelectedNode(null); }}
        />
      </div>

      {/* Right panel */}
      {(selectedNode || selectedEdge) && (
        <div style={{ width: 280, background: '#F8F8FD', borderLeft: '1px solid #D5D4EC', padding: 20, overflowY: 'auto', flexShrink: 0 }}>
          <button onClick={() => { setSelectedNode(null); setSelectedEdge(null); }} style={{ float: 'right', background: 'none', border: 'none', cursor: 'pointer', color: '#9EA2BC', fontSize: 18 }}>×</button>

          {selectedNode && (
            <div>
              <div style={{ fontFamily: 'Fraunces, serif', fontSize: 20, fontWeight: 600, color: '#1C2541' }}>{selectedNode.label}</div>
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
                    <span style={{ color: '#585F7E' }}>{r.label}</span>
                    <span style={{ color: '#1C2541', fontWeight: 500 }}>{r.value}</span>
                  </div>
                ))}
              </div>
              {selectedNode.patterns.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <div style={{ fontFamily: 'Manrope, sans-serif', fontSize: 12, color: '#585F7E', marginBottom: 6 }}>Patterns</div>
                  {selectedNode.patterns.map(p => (
                    <span key={p} style={{ display: 'inline-block', marginRight: 4, marginBottom: 4, background: '#DCE7FB', color: '#4677D2', borderRadius: 6, padding: '2px 8px', fontSize: 11, fontFamily: 'Manrope, sans-serif', fontWeight: 600 }}>{p}</span>
                  ))}
                </div>
              )}
              <a href={`/accounts/${selectedNode.id}`} style={{ display: 'block', marginTop: 16, textAlign: 'center', background: '#4677D2', color: '#F8F8FD', borderRadius: 10, padding: '10px', fontFamily: 'Manrope, sans-serif', fontWeight: 600, fontSize: 13, textDecoration: 'none' }}>
                Open account →
              </a>
            </div>
          )}

          {selectedEdge && (
            <div>
              <div style={{ fontFamily: 'Fraunces, serif', fontSize: 18, fontWeight: 600, color: '#1C2541' }}>Transaction</div>
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
                    <span style={{ color: '#585F7E' }}>{r.label}</span>
                    <span style={{ color: '#1C2541', fontWeight: 500, fontFamily: 'IBM Plex Mono, monospace', fontSize: 12 }}>{r.value}</span>
                  </div>
                ))}
              </div>
              {selectedEdge.cluster_id && (
                <a href={`/clusters/${selectedEdge.cluster_id}`} style={{ display: 'block', marginTop: 16, textAlign: 'center', background: '#4677D2', color: '#F8F8FD', borderRadius: 10, padding: '10px', fontFamily: 'Manrope, sans-serif', fontWeight: 600, fontSize: 13, textDecoration: 'none' }}>
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