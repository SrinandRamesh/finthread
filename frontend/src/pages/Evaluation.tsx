import { useState } from 'react';
import { motion } from 'framer-motion';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { analyze, getEvaluation } from '../api/endpoints';
import type { ModelMetrics } from '../types/contract';
import { Btn, C, F, Card, CountUp, ErrorState, Grid, Loading, Page, mono, num, pct, td, th, useLoad } from '../components/ui';

const MODEL_COLOR: Record<string, string> = { graph: C.olive, baseline: C.slate };


function Gauge({ value, label, color, delay }: { value: number; label: string; color: string; delay: number }) {
  const r = 58, circ = 2 * Math.PI * r;
  return (
    <div style={{ position: 'relative', width: 150, height: 150 }}>
      <svg width="150" height="150" viewBox="0 0 150 150" aria-hidden="true">
        <circle cx="75" cy="75" r={r} fill="none" stroke="rgba(255,255,255,.14)" strokeWidth="10" />
        <motion.circle cx="75" cy="75" r={r} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round" transform="rotate(-90 75 75)"
          strokeDasharray={circ} initial={{ strokeDashoffset: circ }} animate={{ strokeDashoffset: circ * (1 - value) }} transition={{ duration: 1.6, ease: [0.22, 1, 0.36, 1], delay }} />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ fontFamily: F.display, fontSize: 30, fontWeight: 600, color: '#E9E8F8' }}><CountUp to={value * 100} format={v => `${v.toFixed(1)}%`} duration={1.6} /></div>
        <div style={{ fontFamily: F.ui, fontSize: 11.5, color: 'rgba(255,255,255,.65)' }}>{label}</div>
      </div>
    </div>
  );
}

function ModelCard({ m }: { m: ModelMetrics }) {
  const color = MODEL_COLOR[m.model];
  const metrics: [string, number][] = [['Precision', m.precision], ['Recall', m.recall], ['F1 score', m.f1], ['Accuracy', m.accuracy]];
  return (
    <Card title={<span style={{ color }}>{m.display_name}</span>} right={<span style={{ fontFamily: F.ui, fontSize: 12, color: C.cocoa }}>{m.flagged_count} flagged</span>}>
      <Grid cols={4} gap={12}>
        {metrics.map(([label, v]) => (
          <div key={label}>
            <div style={{ fontFamily: F.ui, fontSize: 12, color: C.cocoa }}>{label}</div>
            <div style={{ fontFamily: F.display, fontSize: 30, fontWeight: 600, color }}>{pct(v)}</div>
          </div>
        ))}
      </Grid>
    </Card>
  );
}

function Matrix({ m }: { m: ModelMetrics }) {
  const { tp, fp, fn, tn } = m.confusion_matrix;
  const cell = (v: number, label: string, good: boolean) => (
    <div style={{ background: good ? '#DCF0EA' : '#FFE7DE', borderRadius: 10, padding: 16, textAlign: 'center' }}>
      <div style={{ fontFamily: F.display, fontSize: 30, fontWeight: 600, color: good ? C.olive : C.terracotta }}>{v.toLocaleString('en-IN')}</div>
      <div style={{ fontFamily: F.ui, fontSize: 12, color: C.cocoa, marginTop: 2 }}>{label}</div>
    </div>
  );
  return (
    <Card title={`Confusion matrix · ${m.display_name}`}>
      <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr 1fr', gap: 8, alignItems: 'center', fontFamily: F.ui, fontSize: 12, color: C.cocoa }}>
        <div />
        <div style={{ textAlign: 'center', fontWeight: 600 }}>Flagged</div>
        <div style={{ textAlign: 'center', fontWeight: 600 }}>Not flagged</div>
        <div style={{ fontWeight: 600 }}>Actually suspicious</div>
        {cell(tp, 'true positives', true)}
        {cell(fn, 'missed', false)}
        <div style={{ fontWeight: 600 }}>Actually normal</div>
        {cell(fp, 'false alarms', false)}
        {cell(tn, 'true negatives', true)}
      </div>
    </Card>
  );
}

