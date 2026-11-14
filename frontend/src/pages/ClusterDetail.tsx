import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { getCluster } from '../api/endpoints';
import GraphCanvas from '../components/graph/GraphCanvas';
import { formatDate, formatDuration, formatINR } from '../lib/format';
import { TYPOLOGY_LABELS } from '../types/contract';
import { AccountLink, C, F, Card, ErrorState, Grid, Loading, Page, RiskBadge, Stat, TypChip, mono, num, td, th, useLoad } from '../components/ui';

const ROLE_COLOR: Record<string, string> = { source: C.slate, intermediary: C.ochre, collector: C.terracotta, member: C.stone };

export default function ClusterDetail() {
  const { clusterId = '' } = useParams();
  const { data: c, error, status, loading, reload } = useLoad(() => getCluster(clusterId), [clusterId]);
  const [focus, setFocus] = useState<Set<string>>(new Set());

  if (loading) return <Loading what="investigation" />;
  if (error || !c) return <ErrorState error={error ?? 'Not found'} status={status} onRetry={reload} />;

  const color = c.risk_level === 'high' ? C.terracotta : c.risk_level === 'medium' ? C.ochre : C.olive;

  return (
    <Page
      title={c.headline}
      subtitle={<><Link to="/clusters" style={{ color: C.slate, textDecoration: 'none' }}>← Clusters</Link> · {c.cluster_id} · {formatDate(c.start_time)} → {formatDate(c.end_time)}</>}
    >
      <Grid cols={5}>
        <div style={{ background: C.ivory, border: `1px solid ${C.line}`, borderRadius: 14, padding: 20 }}>
          <div style={{ fontFamily: F.ui, fontSize: 12, color: C.cocoa }}>Risk score</div>
          <div style={{ display: 'flex', alignItems: 'baseline' }}><motion.div layoutId={`score-${c.cluster_id}`} transition={{ type: 'spring', stiffness: 260, damping: 30 }} style={{ fontFamily: F.display, fontSize: 44, fontWeight: 600, color, lineHeight: 1.1 }}>{c.risk_score}</motion.div><span style={{ fontFamily: F.display, fontSize: 18, color: C.stone }}>/100</span></div>
          <RiskBadge level={c.risk_level} />
        </div>
        <Stat label="Total moved" value={formatINR(c.total_amount)} />
        <Stat label="Accounts" value={c.account_count} />
        <Stat label="Transactions" value={c.transaction_count} />
        <Stat label="Median hop time" value={c.median_hop_minutes != null ? formatDuration(c.median_hop_minutes) : '—'} />
      </Grid>

      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>{c.typologies.map(t => <TypChip key={t} t={t} />)}</div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 20 }}>
        <Card title="What happened">
          <p style={{ fontFamily: F.ui, fontSize: 15, lineHeight: 1.65, color: C.espresso, margin: 0 }}>{c.explanation.summary}</p>
          <ul style={{ fontFamily: F.ui, fontSize: 13, color: C.cocoa, lineHeight: 1.7, paddingLeft: 18, marginTop: 14 }}>
            {c.explanation.bullet_points.map((b, i) => <li key={i}>{b}</li>)}
          </ul>
          <div style={{ marginTop: 14, background: C.cream, border: `1px dashed ${C.line}`, borderRadius: 10, padding: '10px 14px', fontFamily: F.ui, fontSize: 12, color: C.cocoa }}>
            {c.explanation.disclaimer}
          </div>
        </Card>
        <Card title="Why this score">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {c.score_breakdown.map(f => (
              <div key={f.factor}>
                <div style={{ display: 'flex', fontFamily: F.ui, fontSize: 13, color: C.espresso, fontWeight: 600 }}>
                  <span style={{ flex: 1, textTransform: 'capitalize' }}>{f.factor.replace(/_/g, ' ')}</span>
                  <span style={{ fontFamily: F.mono }}>{f.points}/{f.max_points}</span>
                </div>
                <div style={{ height: 8, background: C.sand, borderRadius: 4, marginTop: 6, overflow: 'hidden' }}>
                  <motion.div initial={{ width: 0 }} animate={{ width: `${(f.points / f.max_points) * 100}%` }} transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay: 0.3 }} style={{ height: '100%', background: f.points ? C.teal : 'transparent', borderRadius: 4 }} />
                </div>
                <div style={{ fontFamily: F.ui, fontSize: 12, color: C.cocoa, marginTop: 4 }}>{f.reason}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 20 }}>
        <Card title="Money trail graph" right={focus.size > 0 && <button onClick={() => setFocus(new Set())} style={{ background: 'none', border: 'none', color: C.slate, cursor: 'pointer', fontFamily: F.ui, fontSize: 12 }}>Clear highlight</button>} pad={0}>
          <div style={{ height: 460 }}>
            <GraphCanvas graph={c.subgraph} highlightIds={focus} />
          </div>
        </Card>
        <Card title="Accounts and roles" pad={0}>
          <div style={{ maxHeight: 460, overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr><th style={th}>Account</th><th style={th}>Role</th><th style={{ ...th, textAlign: 'right' }}>In</th><th style={{ ...th, textAlign: 'right' }}>Out</th></tr></thead>
              <tbody>
                {c.accounts.map(a => (
                  <tr key={a.account_id} onMouseEnter={() => setFocus(new Set([a.account_id]))}>
                    <td style={mono}><AccountLink id={a.account_id} /></td>
                    <td style={td}><span style={{ color: ROLE_COLOR[a.role], fontWeight: 600, textTransform: 'capitalize' }}>{a.role}</span></td>
                    <td style={num}>{formatINR(a.total_in)}</td>
                    <td style={num}>{formatINR(a.total_out)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <Card title="Evidence timeline">
        <div style={{ position: 'relative', paddingLeft: 22 }}>
          <div style={{ position: 'absolute', left: 6, top: 4, bottom: 4, width: 2, background: C.goldSoft }} />
          {c.explanation.evidence.map(e => (
            <div key={e.transaction_id} style={{ position: 'relative', paddingBottom: 16, cursor: 'pointer' }} onMouseEnter={() => setFocus(new Set([e.transaction_id, e.sender, e.receiver]))}>
              <div style={{ position: 'absolute', left: -21, top: 4, width: 12, height: 12, borderRadius: 6, background: C.gold, border: `2px solid ${C.ivory}` }} />
              <div style={{ display: 'flex', gap: 12, alignItems: 'baseline', flexWrap: 'wrap', fontFamily: F.ui, fontSize: 13 }}>
                <span style={{ fontFamily: F.mono, color: C.cocoa, fontSize: 12, width: 150 }}>{formatDate(e.timestamp)}</span>
                <AccountLink id={e.sender} /> <span style={{ color: C.stone }}>→</span> <AccountLink id={e.receiver} />
                <span style={{ fontFamily: F.mono, fontWeight: 600, color: C.espresso }}>{formatINR(e.amount)}</span>
                <span style={{ fontFamily: F.mono, fontSize: 11, color: C.stone }}>{e.transaction_id}</span>
              </div>
              <div style={{ fontFamily: F.ui, fontSize: 12, color: C.cocoa, marginTop: 2, marginLeft: 162 }}>{e.note}</div>
            </div>
          ))}
        </div>
      </Card>

      <Card title={`Matched patterns (${c.patterns.length})`} pad={0}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead><tr><th style={th}>Pattern</th><th style={th}>Type</th><th style={th}>Accounts</th><th style={th}>Window</th><th style={{ ...th, textAlign: 'right' }}>Amount</th></tr></thead>
          <tbody>
            {c.patterns.map(p => (
              <tr key={p.pattern_id} onMouseEnter={() => setFocus(new Set([...p.accounts, ...p.transaction_ids]))} style={{ cursor: 'pointer' }}>
                <td style={mono}>{p.pattern_id}</td>
                <td style={td}>{TYPOLOGY_LABELS[p.pattern_type]}</td>
                <td style={{ ...mono, fontSize: 12 }}>{p.accounts.slice(0, 6).join(' → ')}{p.accounts.length > 6 ? ' …' : ''}</td>
                <td style={{ ...td, fontSize: 12 }}>{formatDate(p.start_time)} – {formatDate(p.end_time)}</td>
                <td style={num}>{formatINR(p.total_amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card title={`All cluster transactions (${c.transactions.length})`} pad={0}>
        <div style={{ maxHeight: 420, overflowY: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr><th style={th}>ID</th><th style={th}>Time</th><th style={th}>From</th><th style={th}>To</th><th style={{ ...th, textAlign: 'right' }}>Amount</th><th style={th}>Channel</th><th style={th}>Baseline</th></tr></thead>
            <tbody>
              {c.transactions.map(t => (
                <tr key={t.transaction_id}>
                  <td style={mono}>{t.transaction_id}</td>
                  <td style={{ ...td, fontSize: 12 }}>{formatDate(t.timestamp)}</td>
                  <td style={mono}><AccountLink id={t.sender} /></td>
                  <td style={mono}><AccountLink id={t.receiver} /></td>
                  <td style={num}>{formatINR(t.amount)}</td>
                  <td style={td}>{t.channel ?? '—'}</td>
                  <td style={{ ...td, fontSize: 12, color: t.prediction.baseline_flagged ? C.slate : C.stone }}>{t.prediction.baseline_flagged ? t.prediction.baseline_rules.join(', ') : 'not flagged'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </Page>
  );
}
