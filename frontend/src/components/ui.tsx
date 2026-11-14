import { useCallback, useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { animate, motion, useInView } from 'framer-motion';
import { Link } from 'react-router-dom';
import { loadSample } from '../api/endpoints';
import { ApiError } from '../api/client';
import { TYPOLOGY_LABELS, type Typology } from '../types/contract';

export const C = {
  cream: '#E9E8F8', ivory: '#F8F8FD', sand: '#DFDEF2', line: '#D5D4EC',
  espresso: '#1C2541', cocoa: '#585F7E', gold: '#4677D2', goldSoft: '#DCE7FB',
  olive: '#3B9A84', ochre: '#E39B32', terracotta: '#EC6C4E', slate: '#7083B8', stone: '#9EA2BC', coral: '#FF9475', teal: '#4677D2', tealSoft: '#DCE7FB',
};
export const F = { display: 'Fraunces, serif', ui: 'Manrope, sans-serif', mono: 'IBM Plex Mono, monospace' };

/** Data loader that re-runs whenever `deps` change and keeps the HTTP status of errors. */
export function useLoad<T>(fetcher: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const load = useCallback(async () => {
    setLoading(true); setError(null); setStatus(null);
    try { setData(await fetcher()); }
    catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      setStatus(e instanceof ApiError ? e.status : null);
    } finally { setLoading(false); }
  }, deps);
  useEffect(() => { load(); }, [load]);
  return { data, error, status, loading, reload: load };
}

export function Page({ title, subtitle, actions, children }: { title: string; subtitle?: ReactNode; actions?: ReactNode; children: ReactNode }) {
  return (
    <div style={{ padding: 32, maxWidth: 1280 }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 280 }}>
          <motion.h1 initial={{ opacity: 0, y: 14, filter: 'blur(8px)' }} animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }} transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }} style={{ fontFamily: F.display, fontSize: 40, color: C.espresso, fontWeight: 600, margin: 0 }}>{title}</motion.h1>
          {subtitle && <p style={{ fontFamily: F.ui, color: C.cocoa, marginTop: 6, marginBottom: 0, fontSize: 14 }}>{subtitle}</p>}
        </div>
        {actions}
      </div>
      <div style={{ marginTop: 28, display: 'flex', flexDirection: 'column', gap: 20 }}>{children}</div>
    </div>
  );
}

export function Card({ title, right, children, pad = 24, style, delay = 0 }: { title?: ReactNode; right?: ReactNode; children: ReactNode; pad?: number; style?: CSSProperties; delay?: number }) {
  return (
    <motion.div initial={{ opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: '-30px' }} transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1], delay }} style={{ background: C.ivory, border: `1px solid ${C.line}`, borderRadius: 14, boxShadow: '0 1px 2px rgba(28,37,65,.04), 0 8px 24px rgba(28,37,65,.06)', overflow: 'hidden', ...style }}>
      {title && (
        <div style={{ padding: '14px 24px', borderBottom: `1px solid ${C.line}`, display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontFamily: F.ui, fontWeight: 600, color: C.espresso, fontSize: 15, flex: 1 }}>{title}</span>
          {right}
        </div>
      )}
      <div style={{ padding: pad }}>{children}</div>
    </motion.div>
  );
}

export function CountUp({ to, format = (v: number) => Math.round(v).toLocaleString('en-IN'), duration = 1.2 }: { to: number; format?: (v: number) => string; duration?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  useEffect(() => {
    if (!inView || !ref.current) return;
    const c = animate(0, to, { duration, ease: [0.22, 1, 0.36, 1], onUpdate: v => { if (ref.current) ref.current.textContent = format(v); } });
    return () => c.stop();
  }, [inView, to]);
  return <span ref={ref}>{format(0)}</span>;
}

export function Stat({ label, value, color }: { label: string; value: ReactNode; color?: string }) {
  return (
    <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }} whileHover={{ y: -3 }} style={{ background: C.ivory, border: `1px solid ${C.line}`, borderRadius: 14, padding: 20 }}>
      <div style={{ fontFamily: F.ui, fontSize: 12, color: C.cocoa, fontWeight: 500 }}>{label}</div>
      <div style={{ fontFamily: F.display, fontSize: 28, fontWeight: 600, color: color ?? C.espresso, marginTop: 6 }}>{typeof value === 'number' ? <CountUp to={value} /> : value}</div>
    </motion.div>
  );
}

