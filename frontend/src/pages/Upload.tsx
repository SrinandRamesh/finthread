import { useRef, useState, type DragEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { loadSample, uploadCsv } from '../api/endpoints';
import type { UploadResponse } from '../types/contract';
import { Btn, C, F, Card, Grid, Page, Stat, mono, td, th } from '../components/ui';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const COLUMNS: [string, string, string][] = [
  ['transaction_id', 'yes', 'Unique id, e.g. TX000001'],
  ['sender', 'yes', 'Account id of the payer'],
  ['receiver', 'yes', 'Account id of the payee (must differ from sender)'],
  ['amount', 'yes', 'Positive number, INR'],
  ['timestamp', 'yes', '2026-11-14T10:00:00 or 2026-11-14 10:00:00'],
  ['currency', 'no', 'Default INR'],
  ['channel', 'no', 'UPI, IMPS, NEFT, RTGS, CASH, OTHER'],
  ['label', 'no', 'Ground truth: suspicious / normal (used only for evaluation)'],
  ['gt_typology', 'no', 'Ground-truth typology code (evaluation only)'],
];

export default function UploadPage() {
  const nav = useNavigate();
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<UploadResponse>) {
    setBusy(true); setError(null); setResult(null);
    try { setResult(await fn()); } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Upload failed'); }
    finally { setBusy(false); }
  }
  function onFile(f?: File | null) { if (f) run(() => uploadCsv(f)); }
  function onDrop(e: DragEvent) { e.preventDefault(); setDrag(false); onFile(e.dataTransfer.files?.[0]); }

  return (
    <Page title="Upload transactions" subtitle="Upload a CSV of transactions, or load the bundled synthetic sample. Analysis runs automatically after upload.">
      <Card>
        <div
          onDragOver={e => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
          onClick={() => input.current?.click()}
          style={{ border: `2px dashed ${drag ? C.gold : C.line}`, background: drag ? C.goldSoft : C.cream, borderRadius: 14, padding: 40, textAlign: 'center', cursor: 'pointer', transition: 'all .2s' }}
        >
          <div style={{ fontFamily: F.display, fontSize: 24, color: C.espresso, fontWeight: 600 }}>{busy ? 'Analysing…' : 'Drop a CSV here or click to choose'}</div>
          <div style={{ fontFamily: F.ui, fontSize: 13, color: C.cocoa, marginTop: 6 }}>Up to 10 MB / 50,000 rows</div>
          <input ref={input} type="file" accept=".csv,text/csv" hidden onChange={e => onFile(e.target.files?.[0])} />
        </div>
        <div style={{ display: 'flex', gap: 12, marginTop: 16, flexWrap: 'wrap' }}>
          <Btn onClick={() => run(loadSample)} disabled={busy}>Load sample dataset</Btn>
          <a href={`${BASE_URL}/api/dataset/sample`} style={{ textDecoration: 'none' }}><Btn kind="ghost">Download sample CSV</Btn></a>
        </div>
        {error && <div style={{ marginTop: 16, color: C.terracotta, fontFamily: F.ui, fontSize: 14 }}>⚠ {error}</div>}
      </Card>

      {result && (
        <>
          <Grid cols={4}>
            <Stat label="Rows read" value={result.validation.total_rows.toLocaleString('en-IN')} />
            <Stat label="Accepted" value={result.validation.accepted_rows.toLocaleString('en-IN')} color={C.olive} />
            <Stat label="Rejected" value={result.validation.rejected_rows.toLocaleString('en-IN')} color={result.validation.rejected_rows ? C.terracotta : C.espresso} />
            <Stat label="Has labels" value={result.validation.has_labels ? 'Yes' : 'No'} />
          </Grid>
          {result.run && (
            <Card title="Analysis complete" right={<Btn onClick={() => nav('/dashboard')}>Go to overview →</Btn>}>
              <Grid cols={5}>
                <Stat label="Transactions" value={result.run.counts.transactions.toLocaleString('en-IN')} />
                <Stat label="Accounts" value={result.run.counts.accounts.toLocaleString('en-IN')} />
                <Stat label="Patterns" value={result.run.counts.patterns} />
                <Stat label="Clusters" value={result.run.counts.clusters} />
                <Stat label="Alerts" value={result.run.counts.alerts} color={C.terracotta} />
              </Grid>
              <div style={{ fontFamily: F.ui, fontSize: 12, color: C.cocoa, marginTop: 12 }}>Finished in {(result.run.duration_ms / 1000).toFixed(1)} s · dataset {result.dataset.name}</div>
            </Card>
          )}
          {result.validation.errors.length > 0 && (
            <Card title={`Rejected rows (first ${result.validation.errors.length})`} pad={0}>
              <div style={{ maxHeight: 320, overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead><tr><th style={th}>Row</th><th style={th}>Transaction</th><th style={th}>Field</th><th style={th}>Problem</th></tr></thead>
                  <tbody>{result.validation.errors.map((e, i) => (
                    <tr key={i}><td style={mono}>{e.row_number}</td><td style={mono}>{e.transaction_id ?? '—'}</td><td style={mono}>{e.field ?? '—'}</td><td style={td}>{e.message}</td></tr>
                  ))}</tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}

      <Card title="Expected CSV columns" pad={0}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead><tr><th style={th}>Column</th><th style={th}>Required</th><th style={th}>Notes</th></tr></thead>
          <tbody>{COLUMNS.map(([c, r, n]) => (
            <tr key={c}><td style={mono}>{c}</td><td style={{ ...td, color: r === 'yes' ? C.espresso : C.stone, fontWeight: r === 'yes' ? 600 : 400 }}>{r}</td><td style={td}>{n}</td></tr>
          ))}</tbody>
        </table>
      </Card>
    </Page>
  );
}
