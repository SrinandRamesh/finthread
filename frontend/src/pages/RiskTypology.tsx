import { Link } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { getClusters, getConfig } from '../api/endpoints';
import { TYPOLOGY_LABELS, type Typology } from '../types/contract';
import { C, F, Card, ErrorState, Grid, Loading, Page, mono, num, td, th, useLoad } from '../components/ui';

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
      <Grid cols={3}>
        {(Object.keys(TYPOLOGY_LABELS) as Typology[]).map(t => (
          <Link key={t} to={`/clusters?typology=${t}`} style={{ textDecoration: 'none' }}>
            <Card style={{ height: '100%' }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                <span style={{ fontFamily: F.ui, fontWeight: 700, color: C.espresso, fontSize: 15, flex: 1 }}>{TYPOLOGY_LABELS[t]}</span>
                <span style={{ fontFamily: F.display, fontSize: 28, color: C.gold, fontWeight: 600 }}>{counts[t] ?? 0}</span>
              </div>
              <p style={{ fontFamily: F.ui, fontSize: 13, color: C.cocoa, lineHeight: 1.55, marginBottom: 0 }}>{DEFINITIONS[t]}</p>
            </Card>
          </Link>
        ))}
      </Grid>

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
