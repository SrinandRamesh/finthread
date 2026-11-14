import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import PatternMorph from '../components/motion/PatternMorph';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { getClusters, getConfig } from '../api/endpoints';
import { TYPOLOGY_LABELS, type Typology } from '../types/contract';
import { C, F, Card, ErrorState, Grid, Loading, Page, mono, num, td, th, useLoad } from '../components/ui';

const TYPS: Typology[] = ['FAN_IN', 'FAN_OUT', 'CYCLE', 'PASS_THROUGH', 'SCATTER_GATHER'];
const SHORT: Record<Typology, string> = { FAN_IN: 'Fan-in', FAN_OUT: 'Fan-out', CYCLE: 'Cycle', PASS_THROUGH: 'Pass-through', SCATTER_GATHER: 'Scatter-gather' };
const DEFINITIONS: Record<Typology, string> = {
  FAN_IN: 'Many different accounts send money to one account within a short window, typical of a collector gathering funds from mules.',
  FAN_OUT: 'One account splits money to many different accounts within a short window, typical of dispersal to mules (smurfing).',
  CYCLE: 'Money leaves an account and returns to it through other accounts in time order, typical of round-tripping to fake legitimate activity.',
  PASS_THROUGH: 'Each account forwards most of what it received within hours, creating a fast mule chain that hides the source.',
  SCATTER_GATHER: 'Funds are scattered to mules and then gathered back into one collector, combining fan-out and fan-in.',
};

const SCORING: [string, string, string][] = [
  ['Pattern severity', '35', 'Cycle 35 · Pass-through 30 · Scatter-gather 30 · Fan-out 20 · Fan-in 20'],
  ['Multiple typologies', '20', '+10 for each extra distinct typology in the cluster'],
  ['Velocity', '20', 'Median hop ≤ 6 h: 20 · ≤ 24 h: 12 · ≤ 72 h: 5'],
  ['Structuring', '15', 'Share of amounts just below the reporting threshold: ≥ 50%: 15 · ≥ 20%: 8'],
  ['Flow-through', '10', 'Intermediaries forward ≥ 90% of inflow: 10 · ≥ 75%: 5'],
];

