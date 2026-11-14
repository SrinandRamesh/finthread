import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { getClusters } from '../api/endpoints';
import { formatDate, formatDuration, formatINR } from '../lib/format';
import { TYPOLOGY_LABELS, type Typology } from '../types/contract';
import { C, F, Card, ErrorState, Loading, Page, RiskBadge, TypChip, useLoad } from '../components/ui';

const TYPS = Object.keys(TYPOLOGY_LABELS) as Typology[];

export default function Clusters() {
  const [minRisk, setMinRisk] = useState(0);
  const [search] = useSearchParams();
  const [typology, setTypology] = useState(search.get('typology') ?? '');
  const [alertedOnly, setAlertedOnly] = useState(false);
  const [sort, setSort] = useState('-risk_score');

  const params = new URLSearchParams();
  if (minRisk > 0) params.set('min_risk', String(minRisk));
  if (typology) params.set('typology', typology);
  if (alertedOnly) params.set('alerted_only', 'true');
  params.set('sort', sort);
  const q = params.toString();
  const { data, error, status, loading, reload } = useLoad(() => getClusters(q), [q]);

  const ctl = { fontFamily: F.ui, fontSize: 13, color: C.espresso, background: C.ivory, border: `1px solid ${C.line}`, borderRadius: 10, padding: '8px 10px' };

  return (
    <Page title="Suspicious clusters" subtitle="Connected groups of accounts whose transactions matched one or more layering patterns, ranked by risk.">
      <Card pad={16}>
        <div style={{ display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap', fontFamily: F.ui, fontSize: 13, color: C.cocoa }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            Min risk <input type="range" min={0} max={100} step={5} value={minRisk} onChange={e => setMinRisk(Number(e.target.value))} />
            <b style={{ color: C.espresso, width: 24 }}>{minRisk}</b>
          </label>
          <select value={typology} onChange={e => setTypology(e.target.value)} style={ctl}>
            <option value="">All typologies</option>
            {TYPS.map(t => <option key={t} value={t}>{TYPOLOGY_LABELS[t]}</option>)}
          </select>
          <select value={sort} onChange={e => setSort(e.target.value)} style={ctl}>
            <option value="-risk_score">Highest risk first</option>
            <option value="-total_amount">Largest amount first</option>
            <option value="start_time">Earliest first</option>
          </select>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" checked={alertedOnly} onChange={e => setAlertedOnly(e.target.checked)} /> Alerted only
          </label>
          {data && <span style={{ marginLeft: 'auto' }}>{data.total} clusters</span>}
        </div>
      </Card>

      {loading && <Loading what="clusters" />}
      {error && <ErrorState error={error} status={status} onRetry={reload} />}

      {data && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {data.items.map(c => (
            <Link key={c.cluster_id} to={`/clusters/${c.cluster_id}`} style={{ textDecoration: 'none' }}>
              <div style={{ background: C.ivory, border: `1px solid ${C.line}`, borderLeft: `4px solid ${c.risk_level === 'high' ? C.terracotta : c.risk_level === 'medium' ? C.ochre : C.olive}`, borderRadius: 14, padding: '16px 20px', display: 'grid', gridTemplateColumns: '90px 1fr 140px 150px', gap: 20, alignItems: 'center' }}>
                <div>
                  <div style={{ fontFamily: F.display, fontSize: 32, fontWeight: 600, color: c.risk_level === 'high' ? C.terracotta : c.risk_level === 'medium' ? C.ochre : C.olive, lineHeight: 1 }}>{c.risk_score}</div>
                  <div style={{ marginTop: 6 }}><RiskBadge level={c.risk_level} /></div>
                </div>
                <div>
                  <div style={{ fontFamily: F.ui, fontSize: 15, fontWeight: 600, color: C.espresso }}>{c.headline}</div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
                    {c.typologies.map(t => <TypChip key={t} t={t} />)}
                    {!c.alerted && <span style={{ fontFamily: F.ui, fontSize: 12, color: C.stone, padding: '2px 4px' }}>below alert threshold</span>}
                  </div>
                </div>
                <div style={{ fontFamily: F.ui, fontSize: 12, color: C.cocoa, lineHeight: 1.6 }}>
                  <div><b style={{ color: C.espresso }}>{c.account_count}</b> accounts</div>
                  <div><b style={{ color: C.espresso }}>{c.transaction_count}</b> transactions</div>
                  <div>hop {c.median_hop_minutes != null ? formatDuration(c.median_hop_minutes) : '—'}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontFamily: F.mono, fontSize: 15, color: C.espresso, fontWeight: 500 }}>{formatINR(c.total_amount)}</div>
                  <div style={{ fontFamily: F.ui, fontSize: 11, color: C.cocoa, marginTop: 4 }}>{formatDate(c.start_time)}</div>
                  <div style={{ fontFamily: F.mono, fontSize: 11, color: C.stone, marginTop: 2 }}>{c.cluster_id}</div>
                </div>
              </div>
            </Link>
          ))}
          {data.items.length === 0 && <Card><span style={{ fontFamily: F.ui, color: C.cocoa }}>No clusters match these filters.</span></Card>}
        </div>
      )}
    </Page>
  );
}
