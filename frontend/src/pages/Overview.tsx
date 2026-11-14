import React from 'react';
import { useApi } from '../hooks/useApi';
import { getOverview, loadSample } from '../api/endpoints';
import { formatINR, formatDate } from '../lib/format';
import { TYPOLOGY_LABELS } from '../types/contract';

function RiskBadge({ level }: { level: string }) {
  const styles: Record<string, { background: string; color: string }> = {
    high: { background: '#F8E1D9', color: '#C0502F' },
    medium: { background: '#FBEBD0', color: '#D9962B' },
    low: { background: '#E4EDDD', color: '#5E7F4F' },
    none: { background: '#F1ECE4', color: '#A79B8B' },
  };
  const s = styles[level] ?? styles.none;
  return (
    <span style={{ ...s, padding: '2px 10px', borderRadius: 999, fontSize: 12, fontWeight: 600, fontFamily: 'Manrope, sans-serif' }}>
      {level.toUpperCase()}
    </span>
  );
}

export default function Overview() {
  const { data, loading, error, reload } = useApi(getOverview);
  const [loading2, setLoading2] = React.useState(false);

  async function handleLoadSample() {
    setLoading2(true);
    try { await loadSample(); reload(); } catch (e) { alert('Failed to load sample'); }
    finally { setLoading2(false); }
  }

  if (loading) return (
    <div style={{ padding: 32, fontFamily: 'Manrope, sans-serif', color: '#6B5A48' }}>Loading overview…</div>
  );

  if (error) return (
    <div style={{ padding: 32 }}>
      <div style={{ background: '#FFFDF8', border: '1px solid #E7DAC3', borderRadius: 14, padding: 32, maxWidth: 480 }}>
        <h2 style={{ fontFamily: 'Fraunces, serif', fontSize: 28, color: '#2A1F16', fontWeight: 600 }}>No analysis yet</h2>
        <p style={{ fontFamily: 'Manrope, sans-serif', color: '#6B5A48', marginTop: 8 }}>Load the sample dataset to see the overview.</p>
        <button onClick={handleLoadSample} disabled={loading2} style={{ marginTop: 20, background: '#B8862F', color: '#FFFDF8', border: 'none', borderRadius: 10, padding: '12px 28px', fontFamily: 'Manrope, sans-serif', fontWeight: 600, fontSize: 14, cursor: 'pointer' }}>
          {loading2 ? 'Loading…' : 'Load sample dataset'}
        </button>
      </div>
    </div>
  );

  const s = data!.stats;

  const tiles = [
    { label: 'Transactions', value: s.total_transactions.toLocaleString('en-IN') },
    { label: 'Accounts', value: s.total_accounts.toLocaleString('en-IN') },
    { label: 'Total Amount', value: formatINR(s.total_amount) },
    { label: 'Flagged Transactions', value: s.flagged_transactions.toLocaleString('en-IN'), accent: true },
    { label: 'Clusters', value: s.clusters.toLocaleString('en-IN') },
    { label: 'High Risk Alerts', value: s.high_risk_alerts.toLocaleString('en-IN'), accent: true },
  ];

  return (
    <div style={{ padding: 32, maxWidth: 1200 }}>
      <h1 style={{ fontFamily: 'Fraunces, serif', fontSize: 40, color: '#2A1F16', fontWeight: 600 }}>Overview</h1>
      <p style={{ fontFamily: 'Manrope, sans-serif', color: '#6B5A48', marginTop: 4 }}>
        Dataset: {data!.dataset.name} · {data!.dataset.row_count.toLocaleString('en-IN')} rows · Last run: {formatDate(data!.run.finished_at)}
      </p>

      {/* KPI Tiles */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginTop: 32 }}>
        {tiles.map(t => (
          <div key={t.label} style={{ background: '#FFFDF8', border: '1px solid #E7DAC3', borderRadius: 14, padding: 24, boxShadow: '0 1px 2px rgba(42,31,22,.04), 0 8px 24px rgba(42,31,22,.06)' }}>
            <div style={{ fontFamily: 'Manrope, sans-serif', fontSize: 13, color: '#6B5A48', fontWeight: 500 }}>{t.label}</div>
            <div style={{ fontFamily: 'Fraunces, serif', fontSize: 36, fontWeight: 600, color: t.accent ? '#C0502F' : '#2A1F16', marginTop: 8 }}>{t.value}</div>
          </div>
        ))}
      </div>

      {/* Headline Metrics */}
      {data!.headline_metrics && (
        <div style={{ marginTop: 24, background: '#FFFDF8', border: '1px solid #E7DAC3', borderRadius: 14, padding: 24, display: 'flex', gap: 48 }}>
          <div>
            <div style={{ fontFamily: 'Manrope, sans-serif', fontSize: 13, color: '#6B5A48' }}>Graph F1</div>
            <div style={{ fontFamily: 'Fraunces, serif', fontSize: 32, color: '#5E7F4F', fontWeight: 600 }}>{(data!.headline_metrics.graph_f1 * 100).toFixed(1)}%</div>
          </div>
          <div>
            <div style={{ fontFamily: 'Manrope, sans-serif', fontSize: 13, color: '#6B5A48' }}>Baseline F1</div>
            <div style={{ fontFamily: 'Fraunces, serif', fontSize: 32, color: '#4F6D8A', fontWeight: 600 }}>{(data!.headline_metrics.baseline_f1 * 100).toFixed(1)}%</div>
          </div>
          <div>
            <div style={{ fontFamily: 'Manrope, sans-serif', fontSize: 13, color: '#6B5A48' }}>Graph Recall</div>
            <div style={{ fontFamily: 'Fraunces, serif', fontSize: 32, color: '#5E7F4F', fontWeight: 600 }}>{(data!.headline_metrics.graph_recall * 100).toFixed(1)}%</div>
          </div>
          <div>
            <div style={{ fontFamily: 'Manrope, sans-serif', fontSize: 13, color: '#6B5A48' }}>Baseline Recall</div>
            <div style={{ fontFamily: 'Fraunces, serif', fontSize: 32, color: '#4F6D8A', fontWeight: 600 }}>{(data!.headline_metrics.baseline_recall * 100).toFixed(1)}%</div>
          </div>
        </div>
      )}

      {/* Top Alerts */}
      <div style={{ marginTop: 24, background: '#FFFDF8', border: '1px solid #E7DAC3', borderRadius: 14, overflow: 'hidden' }}>
        <div style={{ padding: '16px 24px', borderBottom: '1px solid #E7DAC3' }}>
          <span style={{ fontFamily: 'Manrope, sans-serif', fontWeight: 600, color: '#2A1F16', fontSize: 16 }}>Top Alerts</span>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#F1E6D2' }}>
              {['Risk', 'Typology', 'Headline', 'Accounts', 'Amount', 'Link'].map(h => (
                <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontFamily: 'Manrope, sans-serif', fontSize: 12, fontWeight: 600, color: '#6B5A48' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data!.top_alerts.map((a, i) => (
              <tr key={a.alert_id} style={{ borderTop: '1px solid #E7DAC3', background: i % 2 === 0 ? '#FFFDF8' : '#FBF6EC' }}>
                <td style={{ padding: '10px 16px' }}><RiskBadge level={a.risk_level} /></td>
                <td style={{ padding: '10px 16px', fontFamily: 'Manrope, sans-serif', fontSize: 13, color: '#6B5A48' }}>{TYPOLOGY_LABELS[a.primary_typology]}</td>
                <td style={{ padding: '10px 16px', fontFamily: 'Manrope, sans-serif', fontSize: 13, color: '#2A1F16' }}>{a.headline}</td>
                <td style={{ padding: '10px 16px', fontFamily: 'IBM Plex Mono, monospace', fontSize: 13, color: '#2A1F16' }}>{a.account_count}</td>
                <td style={{ padding: '10px 16px', fontFamily: 'IBM Plex Mono, monospace', fontSize: 13, color: '#2A1F16', textAlign: 'right' }}>{formatINR(a.total_amount)}</td>
                <td style={{ padding: '10px 16px' }}>
                  <a href={`/clusters/${a.cluster_id}`} style={{ color: '#4F6D8A', fontFamily: 'Manrope, sans-serif', fontSize: 13 }}>Investigate →</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}