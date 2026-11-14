import { useEffect, useRef, useState } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom';
import { AnimatePresence, LayoutGroup, motion } from 'framer-motion';
import { Activity, Upload, List, GitBranch, Layers, Shield, BarChart2, ArrowUpRight } from 'lucide-react';
import OverviewPage from './pages/Overview';
import GraphExplorerPage from './pages/GraphExplorer';
import UploadPageImpl from './pages/Upload';
import TransactionsPage from './pages/Transactions';
import ClustersPage from './pages/Clusters';
import ClusterDetailPage from './pages/ClusterDetail';
import AccountDetailPage from './pages/AccountDetail';
import RiskTypologyPage from './pages/RiskTypology';
import EvaluationPage from './pages/Evaluation';
import Landing from './pages/Landing';
import { getHealth } from './api/endpoints';

const T = {
  cream: '#E9E8F8', ivory: '#F8F8FD', line: '#D5D4EC', ink: '#1C2541', muted: '#585F7E',
  teal: '#4677D2', tealSoft: '#DCE7FB', coral: '#FF9475',
};
const ease = [0.22, 1, 0.36, 1] as const;

const GROUPS: { title: string; items: { to: string; icon: typeof Activity; label: string; hint: string }[] }[] = [
  { title: 'Investigate', items: [
    { to: '/dashboard', icon: Activity, label: 'Overview', hint: 'Alerts & key numbers' },
    { to: '/graph', icon: GitBranch, label: 'Graph explorer', hint: 'The money web' },
    { to: '/clusters', icon: Layers, label: 'Clusters', hint: 'Rings ranked by risk' },
  ] },
  { title: 'Analyse', items: [
    { to: '/evaluation', icon: BarChart2, label: 'Evaluation', hint: 'Graph vs rules' },
    { to: '/risk', icon: Shield, label: 'Risk & typology', hint: 'How scores work' },
  ] },
  { title: 'Data', items: [
    { to: '/transactions', icon: List, label: 'Transactions', hint: 'Every transfer' },
    { to: '/upload', icon: Upload, label: 'Upload data', hint: 'Bring your CSV' },
  ] },
];
const ORDER = GROUPS.flatMap(g => g.items.map(i => i.to));
const orderOf = (path: string) => {
  if (path.startsWith('/accounts')) return ORDER.indexOf('/clusters') + 0.5;
  const i = ORDER.findIndex(to => path === to || (to !== '/dashboard' && path.startsWith(to)));
  return i < 0 ? 0 : i + (path.split('/').length > 2 ? 0.5 : 0);
};

const TITLES: [RegExp, string][] = [
  [/^\/dashboard/, 'Overview'], [/^\/graph/, 'Graph explorer'], [/^\/clusters\/.+/, 'Investigation'], [/^\/clusters/, 'Clusters'],
  [/^\/evaluation/, 'Evaluation'], [/^\/transactions/, 'Transactions'], [/^\/risk/, 'Risk & typology'], [/^\/upload/, 'Upload data'], [/^\/accounts/, 'Account'],
];

export function LogoMark({ size = 28, light }: { size?: number; light?: boolean }) {
  const c = light ? T.cream : T.teal;
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" aria-hidden="true">
      <path d="M6 14L22 6M6 14L22 22M22 6L22 22" stroke={c} strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="6" cy="14" r="3.6" fill={c} /><circle cx="22" cy="6" r="3.6" fill={c} /><circle cx="22" cy="22" r="3.6" fill={T.coral} />
    </svg>
  );
}

