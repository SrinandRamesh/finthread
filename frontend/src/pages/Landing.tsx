import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import HeroNetwork from '../components/landing/HeroNetwork';

const C = {
  lavender: '#E9E8F8', powder: '#8DB9F0', peach: '#FFB69E', peachDeep: '#F2805E',
  navy: '#1C2541', muted: '#4E5878', blue: '#4A7FD6',
};
const F = { display: 'Fraunces, serif', ui: 'Manrope, sans-serif', mono: 'IBM Plex Mono, monospace' };
const ease = [0.22, 1, 0.36, 1] as const;

export default function Landing() {
  const nav = useNavigate();
  const [zoom, setZoom] = useState<{ x: number; y: number } | null>(null);

  function enter(e: React.MouseEvent) {
    e.preventDefault();
    setZoom({ x: e.clientX, y: e.clientY });
    setTimeout(() => nav('/dashboard', { state: { fromLanding: true } }), 650);
  }

  const R = typeof window !== 'undefined' ? Math.hypot(window.innerWidth, window.innerHeight) * 1.1 : 2000;
  const word = (w: string, i: number, base: number) => (
    <motion.span key={i} initial={{ opacity: 0, y: 36, filter: 'blur(10px)' }} animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }} transition={{ duration: 0.9, ease, delay: base + i * 0.08 }} style={{ display: 'inline-block', marginRight: '0.22em' }}>{w}</motion.span>
  );

  return (
    <div style={{
      position: 'relative', height: '100vh', minHeight: 640, overflow: 'hidden',
      background: `radial-gradient(ellipse 65% 42% at 12% 104%, rgba(255,190,165,.9) 0%, rgba(255,205,185,.45) 40%, rgba(255,182,158,0) 72%),
                   radial-gradient(ellipse 60% 40% at 95% 95%, rgba(255,182,158,.35) 0%, rgba(255,182,158,0) 70%),
                   linear-gradient(180deg, ${C.lavender} 0%, ${C.lavender} 28%, #C9D7F6 58%, ${C.powder} 100%)`,
    }}>
      <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 1.6, ease, delay: 0.3 }} style={{ position: 'absolute', inset: 0 }}>
        <HeroNetwork cx={0.735} cy={0.53} size={0.265} blendFrom={0.38} blendTo={0.9} />
      </motion.div>

      <div style={{ position: 'relative', zIndex: 2, height: '100%', padding: '30px 64px', display: 'flex', flexDirection: 'column', pointerEvents: 'none' }}>
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease }} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <svg width="30" height="30" viewBox="0 0 28 28" aria-hidden="true"><path d="M6 14L22 6M6 14L22 22M22 6L22 22" stroke={C.navy} strokeWidth="1.8" strokeLinecap="round" /><circle cx="6" cy="14" r="3.6" fill={C.navy} /><circle cx="22" cy="6" r="3.6" fill={C.blue} /><circle cx="22" cy="22" r="3.6" fill={C.peachDeep} /></svg>
          <span style={{ fontFamily: F.display, fontSize: 24, fontWeight: 600, color: C.navy }}>FinThread</span>
        </motion.div>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', maxWidth: 620, paddingBottom: 40 }}>
          <motion.span initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease, delay: 0.25 }}
            style={{ alignSelf: 'flex-start', display: 'inline-flex', alignItems: 'center', gap: 8, fontFamily: F.mono, fontSize: 11.5, letterSpacing: '.1em', textTransform: 'uppercase', color: C.navy, background: 'rgba(255,255,255,.65)', border: '1px solid rgba(28,37,65,.08)', padding: '6px 11px', borderRadius: 999 }}>
            <span style={{ width: 6, height: 6, borderRadius: 3, background: C.peachDeep }} />Graph intelligence for AML
          </motion.span>
          <h1 style={{ fontFamily: F.display, fontWeight: 600, fontSize: 'clamp(46px, 5.4vw, 92px)', lineHeight: 0.98, letterSpacing: '-0.02em', color: C.navy, margin: '20px 0 0' }}>
            <span style={{ display: 'block', whiteSpace: 'nowrap' }}>{['Follow', 'the', 'thread.'].map((w, i) => word(w, i, 0.35))}</span>
            <span style={{ display: 'block', fontStyle: 'italic', background: `linear-gradient(90deg, ${C.peachDeep}, #FF9C7E 60%, ${C.blue})`, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', paddingBottom: 6 }}>
              {['Find', 'the', 'ring.'].map((w, i) => word(w, i, 0.7))}
            </span>
          </h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.9, delay: 1.1 }}
            style={{ fontFamily: F.ui, fontSize: 17, lineHeight: 1.65, color: C.muted, maxWidth: 470, margin: '16px 0 0' }}>
            Scammers bounce stolen money through dozens of accounts. FinThread maps every transfer as a graph and exposes the whole ring.
          </motion.p>
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease, delay: 1.25 }} style={{ marginTop: 30, pointerEvents: 'auto', alignSelf: 'flex-start' }}>
            <motion.a href="/dashboard" onClick={enter} whileHover={{ y: -2, boxShadow: '0 18px 36px rgba(28,37,65,.28)' }} whileTap={{ scale: 0.97 }}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 12, fontFamily: F.ui, fontWeight: 700, fontSize: 15, color: '#fff', background: C.navy, padding: '16px 18px 16px 26px', borderRadius: 999, textDecoration: 'none', boxShadow: '0 12px 28px rgba(28,37,65,.22)' }}>
              Open investigation workspace
              <span style={{ width: 30, height: 30, borderRadius: 15, background: C.peach, color: C.navy, display: 'grid', placeItems: 'center', fontSize: 16 }}>→</span>
            </motion.a>
          </motion.div>
        </div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1, delay: 1.8 }}
          style={{ display: 'flex', alignItems: 'center', gap: 10, fontFamily: F.ui, fontSize: 12.5, color: C.navy, opacity: 0.75 }}>
          <span style={{ width: 22, height: 3, borderRadius: 2, background: C.peachDeep }} />
          Peach threads are laundering rings, caught as money moves.
        </motion.div>
      </div>

      {zoom && (
        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ duration: 0.7, ease }}
          style={{ position: 'fixed', zIndex: 200, left: zoom.x - R, top: zoom.y - R, width: R * 2, height: R * 2, borderRadius: '50%', background: `linear-gradient(180deg, ${C.lavender}, ${C.powder})`, pointerEvents: 'none' }} />
      )}
    </div>
  );
}
