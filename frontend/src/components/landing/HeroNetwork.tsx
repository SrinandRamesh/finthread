import { useEffect, useRef } from 'react';

type Node3 = { x: number; y: number; z: number; ring: number; seed: number };
type Edge = [number, number];
type Spark = { e: number; t: number; speed: number; dir: 1 | -1 };
type Flare = { n: number; t: number };

// colour where the background is light lavender (top) and where it is powder blue (bottom)
const TOP = { node: [24, 34, 78], edge: [30, 42, 96] };
const BOTTOM = { node: [22, 44, 120], edge: [24, 46, 124] };
const PEACH = [255, 128, 92];
const PEACH_GLOW = '255,182,158';

function fib(n: number): Node3[] {
  const pts: Node3[] = [];
  const phi = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    const t = phi * i;
    const j = 0.88 + 0.2 * Math.abs((Math.sin(i * 12.9898) * 43758.5453) % 1);
    pts.push({ x: Math.cos(t) * r * j, y: y * j, z: Math.sin(t) * r * j, ring: -1, seed: Math.random() * 10 });
  }
  return pts;
}

const smooth = (a: number, b: number, x: number) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

/**
 * Rotating 3D account network on a lavender → powder-blue gradient.
 * Colours blend smoothly with height. Threads, glowing peach laundering rings, money pulses,
 * sparks, flaring nodes and an orbiting satellite ring.
 */