export default function Evaluation() {
  const { data, error, status, loading, reload } = useLoad(getEvaluation);
  const [busy, setBusy] = useState(false);

  async function rerun() {
    setBusy(true);
    try { await analyze(); await reload(); } finally { setBusy(false); }
  }

  if (loading) return <Loading what="evaluation" />;
  if (error || !data) return <ErrorState error={error ?? 'No data'} status={status} onRetry={reload} />;

  if (!data.available) {
    return (
      <Page title="Evaluation">
        <Card><span style={{ fontFamily: F.ui, color: C.cocoa }}>{data.reason ?? 'Evaluation is not available for this dataset.'}</span></Card>
      </Page>
    );
  }

  const chart = ['precision', 'recall', 'f1'].map(k => {
    const row: Record<string, string | number> = { metric: k === 'f1' ? 'F1' : k[0].toUpperCase() + k.slice(1) };
    data.models.forEach(m => { row[m.display_name] = Number(((m as unknown as Record<string, number>)[k] * 100).toFixed(1)); });
    return row;
  });

  return (
    <Page
      title="Graph detection vs rule-based baseline"
      subtitle={`Transaction-level evaluation on ${data.total.toLocaleString('en-IN')} labelled transactions (${data.positives} suspicious, ${data.negatives.toLocaleString('en-IN')} normal) · labels: ${data.label_source ?? 'n/a'}`}
      actions={<Btn kind="ghost" onClick={rerun} disabled={busy}>{busy ? 'Re-running…' : 'Re-run analysis'}</Btn>}
    >
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', borderRadius: 24, overflow: 'hidden', border: `1px solid ${C.line}` }}>
        <div style={{ background: C.ivory, padding: 28, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ fontFamily: F.mono, fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase', color: C.cocoa }}>Headline result</div>
          <div style={{ fontFamily: F.display, fontSize: 34, fontWeight: 600, color: C.espresso, lineHeight: 1.1, marginTop: 8 }}>
            Graph detection catches <em style={{ color: C.coral }}>{data.models[0].confusion_matrix.tp}</em> of {data.positives} suspicious transactions.
          </div>
          <div style={{ fontFamily: F.ui, fontSize: 14, color: C.cocoa, marginTop: 10, lineHeight: 1.6 }}>
            The rule-based baseline catches {data.models[1].confusion_matrix.tp} and raises {data.models[1].confusion_matrix.fp} false alarms.
          </div>
        </div>
        <div style={{ background: 'linear-gradient(135deg, #4F7FD8 0%, #7DA6EA 70%, #F6B29E 140%)', padding: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-around' }}>
          <Gauge value={data.models[0].f1} label="Graph F1" color={C.coral} delay={0.2} />
          <Gauge value={data.models[1].f1} label="Rules F1" color="#B9CDF2" delay={0.4} />
          <Gauge value={data.models[0].recall} label="Graph recall" color="#D6E6FC" delay={0.6} />
        </div>
      </motion.div>

      <Grid cols={2}>{data.models.map(m => <ModelCard key={m.model} m={m} />)}</Grid>

      <Card title="Precision, recall and F1">
        <div style={{ height: 280 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chart} barGap={6}>
              <CartesianGrid stroke={C.line} vertical={false} />
              <XAxis dataKey="metric" tick={{ fontFamily: F.ui, fontSize: 12, fill: C.cocoa }} axisLine={{ stroke: C.line }} tickLine={false} />
              <YAxis domain={[0, 100]} unit="%" tick={{ fontFamily: F.ui, fontSize: 12, fill: C.cocoa }} axisLine={false} tickLine={false} />
              <Tooltip formatter={(v) => `${v}%`} contentStyle={{ fontFamily: F.ui, borderRadius: 10, border: `1px solid ${C.line}` }} />
              <Legend wrapperStyle={{ fontFamily: F.ui, fontSize: 12 }} />
              {data.models.map(m => <Bar key={m.model} dataKey={m.display_name} fill={MODEL_COLOR[m.model]} radius={[6, 6, 0, 0]} />)}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Grid cols={2}>{data.models.map(m => <Matrix key={m.model} m={m} />)}</Grid>

      <Card title="Recall by laundering typology" pad={0}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead><tr><th style={th}>Typology</th><th style={{ ...th, textAlign: 'right' }}>Suspicious transactions</th><th style={{ ...th, textAlign: 'right' }}>Graph recall</th><th style={{ ...th, textAlign: 'right' }}>Baseline recall</th></tr></thead>
          <tbody>
            {data.per_typology.map(t => (
              <tr key={t.typology}>
                <td style={td}>{t.label}</td>
                <td style={num}>{t.positives}</td>
                <td style={{ ...num, color: C.olive, fontWeight: 600 }}>{pct(t.graph_recall)}</td>
                <td style={{ ...num, color: C.slate, fontWeight: 600 }}>{pct(t.baseline_recall)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Grid cols={2}>
        <Card title="Notes">
          <ul style={{ fontFamily: F.ui, fontSize: 13, color: C.cocoa, lineHeight: 1.7, paddingLeft: 18, margin: 0 }}>
            {data.notes.map((n, i) => <li key={i}>{n}</li>)}
          </ul>
        </Card>
        <Card title="Thresholds used" pad={0}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <tbody>
              {Object.entries(data.thresholds).map(([k, v]) => (
                <tr key={k}><td style={mono}>{k}</td><td style={num}>{v.toLocaleString('en-IN')}</td></tr>
              ))}
            </tbody>
          </table>
        </Card>
      </Grid>
    </Page>
  );
}