function Sidebar() {
  const location = useLocation();
  let k = 0;
  return (
    <aside style={{ width: 264, flexShrink: 0, background: 'linear-gradient(180deg, #7FA9EC 0%, #5383D6 100%)', display: 'flex', flexDirection: 'column', padding: '26px 16px 20px', position: 'sticky', top: 0, height: '100vh' }}>
      <NavLink to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 10px', textDecoration: 'none' }}>
        <LogoMark light />
        <span style={{ fontFamily: 'Fraunces, serif', fontSize: 23, fontWeight: 600, color: T.cream }}>FinThread</span>
      </NavLink>
      <LayoutGroup id="sidebar">
        <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-evenly', padding: '18px 0' }}>
          {GROUPS.map(g => (
            <div key={g.title}>
              <div style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 10.5, letterSpacing: '.12em', textTransform: 'uppercase', color: 'rgba(255,255,255,.42)', padding: '0 12px 8px' }}>{g.title}</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {g.items.map(({ to, icon: Icon, label, hint }) => {
                  const i = k++;
                  const active = location.pathname === to || (to !== '/dashboard' && location.pathname.startsWith(to));
                  return (
                    <motion.div key={to} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.45, ease, delay: 0.04 * i }}>
                      <NavLink to={to} className={active ? undefined : 'ft-nav'} style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: 12, padding: '11px 12px', borderRadius: 14, textDecoration: 'none', fontFamily: 'Manrope, sans-serif' }}>
                        {active && <motion.span layoutId="navPill" transition={{ type: 'spring', stiffness: 380, damping: 34 }} style={{ position: 'absolute', inset: 0, borderRadius: 14, background: T.cream, boxShadow: '0 8px 22px rgba(0,0,0,.18)' }} />}
                        <span style={{ position: 'relative', width: 34, height: 34, borderRadius: 10, display: 'grid', placeItems: 'center', background: active ? T.teal : 'rgba(255,255,255,.07)', color: active ? T.cream : 'rgba(255,255,255,.8)', transition: 'background .3s' }}><Icon size={17} /></span>
                        <span style={{ position: 'relative', flex: 1, minWidth: 0 }}>
                          <span style={{ display: 'block', fontSize: 14, fontWeight: 700, color: active ? T.ink : 'rgba(255,255,255,.9)' }}>{label}</span>
                          <span style={{ display: 'block', fontSize: 11.5, color: active ? T.muted : 'rgba(255,255,255,.45)', marginTop: 1 }}>{hint}</span>
                        </span>
                        {active && <motion.span layoutId="navDot" style={{ position: 'relative', width: 7, height: 7, borderRadius: 4, background: T.coral }} />}
                      </NavLink>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </LayoutGroup>
      <NavLink to="/" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 12px', borderRadius: 12, border: '1px solid rgba(255,255,255,.14)', textDecoration: 'none', fontFamily: 'Manrope, sans-serif', fontSize: 12.5, color: 'rgba(255,255,255,.75)' }}>
        <ArrowUpRight size={15} /> Back to intro
      </NavLink>
    </aside>
  );
}

function Topbar() {
  const location = useLocation();
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => { getHealth().then(h => setOk(h.dataset_loaded)).catch(() => setOk(false)); }, []);
  const title = TITLES.find(([r]) => r.test(location.pathname))?.[1] ?? '';
  return (
    <div style={{ height: 60, position: 'sticky', top: 0, zIndex: 20, background: 'rgba(255,255,255,.78)', backdropFilter: 'blur(14px)', borderBottom: `1px solid ${T.line}`, display: 'flex', alignItems: 'center', padding: '0 32px', gap: 14 }}>
      <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 12, color: T.muted }}>Workspace /</span>
      <div style={{ position: 'relative', height: 22, overflow: 'hidden', minWidth: 200 }}>
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.span key={title} initial={{ y: 22, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: -22, opacity: 0 }} transition={{ duration: 0.35, ease }}
            style={{ position: 'absolute', fontFamily: 'Manrope, sans-serif', fontSize: 14, fontWeight: 700, color: T.ink, whiteSpace: 'nowrap' }}>{title}</motion.span>
        </AnimatePresence>
      </div>
      <div style={{ flex: 1 }} />
      <span style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'Manrope, sans-serif', fontSize: 12, color: T.muted }}>
        <span style={{ position: 'relative', width: 8, height: 8 }}>
          <span style={{ position: 'absolute', inset: 0, borderRadius: 4, background: ok ? '#3B9A84' : ok === false ? T.coral : T.line }} />
          {ok && <motion.span animate={{ scale: [1, 2.4], opacity: [0.5, 0] }} transition={{ duration: 1.8, repeat: Infinity }} style={{ position: 'absolute', inset: 0, borderRadius: 4, background: '#3B9A84' }} />}
        </span>
        {ok ? 'Live data' : ok === false ? 'Backend waking up…' : 'Connecting…'}
      </span>
      <NavLink to="/" style={{ display: 'flex', alignItems: 'center', gap: 4, fontFamily: 'Manrope, sans-serif', fontSize: 12, fontWeight: 600, color: T.teal, textDecoration: 'none' }}>Home <ArrowUpRight size={14} /></NavLink>
    </div>
  );
}

const glide = {
  enter: (d: number) => ({ y: d * 90, opacity: 0, scale: 0.985 }),
  center: { y: 0, opacity: 1, scale: 1 },
  exit: (d: number) => ({ y: d * -90, opacity: 0, scale: 0.985 }),
};

function AppLayout() {
  const location = useLocation();
  const fromLanding = (location.state as { fromLanding?: boolean } | null)?.fromLanding;
  const idx = orderOf(location.pathname);
  const prev = useRef(idx);
  const dir = idx === prev.current ? 1 : idx > prev.current ? 1 : -1;
  useEffect(() => { prev.current = idx; window.scrollTo({ top: 0 }); }, [idx]);
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: T.cream }}>
      {fromLanding && (
        <motion.div initial={{ opacity: 1 }} animate={{ opacity: 0 }} transition={{ duration: 0.7, ease, delay: 0.15 }}
          style={{ position: 'fixed', inset: 0, zIndex: 100, background: 'linear-gradient(180deg, #E9E8F8, #8DB9F0)', pointerEvents: 'none' }} />
      )}
      <Sidebar />
      <main style={{ flex: 1, minWidth: 0, position: 'relative' }}>
        <Topbar />
        <div style={{ position: 'relative', overflow: 'hidden', minHeight: 'calc(100vh - 60px)' }}>
          <AnimatePresence mode="popLayout" custom={dir} initial={false}>
            <motion.div
              key={location.pathname}
              custom={dir}
              variants={glide}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ y: { type: 'spring', stiffness: 170, damping: 26, mass: 0.9 }, opacity: { duration: 0.35 }, scale: { duration: 0.5, ease } }}
              style={{ width: '100%' }}
            >
              <Routes location={location}>
                <Route path="/dashboard" element={<OverviewPage />} />
                <Route path="/upload" element={<UploadPageImpl />} />
                <Route path="/transactions" element={<TransactionsPage />} />
                <Route path="/graph" element={<GraphExplorerPage />} />
                <Route path="/clusters" element={<ClustersPage />} />
                <Route path="/clusters/:clusterId" element={<ClusterDetailPage />} />
                <Route path="/accounts/:accountId" element={<AccountDetailPage />} />
                <Route path="/risk" element={<RiskTypologyPage />} />
                <Route path="/evaluation" element={<EvaluationPage />} />
              </Routes>
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/*" element={<AppLayout />} />
      </Routes>
    </BrowserRouter>
  );
}