export function Grid({ cols, children, gap = 16 }: { cols: number; children: ReactNode; gap?: number }) {
  return <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`, gap }}>{children}</div>;
}

const RISK: Record<string, { background: string; color: string }> = {
  high: { background: '#FFE7DE', color: C.terracotta },
  medium: { background: '#FCEED6', color: C.ochre },
  low: { background: '#DCF0EA', color: C.olive },
  none: { background: '#ECEBF6', color: C.stone },
};
export function RiskBadge({ level, score }: { level: string; score?: number | null }) {
  const s = RISK[level] ?? RISK.none;
  return (
    <span style={{ ...s, padding: '2px 10px', borderRadius: 999, fontSize: 12, fontWeight: 700, fontFamily: F.ui, whiteSpace: 'nowrap' }}>
      {level.toUpperCase()}{score != null ? ` · ${score}` : ''}
    </span>
  );
}

export function TypChip({ t }: { t: Typology | string }) {
  return (
    <span style={{ background: C.goldSoft, color: '#4677D2', padding: '2px 10px', borderRadius: 10, fontSize: 12, fontWeight: 600, fontFamily: F.ui, whiteSpace: 'nowrap' }}>
      {TYPOLOGY_LABELS[t as Typology] ?? t}
    </span>
  );
}

export function Btn({ children, onClick, disabled, kind = 'primary', type = 'button' }: { children: ReactNode; onClick?: () => void; disabled?: boolean; kind?: 'primary' | 'ghost'; type?: 'button' | 'submit' }) {
  const primary = kind === 'primary';
  return (
    <button type={type} onClick={onClick} disabled={disabled} style={{
      background: primary ? C.gold : C.ivory, color: primary ? C.ivory : C.espresso,
      border: primary ? 'none' : `1px solid ${C.line}`, borderRadius: 10, padding: '10px 20px',
      fontFamily: F.ui, fontWeight: 600, fontSize: 14, cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.6 : 1,
    }}>{children}</button>
  );
}

export const th: CSSProperties = { padding: '10px 14px', textAlign: 'left', fontFamily: F.ui, fontSize: 12, fontWeight: 600, color: C.cocoa, background: C.sand, position: 'sticky', top: 0, whiteSpace: 'nowrap' };
export const td: CSSProperties = { padding: '10px 14px', fontFamily: F.ui, fontSize: 13, color: C.espresso, borderTop: `1px solid ${C.line}`, verticalAlign: 'top' };
export const mono: CSSProperties = { ...td, fontFamily: F.mono };
export const num: CSSProperties = { ...mono, textAlign: 'right', whiteSpace: 'nowrap' };

export function AccountLink({ id }: { id: string }) {
  return <Link to={`/accounts/${encodeURIComponent(id)}`} style={{ color: C.slate, fontFamily: F.mono, fontSize: 13, textDecoration: 'none' }}>{id}</Link>;
}

export function Loading({ what = 'data' }: { what?: string }) {
  return <div style={{ padding: 32, fontFamily: F.ui, color: C.cocoa }}>Loading {what}…</div>;
}

export function ErrorState({ error, status, onRetry }: { error: string; status: number | null; onRetry: () => void }) {
  const [busy, setBusy] = useState(false);
  const noRun = status === 409;
  async function load() {
    setBusy(true);
    try { await loadSample(); onRetry(); } catch { /* shown by retry */ } finally { setBusy(false); }
  }
  return (
    <div style={{ padding: 32 }}>
      <Card style={{ maxWidth: 520 }}>
        <h2 style={{ fontFamily: F.display, fontSize: 26, color: C.espresso, fontWeight: 600, margin: 0 }}>{noRun ? 'No analysis yet' : 'Something went wrong'}</h2>
        <p style={{ fontFamily: F.ui, color: C.cocoa, marginTop: 8 }}>{noRun ? 'Load the sample dataset or upload a CSV to start.' : error}</p>
        <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
          {noRun && <Btn onClick={load} disabled={busy}>{busy ? 'Loading…' : 'Load sample dataset'}</Btn>}
          <Btn kind="ghost" onClick={onRetry}>Retry</Btn>
        </div>
      </Card>
    </div>
  );
}

export function pct(v: number | null | undefined) {
  return v == null ? '—' : `${(v * 100).toFixed(1)}%`;
}
