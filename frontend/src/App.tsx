import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Activity, Upload, List, GitBranch, Layers, Shield, BarChart2 } from 'lucide-react';
import OverviewPage from './pages/Overview';
import GraphExplorerPage from './pages/GraphExplorer';

function Landing() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: '#FBF6EC' }}>
      <h1 style={{ fontFamily: 'Fraunces, serif', fontSize: 64, color: '#2A1F16', fontWeight: 600, lineHeight: 1.1, textAlign: 'center' }}>
        Follow the thread.<br />Find the ring.
      </h1>
      <p style={{ fontFamily: 'Manrope, sans-serif', fontSize: 20, color: '#6B5A48', marginTop: 24, maxWidth: 540, textAlign: 'center' }}>
        Graph intelligence that exposes layered money-laundering networks that single-transaction rules miss.
      </p>
      <a href="/dashboard" style={{ marginTop: 40, background: '#B8862F', color: '#FFFDF8', fontFamily: 'Manrope, sans-serif', fontWeight: 600, fontSize: 16, padding: '14px 36px', borderRadius: 10, textDecoration: 'none' }}>
        Open investigation workspace →
      </a>
    </div>
  );
}

function PageShell({ title }: { title: string }) {
  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ fontFamily: 'Fraunces, serif', fontSize: 40, color: '#2A1F16', fontWeight: 600 }}>{title}</h1>
      <p style={{ fontFamily: 'Manrope, sans-serif', color: '#6B5A48', marginTop: 8 }}>Coming soon…</p>
    </div>
  );
}

function Overview() { return <OverviewPage />; }
function UploadPage() { return <PageShell title="Upload Data" />; }
function Transactions() { return <PageShell title="Transactions" />; }
function GraphExplorer() { return <GraphExplorerPage />; }
function Clusters() { return <PageShell title="Clusters" />; }
function ClusterDetail() { return <PageShell title="Cluster Investigation" />; }
function AccountDetail() { return <PageShell title="Account" />; }
function RiskTypology() { return <PageShell title="Risk & Typology" />; }
function Evaluation() { return <PageShell title="Evaluation" />; }

const NAV = [
  { to: '/dashboard', icon: <Activity size={18} />, label: 'Overview' },
  { to: '/upload', icon: <Upload size={18} />, label: 'Upload data' },
  { to: '/transactions', icon: <List size={18} />, label: 'Transactions' },
  { to: '/graph', icon: <GitBranch size={18} />, label: 'Graph explorer' },
  { to: '/clusters', icon: <Layers size={18} />, label: 'Clusters' },
  { to: '/risk', icon: <Shield size={18} />, label: 'Risk & typology' },
  { to: '/evaluation', icon: <BarChart2 size={18} />, label: 'Evaluation' },
];

function AppLayout() {
  const location = useLocation();
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#FBF6EC' }}>
      <aside style={{ width: 248, background: '#FFFDF8', borderRight: '1px solid #E7DAC3', display: 'flex', flexDirection: 'column', padding: '24px 0' }}>
        <div style={{ padding: '0 24px 24px', borderBottom: '1px solid #E7DAC3' }}>
          <span style={{ fontFamily: 'Fraunces, serif', fontSize: 22, fontWeight: 600, color: '#2A1F16' }}>FinThread</span>
          <div style={{ height: 2, background: '#B8862F', width: 48, marginTop: 4, borderRadius: 2 }} />
        </div>
        <nav style={{ marginTop: 16, flex: 1 }}>
          {NAV.map(function(item) {
            return (
              <NavLink key={item.to} to={item.to} style={function(props) {
                return {
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '10px 24px',
                  textDecoration: 'none',
                  fontFamily: 'Manrope, sans-serif',
                  fontSize: 14,
                  fontWeight: props.isActive ? 600 : 400,
                  color: props.isActive ? '#B8862F' : '#6B5A48',
                  background: props.isActive ? '#F3E2BC' : 'transparent',
                  borderRight: props.isActive ? '3px solid #B8862F' : '3px solid transparent',
                };
              }}>
                {item.icon}{item.label}
              </NavLink>
            );
          })}
        </nav>
      </aside>

      <main style={{ flex: 1, overflow: 'auto' }}>
        <div style={{ height: 56, background: '#FFFDF8', borderBottom: '1px solid #E7DAC3', display: 'flex', alignItems: 'center', padding: '0 32px', gap: 16 }}>
          <span style={{ fontFamily: 'Manrope, sans-serif', fontSize: 14, color: '#6B5A48' }}>FinThread — AML Investigation Platform</span>
          <div style={{ marginLeft: 'auto', width: 8, height: 8, borderRadius: '50%', background: '#5E7F4F' }} />
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
          >
            <Routes location={location}>
              <Route path="/dashboard" element={<Overview />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/transactions" element={<Transactions />} />
              <Route path="/graph" element={<GraphExplorer />} />
              <Route path="/clusters" element={<Clusters />} />
              <Route path="/clusters/:clusterId" element={<ClusterDetail />} />
              <Route path="/accounts/:accountId" element={<AccountDetail />} />
              <Route path="/risk" element={<RiskTypology />} />
              <Route path="/evaluation" element={<Evaluation />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
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