export default function RiskTypology() {
  const clusters = useLoad(() => getClusters());
  const config = useLoad(getConfig);
  const [active, setActive] = useState(0);

  if (clusters.loading || config.loading) return <Loading what="risk model" />;
  if (clusters.error) return <ErrorState error={clusters.error} status={clusters.status} onRetry={clusters.reload} />;

  const items = clusters.data?.items ?? [];
  const counts: Record<string, number> = {};
  items.forEach(c => c.typologies.forEach(t => { counts[t] = (counts[t] ?? 0) + 1; }));
  const bins = Array.from({ length: 10 }, (_, i) => ({ range: `${i * 10}–${i * 10 + 9}`, start: i * 10, count: 0 }));
  items.forEach(c => { bins[Math.min(9, Math.floor(c.risk_score / 10))].count += 1; });
  const alertAt = config.data?.risk.ALERT_THRESHOLD ?? 40;
  const highAt = config.data?.risk.HIGH_RISK_THRESHOLD ?? 70;

  return (
    <Page title="Risk & typology" subtitle="How FinThread labels patterns and builds each cluster's 0–100 risk score. Every point is explainable.">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        style={{ display: 'grid', gridTemplateColumns: '1.15fr 1fr', borderRadius: 24, overflow: 'hidden', border: `1px solid ${C.line}`, background: C.ivory, minHeight: 440 }}>
        <div style={{ position: 'relative', background: 'linear-gradient(135deg, #4F7FD8 0%, #7DA6EA 70%, #F6B29E 140%)' }}>
          <PatternMorph index={active} scale={0.36} />
          <div style={{ position: 'absolute', left: 24, top: 22, fontFamily: F.mono, fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase', color: 'rgba(255,255,255,.6)' }}>Pattern library</div>
          <div style={{ position: 'absolute', left: 24, bottom: 22, right: 24 }}>
            <AnimatePresence mode="wait">
              <motion.div key={active} initial={{ opacity: 0, y: 18, filter: 'blur(10px)' }} animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }} exit={{ opacity: 0, y: -12, filter: 'blur(10px)' }} transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}>
                <div style={{ fontFamily: F.mono, fontSize: 12, color: C.coral, letterSpacing: '.08em' }}>0{active + 1} · {counts[TYPS[active]] ?? 0} clusters</div>
                <div style={{ fontFamily: F.display, fontSize: 52, fontWeight: 600, color: C.cream, lineHeight: 1 }}>{SHORT[TYPS[active]]}</div>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
        <div style={{ padding: 22, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {TYPS.map((t, i) => (
            <button key={t} onClick={() => setActive(i)} style={{ position: 'relative', textAlign: 'left', border: 'none', background: 'transparent', cursor: 'pointer', borderRadius: 14, padding: '12px 14px' }}>
              {active === i && <motion.span layoutId="typPill" transition={{ type: 'spring', stiffness: 380, damping: 32 }} style={{ position: 'absolute', inset: 0, borderRadius: 14, background: C.tealSoft }} />}
              <div style={{ position: 'relative', display: 'flex', alignItems: 'baseline', gap: 10 }}>
                <span style={{ fontFamily: F.mono, fontSize: 12, color: active === i ? C.coral : C.stone }}>0{i + 1}</span>
                <span style={{ fontFamily: F.ui, fontSize: 15, fontWeight: 700, color: C.espresso, flex: 1 }}>{TYPOLOGY_LABELS[t]}</span>
                <span style={{ fontFamily: F.display, fontSize: 20, fontWeight: 600, color: C.teal }}>{counts[t] ?? 0}</span>
              </div>
              <AnimatePresence initial={false}>
                {active === i && (
                  <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }} style={{ position: 'relative', overflow: 'hidden' }}>
                    <p style={{ fontFamily: F.ui, fontSize: 13, color: C.cocoa, lineHeight: 1.55, margin: '8px 0 6px 26px' }}>{DEFINITIONS[t]}</p>
                    <Link to={`/clusters?typology=${t}`} style={{ marginLeft: 26, fontFamily: F.ui, fontSize: 12.5, fontWeight: 700, color: C.teal, textDecoration: 'none' }}>View these clusters →</Link>
                  </motion.div>
                )}
              </AnimatePresence>
            </button>
          ))}
        </div>
      </motion.div>

      <Card title="Cluster risk score distribution" right={<span style={{ fontFamily: F.ui, fontSize: 12, color: C.cocoa }}>alert ≥ {alertAt} · high ≥ {highAt}</span>}>
        <div style={{ height: 240 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={bins}>
              <CartesianGrid stroke={C.line} vertical={false} />
              <XAxis dataKey="range" tick={{ fontFamily: F.ui, fontSize: 11, fill: C.cocoa }} axisLine={{ stroke: C.line }} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fontFamily: F.ui, fontSize: 11, fill: C.cocoa }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ fontFamily: F.ui, borderRadius: 10, border: `1px solid ${C.line}` }} />
              <Bar dataKey="count" name="Clusters" radius={[6, 6, 0, 0]}>
                {bins.map(b => <Cell key={b.start} fill={b.start >= highAt ? C.terracotta : b.start >= alertAt ? C.ochre : C.olive} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Grid cols={2}>
        <Card title="How the score is built" pad={0}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr><th style={th}>Factor</th><th style={{ ...th, textAlign: 'right' }}>Max</th><th style={th}>Rule</th></tr></thead>
            <tbody>{SCORING.map(([f, m, r]) => (
              <tr key={f}><td style={{ ...td, fontWeight: 600 }}>{f}</td><td style={num}>{m}</td><td style={{ ...td, fontSize: 12, color: C.cocoa }}>{r}</td></tr>
            ))}</tbody>
          </table>
        </Card>
        <Card title="Active thresholds" pad={0}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <tbody>
              {config.data && (['detection', 'risk', 'baseline'] as const).flatMap(group =>
                Object.entries(config.data![group]).map(([k, v]) => (
                  <tr key={k}><td style={{ ...td, fontSize: 11, color: C.stone, textTransform: 'uppercase' }}>{group}</td><td style={mono}>{k}</td><td style={num}>{v.toLocaleString('en-IN')}</td></tr>
                )))}
            </tbody>
          </table>
        </Card>
      </Grid>
    </Page>
  );
}
