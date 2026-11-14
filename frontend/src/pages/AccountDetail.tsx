import { Link, useParams } from 'react-router-dom';
import { getAccount } from '../api/endpoints';
import GraphCanvas from '../components/graph/GraphCanvas';
import { formatDate, formatDuration, formatINR } from '../lib/format';
import { TYPOLOGY_LABELS } from '../types/contract';
import { AccountLink, C, F, Card, ErrorState, Grid, Loading, Page, RiskBadge, Stat, TypChip, mono, num, td, th, useLoad } from '../components/ui';

export default function AccountDetail() {
  const { accountId = '' } = useParams();
  const { data, error, status, loading, reload } = useLoad(() => getAccount(accountId), [accountId]);

  if (loading) return <Loading what="account" />;
  if (error || !data) return <ErrorState error={error ?? 'Not found'} status={status} onRetry={reload} />;
  const a = data.account;
  const r = data.risk;

  return (
    <Page
      title={a.account_id}
      subtitle={<>Active {formatDate(a.first_seen)} → {formatDate(a.last_seen)}</>}
      actions={<RiskBadge level={r.risk_level} score={r.risk_score} />}
    >
      <Grid cols={4}>
        <Stat label="Total received" value={formatINR(a.total_in)} />
        <Stat label="Total sent" value={formatINR(a.total_out)} />
        <Stat label="Transactions in / out" value={`${a.in_tx_count} / ${a.out_tx_count}`} />
        <Stat label="Counterparties in / out" value={`${a.in_degree} / ${a.out_degree}`} />
        <Stat label="Median dwell time" value={a.median_dwell_minutes != null ? formatDuration(a.median_dwell_minutes) : '—'} />
        <Stat label="Retention ratio" value={a.retention_ratio != null ? `${(a.retention_ratio * 100).toFixed(0)}%` : '—'} />
        <Stat label="Max sent in 24 h" value={formatINR(a.max_out_24h_amount)} />
        <Stat label="Max transfers in 24 h" value={a.max_out_24h_count} />
      </Grid>

      {(r.typologies.length > 0 || r.cluster_ids.length > 0) && (
        <Card title="Risk context">
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            {r.typologies.map(t => <TypChip key={t} t={t} />)}
            <span style={{ fontFamily: F.ui, fontSize: 13, color: C.cocoa, marginLeft: 8 }}>Clusters:</span>
            {r.cluster_ids.map(id => <Link key={id} to={`/clusters/${id}`} style={{ fontFamily: F.mono, fontSize: 13, color: C.slate }}>{id}</Link>)}
          </div>
        </Card>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 20 }}>
        <Card title="1-hop network" pad={0}>
          <div style={{ height: 420 }}><GraphCanvas graph={data.subgraph} highlightIds={new Set([a.account_id])} /></div>
        </Card>
        <Card title="Top counterparties" pad={0}>
          <div style={{ maxHeight: 420, overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr><th style={th}>Account</th><th style={th}>Direction</th><th style={{ ...th, textAlign: 'right' }}>Txs</th><th style={{ ...th, textAlign: 'right' }}>Amount</th></tr></thead>
              <tbody>{data.counterparties.map(cp => (
                <tr key={cp.account_id + cp.direction}>
                  <td style={mono}><AccountLink id={cp.account_id} /></td>
                  <td style={{ ...td, color: cp.direction === 'in' ? C.olive : C.ochre, fontWeight: 600 }}>{cp.direction === 'in' ? '← received' : '→ sent'}</td>
                  <td style={num}>{cp.tx_count}</td>
                  <td style={num}>{formatINR(cp.total_amount)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </Card>
      </div>

      {data.patterns.length > 0 && (
        <Card title="Patterns involving this account" pad={0}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr><th style={th}>Pattern</th><th style={th}>Type</th><th style={th}>Cluster</th><th style={th}>Window</th><th style={{ ...th, textAlign: 'right' }}>Amount</th></tr></thead>
            <tbody>{data.patterns.map(p => (
              <tr key={p.pattern_id}>
                <td style={mono}>{p.pattern_id}</td>
                <td style={td}>{TYPOLOGY_LABELS[p.pattern_type]}</td>
                <td style={mono}>{p.cluster_id ? <Link to={`/clusters/${p.cluster_id}`} style={{ color: C.slate }}>{p.cluster_id}</Link> : '—'}</td>
                <td style={{ ...td, fontSize: 12 }}>{formatDate(p.start_time)} – {formatDate(p.end_time)}</td>
                <td style={num}>{formatINR(p.total_amount)}</td>
              </tr>
            ))}</tbody>
          </table>
        </Card>
      )}

      <Card title={`Recent transactions (${data.transactions.length})`} pad={0}>
        <div style={{ maxHeight: 420, overflowY: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr><th style={th}>ID</th><th style={th}>Time</th><th style={th}>From</th><th style={th}>To</th><th style={{ ...th, textAlign: 'right' }}>Amount</th><th style={th}>Graph flag</th></tr></thead>
            <tbody>{data.transactions.map(t => (
              <tr key={t.transaction_id}>
                <td style={mono}>{t.transaction_id}</td>
                <td style={{ ...td, fontSize: 12 }}>{formatDate(t.timestamp)}</td>
                <td style={mono}><AccountLink id={t.sender} /></td>
                <td style={mono}><AccountLink id={t.receiver} /></td>
                <td style={num}>{formatINR(t.amount)}</td>
                <td style={{ ...td, fontSize: 12, color: t.prediction.graph_flagged ? C.terracotta : C.stone, fontWeight: t.prediction.graph_flagged ? 600 : 400 }}>{t.prediction.graph_flagged ? t.prediction.cluster_id : '—'}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </Card>
    </Page>
  );
}
