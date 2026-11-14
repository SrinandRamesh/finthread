import { useState } from 'react';
import { Link } from 'react-router-dom';
import { getTransactions } from '../api/endpoints';
import { formatDate, formatINR } from '../lib/format';
import { TYPOLOGY_LABELS, type PatternType } from '../types/contract';
import { AccountLink, Btn, C, F, Card, ErrorState, Loading, Page, TypChip, mono, num, td, th, useLoad } from '../components/ui';

const PATTERNS: PatternType[] = ['FAN_IN', 'FAN_OUT', 'CYCLE', 'PASS_THROUGH'];
const PAGE_SIZE = 50;

export default function Transactions() {
  const [page, setPage] = useState(1);
  const [account, setAccount] = useState('');
  const [minAmount, setMinAmount] = useState('');
  const [pattern, setPattern] = useState('');
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [sort, setSort] = useState('-timestamp');

  const p = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE), sort });
  if (account.trim()) p.set('account', account.trim());
  if (minAmount) p.set('min_amount', minAmount);
  if (pattern) p.set('pattern', pattern);
  if (flaggedOnly) p.set('flagged_only', 'true');
  const q = p.toString();
  const { data, error, status, loading, reload } = useLoad(() => getTransactions(q), [q]);

  const ctl = { fontFamily: F.ui, fontSize: 13, color: C.espresso, background: C.ivory, border: `1px solid ${C.line}`, borderRadius: 10, padding: '8px 10px' };
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const reset = (fn: () => void) => { fn(); setPage(1); };

  return (
    <Page title="Transactions" subtitle="Every transaction with the graph model's flag, the baseline's rules and (separately) the ground-truth label.">
      <Card pad={16}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', fontFamily: F.ui, fontSize: 13, color: C.cocoa }}>
          <input placeholder="Account id" value={account} onChange={e => reset(() => setAccount(e.target.value))} style={{ ...ctl, width: 140 }} />
          <input placeholder="Min amount" type="number" value={minAmount} onChange={e => reset(() => setMinAmount(e.target.value))} style={{ ...ctl, width: 130 }} />
          <select value={pattern} onChange={e => reset(() => setPattern(e.target.value))} style={ctl}>
            <option value="">Any pattern</option>
            {PATTERNS.map(t => <option key={t} value={t}>{TYPOLOGY_LABELS[t]}</option>)}
          </select>
          <select value={sort} onChange={e => reset(() => setSort(e.target.value))} style={ctl}>
            <option value="-timestamp">Newest first</option>
            <option value="timestamp">Oldest first</option>
            <option value="-amount">Largest first</option>
            <option value="amount">Smallest first</option>
          </select>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" checked={flaggedOnly} onChange={e => reset(() => setFlaggedOnly(e.target.checked))} /> Graph-flagged only
          </label>
          {data && <span style={{ marginLeft: 'auto' }}>{data.total.toLocaleString('en-IN')} transactions</span>}
        </div>
      </Card>

      {loading && !data && <Loading what="transactions" />}
      {error && <ErrorState error={error} status={status} onRetry={reload} />}

      {data && (
        <Card pad={0}>
          <div style={{ overflowX: 'auto', opacity: loading ? 0.6 : 1 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr>
                <th style={th}>ID</th><th style={th}>Time</th><th style={th}>From → To</th><th style={{ ...th, textAlign: 'right' }}>Amount</th>
                <th style={th}>Channel</th><th style={th}>Graph</th><th style={th}>Baseline</th><th style={th} title="Ground truth from the dataset, never used by detection">Ground truth</th>
              </tr></thead>
              <tbody>
                {data.items.map(t => (
                  <tr key={t.transaction_id}>
                    <td style={mono}>{t.transaction_id}</td>
                    <td style={{ ...td, fontSize: 12, whiteSpace: 'nowrap' }}>{formatDate(t.timestamp)}</td>
                    <td style={{ ...mono, whiteSpace: 'nowrap' }}><AccountLink id={t.sender} /> <span style={{ color: C.stone }}>→</span> <AccountLink id={t.receiver} /></td>
                    <td style={num}>{formatINR(t.amount)}</td>
                    <td style={td}>{t.channel ?? '—'}</td>
                    <td style={td}>
                      {t.prediction.graph_flagged
                        ? <Link to={`/clusters/${t.prediction.cluster_id}`} style={{ color: C.terracotta, fontWeight: 600, textDecoration: 'none', fontSize: 12 }}>● {t.prediction.cluster_id}</Link>
                        : <span style={{ color: C.stone, fontSize: 12 }}>—</span>}
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>{t.prediction.patterns.map(pt => <TypChip key={pt} t={pt} />)}</div>
                    </td>
                    <td style={{ ...td, fontSize: 12, color: t.prediction.baseline_flagged ? C.slate : C.stone }}>{t.prediction.baseline_flagged ? t.prediction.baseline_rules.join(', ') : '—'}</td>
                    <td style={{ ...td, fontSize: 12, color: C.stone }}>{t.ground_truth?.label ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 14, borderTop: `1px solid ${C.line}`, fontFamily: F.ui, fontSize: 13, color: C.cocoa }}>
            <Btn kind="ghost" onClick={() => setPage(x => Math.max(1, x - 1))} disabled={page <= 1}>← Prev</Btn>
            <span>Page {page} of {pages}</span>
            <Btn kind="ghost" onClick={() => setPage(x => Math.min(pages, x + 1))} disabled={page >= pages}>Next →</Btn>
          </div>
        </Card>
      )}
    </Page>
  );
}
