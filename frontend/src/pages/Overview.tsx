import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { getOverview } from '../api/endpoints';
import { formatDate, formatINR } from '../lib/format';
import { TYPOLOGY_LABELS } from '../types/contract';
import { C, F, Card, CountUp, ErrorState, Grid, Loading, RiskBadge, TypChip, useLoad } from '../components/ui';

const ease = [0.22, 1, 0.36, 1] as const;
const short = (v: number) => (v >= 1e7 ? `₹${(v / 1e7).toFixed(1)} Cr` : v >= 1e5 ? `₹${(v / 1e5).toFixed(1)} L` : formatINR(v));

export default function Overview() {
  const { data, loading, error, status, reload } = useLoad(getOverview);
  const nav = useNavigate();

  if (loading) return <Loading what="overview" />;
  if (error || !data) return <ErrorState error={error ?? 'No data'} status={status} onRetry={reload} />;

  const s = data.stats;
  const hm = data.headline_metrics;
  const tiles: { label: string; value: number; fmt?: (v: number) => string; accent?: string }[] = [
    { label: 'Transactions analysed', value: s.total_transactions },
    { label: 'Accounts', value: s.total_accounts },
    { label: 'Money analysed', value: s.total_amount, fmt: short },
    { label: 'Flagged transactions', value: s.flagged_transactions, accent: C.coral },
    { label: 'Suspicious clusters', value: s.clusters },
    { label: 'High-risk alerts', value: s.high_risk_alerts, accent: C.coral },
  ];
  const maxTyp = Math.max(1, ...data.typology_counts.map(t => t.count));

  return (
    <div style={{ padding: 32, maxWidth: 1280 }}>
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease }}>
        <div style={{ fontFamily: F.mono, fontSize: 12, letterSpacing: '.08em', textTransform: 'uppercase', color: C.cocoa }}>{data.dataset.name} · run {formatDate(data.run.finished_at)}</div>
        <h1 style={{ fontFamily: F.display, fontSize: 44, fontWeight: 600, color: C.espresso, margin: '8px 0 0', lineHeight: 1.05 }}>
          <CountUp to={s.alerts} /> rings need <em style={{ color: C.teal }}>your attention.</em>
        </h1>
      </motion.div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, minmax(0, 1fr))', gap: 14, marginTop: 28 }}>
        {tiles.map((t, i) => (
          <motion.div key={t.label} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease, delay: 0.06 * i }} whileHover={{ y: -4 }}
            style={{ background: C.ivory, border: `1px solid ${C.line}`, borderRadius: 16, padding: '18px 18px 16px', position: 'relative', overflow: 'hidden' }}>
            {t.accent && <span style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: t.accent }} />}
            <div style={{ fontFamily: F.ui, fontSize: 12, color: C.cocoa, fontWeight: 500 }}>{t.label}</div>
            <div style={{ fontFamily: F.display, fontSize: 30, fontWeight: 600, color: t.accent ?? C.espresso, marginTop: 8 }}><CountUp to={t.value} format={t.fmt} /></div>
          </motion.div>
        ))}
      </div>

      {hm && (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease, delay: 0.3 }}
          style={{ marginTop: 20, background: 'linear-gradient(120deg, #4677D2 0%, #6F9BE6 65%, #F2AE98 135%)', borderRadius: 20, padding: '24px 28px', display: 'flex', alignItems: 'center', gap: 40, color: C.cream, position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', right: -80, top: -80, width: 260, height: 260, borderRadius: '50%', border: '1px solid rgba(255,255,255,.12)' }} />
          <div style={{ position: 'absolute', right: -20, top: -20, width: 140, height: 140, borderRadius: '50%', border: '1px solid rgba(255,255,255,.12)' }} />
          <div style={{ flex: 1.3 }}>
            <div style={{ fontFamily: F.mono, fontSize: 11, letterSpacing: '.08em', textTransform: 'uppercase', opacity: 0.7 }}>Graph detection vs rule-based baseline</div>
            <div style={{ fontFamily: F.display, fontSize: 24, fontWeight: 600, marginTop: 6 }}>The graph catches what thresholds miss.</div>
            <Link to="/evaluation" style={{ display: 'inline-block', marginTop: 12, fontFamily: F.ui, fontSize: 13, fontWeight: 700, color: C.teal, background: C.cream, padding: '8px 14px', borderRadius: 999, textDecoration: 'none' }}>See full evaluation →</Link>
          </div>
          {[['Graph F1', hm.graph_f1, '#FFFFFF'], ['Rules F1', hm.baseline_f1, 'rgba(255,255,255,.62)'], ['Graph recall', hm.graph_recall, '#FFFFFF'], ['Rules recall', hm.baseline_recall, 'rgba(255,255,255,.62)']].map(([l, v, c]) => (
            <div key={l as string}>
              <div style={{ fontFamily: F.ui, fontSize: 12, opacity: 0.7 }}>{l as string}</div>
              <div style={{ fontFamily: F.display, fontSize: 34, fontWeight: 600, color: c as string }}><CountUp to={(v as number) * 100} format={x => `${x.toFixed(1)}%`} /></div>
            </div>
          ))}
        </motion.div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 20, marginTop: 20 }}>
        <Card title="Daily volume vs flagged amount" delay={0.1}>
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.daily_volume} margin={{ left: 0, right: 8, top: 8 }}>
                <defs>
                  <linearGradient id="gTot" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C.teal} stopOpacity={0.28} /><stop offset="100%" stopColor={C.teal} stopOpacity={0} /></linearGradient>
                  <linearGradient id="gFl" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C.coral} stopOpacity={0.45} /><stop offset="100%" stopColor={C.coral} stopOpacity={0} /></linearGradient>
                </defs>
                <CartesianGrid stroke={C.line} vertical={false} />
                <XAxis dataKey="date" tickFormatter={d => d.slice(8)} tick={{ fontFamily: F.ui, fontSize: 11, fill: C.cocoa }} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={short} width={64} tick={{ fontFamily: F.ui, fontSize: 11, fill: C.cocoa }} axisLine={false} tickLine={false} />
                <Tooltip formatter={(v) => formatINR(Number(v))} contentStyle={{ fontFamily: F.ui, borderRadius: 12, border: `1px solid ${C.line}` }} />
                <Area type="monotone" dataKey="total_amount" name="Total" stroke={C.teal} strokeWidth={2} fill="url(#gTot)" animationDuration={1200} />
                <Area type="monotone" dataKey="flagged_amount" name="Flagged" stroke={C.coral} strokeWidth={2} fill="url(#gFl)" animationDuration={1400} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Clusters by typology" delay={0.15}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {data.typology_counts.map((t, i) => (
              <div key={t.typology}>
                <div style={{ display: 'flex', fontFamily: F.ui, fontSize: 13, color: C.espresso }}><span style={{ flex: 1 }}>{t.label}</span><b style={{ fontFamily: F.mono }}>{t.count}</b></div>
                <div style={{ height: 8, background: C.sand, borderRadius: 4, marginTop: 6, overflow: 'hidden' }}>
                  <motion.div initial={{ width: 0 }} animate={{ width: `${(t.count / maxTyp) * 100}%` }} transition={{ duration: 0.9, ease, delay: 0.3 + i * 0.08 }} style={{ height: '100%', background: i === 0 ? C.coral : C.teal, borderRadius: 4 }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card title="Priority alerts" right={<Link to="/clusters" style={{ fontFamily: F.ui, fontSize: 13, fontWeight: 600, color: C.teal, textDecoration: 'none' }}>All clusters →</Link>} pad={0} style={{ marginTop: 20 }} delay={0.2}>
        {data.top_alerts.map((a, i) => (
          <motion.div key={a.alert_id} onClick={() => nav(`/clusters/${a.cluster_id}`)}
            initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4, ease, delay: 0.35 + i * 0.06 }}
            whileHover={{ backgroundColor: '#E9E8F8', x: 4 }}
            style={{ display: 'grid', gridTemplateColumns: '64px 1fr 220px 140px 24px', gap: 16, alignItems: 'center', padding: '14px 24px', borderTop: i ? `1px solid ${C.line}` : 'none', cursor: 'pointer' }}>
            <motion.div layoutId={`score-${a.cluster_id}`} style={{ fontFamily: F.display, fontSize: 28, fontWeight: 600, color: a.risk_level === 'high' ? C.coral : C.ochre }}>{a.risk_score}</motion.div>
            <div>
              <div style={{ fontFamily: F.ui, fontSize: 14, fontWeight: 600, color: C.espresso }}>{a.headline}</div>
              <div style={{ display: 'flex', gap: 6, marginTop: 6 }}><RiskBadge level={a.risk_level} />{a.typologies.slice(0, 2).map(t => <TypChip key={t} t={t} />)}</div>
            </div>
            <div style={{ fontFamily: F.ui, fontSize: 12, color: C.cocoa }}>{TYPOLOGY_LABELS[a.primary_typology]} · {a.account_count} accounts</div>
            <div style={{ fontFamily: F.mono, fontSize: 14, color: C.espresso, textAlign: 'right' }}>{formatINR(a.total_amount)}</div>
            <div style={{ color: C.teal, fontSize: 18 }}>→</div>
          </motion.div>
        ))}
      </Card>
      <Grid cols={1}><div /></Grid>
    </div>
  );
}