export default function HeroNetwork({ cx = 0.7, cy = 0.52, size = 0.3, blendFrom = 0.35, blendTo = 0.85 }: { cx?: number; cy?: number; size?: number; blendFrom?: number; blendTo?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const opts = useRef({ cx, cy, size, blendFrom, blendTo });
  opts.current = { cx, cy, size, blendFrom, blendTo };

  useEffect(() => {
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext('2d')!;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const nodes = fib(200);

    const edges: Edge[] = [];
    for (let i = 0; i < nodes.length; i++) {
      const d: [number, number][] = [];
      for (let j = 0; j < nodes.length; j++) {
        if (i === j) continue;
        const a = nodes[i], b = nodes[j];
        d.push([j, (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2]);
      }
      d.sort((p, q) => p[1] - q[1]);
      d.slice(0, 3).forEach(([j]) => { if (i < j) edges.push([i, j]); });
    }

    const rings: number[][] = [];
    const used = new Set<number>();
    [9, 37, 66, 95, 121, 150, 178].forEach((s, ri) => {
      if (used.has(s)) return;
      const chain = [s]; used.add(s);
      for (let k = 0; k < 4; k++) {
        const last = chain[chain.length - 1];
        const next = edges.filter(e => e[0] === last || e[1] === last).map(e => (e[0] === last ? e[1] : e[0])).find(n => !used.has(n));
        if (next == null) break;
        chain.push(next); used.add(next);
      }
      chain.forEach(n => (nodes[n].ring = ri));
      rings.push(chain);
    });

    let w = 0, h = 0;
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.clientWidth; h = canvas.clientHeight;
      canvas.width = w * dpr; canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    const ro = new ResizeObserver(resize); ro.observe(canvas);

    let mx = 0, my = 0;
    const onMove = (e: PointerEvent) => {
      const r = canvas.getBoundingClientRect();
      mx = ((e.clientX - r.left) / r.width - 0.5) * 2;
      my = ((e.clientY - r.top) / r.height - 0.5) * 2;
    };
    window.addEventListener('pointermove', onMove);

    const sparks: Spark[] = [];
    const flares: Flare[] = [];
    let rot = 0, tiltX = 0, tiltY = 0, raf = 0, lastSpark = 0, lastFlare = 0;
    const t0 = performance.now();
    const mix = (a: number[], b: number[], k: number) => [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k];
    const rgba = (c: number[], a: number) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`;

    function frame(now: number) {
      const t = Math.max(0, (now - t0) / 1000);
      const o = opts.current;
      if (!reduce) rot += 0.0045;
      tiltX += (my * 0.35 - tiltX) * 0.06;
      tiltY += (mx * 0.5 - tiltY) * 0.06;
      const breathe = 1 + Math.sin(t * 0.9) * 0.025;

      ctx.clearRect(0, 0, w, h);
      const R = Math.min(w, h * 1.4) * o.size * breathe;
      const cxp = w * o.cx, cyp = h * o.cy;
      const cr = Math.cos(rot + tiltY), sr = Math.sin(rot + tiltY);
      const ct = Math.cos(tiltX + 0.25), st = Math.sin(tiltX + 0.25);
      const k = (y: number) => smooth(h * o.blendFrom, h * o.blendTo, y);

      const project = (x: number, y: number, z: number) => {
        const x1 = x * cr - z * sr, z1 = x * sr + z * cr;
        const y1 = y * ct - z1 * st, z2 = y * st + z1 * ct;
        const s = 2.6 / (2.6 + z2);
        return { x: cxp + x1 * R * s, y: cyp + y1 * R * s, z: z2, s };
      };
      const P = nodes.map(n => project(n.x, n.y, n.z));

      // soft halo behind the globe
      const halo = ctx.createRadialGradient(cxp, cyp, R * 0.2, cxp, cyp, R * 1.35);
      halo.addColorStop(0, 'rgba(255,255,255,0.35)');
      halo.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.fillStyle = halo; ctx.beginPath(); ctx.arc(cxp, cyp, R * 1.35, 0, Math.PI * 2); ctx.fill();

      // orbit ring (back half) + satellite
      const orbit: { x: number; y: number; z: number }[] = [];
      for (let a = 0; a <= 64; a++) {
        const ang = (a / 64) * Math.PI * 2;
        orbit.push(project(Math.cos(ang) * 1.32, Math.sin(ang) * 0.18, Math.sin(ang) * 1.32));
      }
      const drawOrbit = (front: boolean) => {
        ctx.lineWidth = 1.2;
        for (let a = 0; a < 64; a++) {
          const p = orbit[a], q = orbit[a + 1];
          if ((p.z < 0) !== front) continue;
          ctx.strokeStyle = rgba(mix(TOP.edge, BOTTOM.edge, k(p.y)), front ? 0.55 : 0.25);
          ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke();
        }
      };
      drawOrbit(false);

      // threads
      for (const [a, b] of edges) {
        const depth = (2 - (P[a].z + P[b].z)) / 4;
        const inRing = nodes[a].ring >= 0 && nodes[a].ring === nodes[b].ring;
        const kk = k((P[a].y + P[b].y) / 2);
        if (inRing) {
          ctx.strokeStyle = rgba(PEACH, 0.95); ctx.lineWidth = 2.4;
        } else {
          ctx.strokeStyle = rgba(mix(TOP.edge, BOTTOM.edge, kk), 0.32 + 0.45 * depth);
          ctx.lineWidth = 0.7 + 0.8 * depth;
        }
        ctx.beginPath(); ctx.moveTo(P[a].x, P[a].y); ctx.lineTo(P[b].x, P[b].y); ctx.stroke();
      }

      // money pulses along the rings
      rings.forEach((chain, ri) => {
        if (chain.length < 2) return;
        for (let q = 0; q < 2; q++) {
          const raw = (t * (0.5 + ri * 0.06) + ri * 0.37 + q * 0.5) % 1;
          const pos = raw * (chain.length - 1);
          const i = Math.floor(pos), f = pos - i;
          const a = P[chain[i]], b = P[chain[Math.min(i + 1, chain.length - 1)]];
          const x = a.x + (b.x - a.x) * f, y = a.y + (b.y - a.y) * f;
          const g = ctx.createRadialGradient(x, y, 0, x, y, 18);
          g.addColorStop(0, `rgba(${PEACH_GLOW},1)`); g.addColorStop(0.35, `rgba(${PEACH_GLOW},.55)`); g.addColorStop(1, `rgba(${PEACH_GLOW},0)`);
          ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, 18, 0, Math.PI * 2); ctx.fill();
          ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(x, y, 2.6, 0, Math.PI * 2); ctx.fill();
        }
      });

      // sparks: transfers racing along random threads, with a short tail
      if (now - lastSpark > 55 && !reduce) {
        lastSpark = now;
        sparks.push({ e: Math.floor(Math.random() * edges.length), t: 0, speed: 0.02 + Math.random() * 0.03, dir: Math.random() > 0.5 ? 1 : -1 });
        if (sparks.length > 50) sparks.shift();
      }
      for (const s of sparks) {
        s.t += s.speed;
        if (s.t > 1) continue;
        const [a, b] = edges[s.e];
        const A = s.dir === 1 ? P[a] : P[b], B = s.dir === 1 ? P[b] : P[a];
        const x = A.x + (B.x - A.x) * s.t, y = A.y + (B.y - A.y) * s.t;
        const tx = A.x + (B.x - A.x) * Math.max(0, s.t - 0.25), ty = A.y + (B.y - A.y) * Math.max(0, s.t - 0.25);
        const col = mix([40, 70, 190], [255, 255, 255], k(y) * 0.6);
        const al = Math.sin(s.t * Math.PI);
        const grad = ctx.createLinearGradient(tx, ty, x, y);
        grad.addColorStop(0, rgba(col, 0)); grad.addColorStop(1, rgba(col, 0.9 * al));
        ctx.strokeStyle = grad; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(tx, ty); ctx.lineTo(x, y); ctx.stroke();
        ctx.fillStyle = rgba(col, al); ctx.beginPath(); ctx.arc(x, y, 2, 0, Math.PI * 2); ctx.fill();
      }

      // random nodes flare
      if (now - lastFlare > 260 && !reduce) {
        lastFlare = now;
        flares.push({ n: Math.floor(Math.random() * nodes.length), t: 0 });
        if (flares.length > 10) flares.shift();
      }

      // nodes back to front
      const order = P.map((_, i) => i).sort((a, b) => P[b].z - P[a].z);
      for (const i of order) {
        const p = P[i], n = nodes[i];
        const depth = (1 - p.z) / 2;
        const kk = k(p.y);
        const tw = 0.85 + 0.15 * Math.sin(t * 3 + n.seed * 4);
        let col = mix(TOP.node, BOTTOM.node, kk);
        let r = (1.8 + 2 * p.s * depth) * tw;
        let alpha = 0.6 + 0.4 * depth;
        if (n.ring >= 0) { col = PEACH; r += 2; alpha = 1; }
        ctx.fillStyle = rgba(col, alpha);
        ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI * 2); ctx.fill();
        if (n.ring >= 0) {
          const ph = (t * 1.4 + n.seed) % 1;
          ctx.strokeStyle = rgba(PEACH, 0.45 * (1 - ph)); ctx.lineWidth = 1.4;
          ctx.beginPath(); ctx.arc(p.x, p.y, r + 3 + ph * 10, 0, Math.PI * 2); ctx.stroke();
        }
      }

      for (const f of flares) {
        f.t += 0.025;
        if (f.t > 1) continue;
        const p = P[f.n];
        if (p.z > 0.3) continue;
        const a = Math.sin(f.t * Math.PI);
        const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, 22 * a + 4);
        g.addColorStop(0, `rgba(255,255,255,${0.95 * a})`); g.addColorStop(0.4, `rgba(${PEACH_GLOW},${0.5 * a})`); g.addColorStop(1, `rgba(${PEACH_GLOW},0)`);
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(p.x, p.y, 22 * a + 4, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = `rgba(255,255,255,${0.85 * a})`; ctx.lineWidth = 1.2;
        const L = 14 * a;
        ctx.beginPath(); ctx.moveTo(p.x - L, p.y); ctx.lineTo(p.x + L, p.y); ctx.moveTo(p.x, p.y - L); ctx.lineTo(p.x, p.y + L); ctx.stroke();
      }

      drawOrbit(true);
      const sa = t * 0.7;
      const sat = project(Math.cos(sa) * 1.32, Math.sin(sa) * 0.18, Math.sin(sa) * 1.32);
      const sg = ctx.createRadialGradient(sat.x, sat.y, 0, sat.x, sat.y, 14);
      sg.addColorStop(0, `rgba(${PEACH_GLOW},1)`); sg.addColorStop(1, `rgba(${PEACH_GLOW},0)`);
      ctx.fillStyle = sg; ctx.beginPath(); ctx.arc(sat.x, sat.y, 14, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = rgba(PEACH, 1); ctx.beginPath(); ctx.arc(sat.x, sat.y, 4 * sat.s, 0, Math.PI * 2); ctx.fill();

      raf = requestAnimationFrame(frame);
    }
    raf = requestAnimationFrame(frame);
    return () => { cancelAnimationFrame(raf); ro.disconnect(); window.removeEventListener('pointermove', onMove); };
  }, []);

  return <canvas ref={canvasRef} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} aria-hidden="true" />;
}
