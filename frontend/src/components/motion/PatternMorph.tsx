import { useEffect, useRef } from 'react';

const N = 760;

type Shape = { nodes: [number, number][]; edges: [number, number][]; hot: number[] };

export const MORPH_SHAPES: Shape[] = [
  // 0 fan-in
  { nodes: [[0.1, 0], [-0.8, -0.6], [-0.85, 0], [-0.8, 0.6], [-0.3, -0.85], [-0.3, 0.85], [0.85, 0]], edges: [[1, 0], [2, 0], [3, 0], [4, 0], [5, 0], [0, 6]], hot: [0] },
  // 1 fan-out
  { nodes: [[-0.1, 0], [0.75, -0.65], [0.85, -0.2], [0.85, 0.25], [0.75, 0.68], [0.3, -0.85], [0.3, 0.85], [-0.85, 0]], edges: [[7, 0], [0, 1], [0, 2], [0, 3], [0, 4], [0, 5], [0, 6]], hot: [0] },
  // 2 cycle
  { nodes: [[0, -0.78], [0.74, -0.24], [0.46, 0.63], [-0.46, 0.63], [-0.74, -0.24]], edges: [[0, 1], [1, 2], [2, 3], [3, 4], [4, 0]], hot: [0] },
  // 3 pass-through
  { nodes: [[-0.9, 0.3], [-0.55, -0.28], [-0.18, 0.3], [0.18, -0.3], [0.55, 0.28], [0.9, -0.3]], edges: [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5]], hot: [0, 5] },
  // 4 scatter-gather
  { nodes: [[-0.85, 0], [-0.1, -0.7], [-0.1, -0.25], [-0.1, 0.25], [-0.1, 0.7], [0.85, 0]], edges: [[0, 1], [0, 2], [0, 3], [0, 4], [1, 5], [2, 5], [3, 5], [4, 5]], hot: [0, 5] },
];

function targets(shape: Shape) {
  const pts: { x: number; y: number; hot: boolean }[] = [];
  const per = Math.floor((N * 0.42) / shape.nodes.length);
  shape.nodes.forEach(([x, y], i) => {
    const big = shape.hot.includes(i);
    const r = big ? 0.12 : 0.07;
    for (let k = 0; k < per; k++) {
      const a = Math.random() * Math.PI * 2, d = Math.sqrt(Math.random()) * r;
      pts.push({ x: x + Math.cos(a) * d, y: y + Math.sin(a) * d, hot: big });
    }
  });
  const rest = N - pts.length;
  for (let k = 0; k < rest; k++) {
    const [a, b] = shape.edges[k % shape.edges.length];
    const [x1, y1] = shape.nodes[a], [x2, y2] = shape.nodes[b];
    const t = Math.random();
    pts.push({ x: x1 + (x2 - x1) * t + (Math.random() - 0.5) * 0.025, y: y1 + (y2 - y1) * t + (Math.random() - 0.5) * 0.025, hot: false });
  }
  return pts.sort(() => Math.random() - 0.5);
}

/** A particle cloud that morphs into the laundering pattern at `index`. Fills its parent. */
export default function PatternMorph({ index, scale = 0.42, light = false }: { index: number; scale?: number; light?: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const idx = useRef(index);
  idx.current = index;

  useEffect(() => {
    const canvas = ref.current!;
    const ctx = canvas.getContext('2d')!;
    const all = MORPH_SHAPES.map(targets);
    const P = Array.from({ length: N }, () => ({ x: (Math.random() - 0.5) * 2.4, y: (Math.random() - 0.5) * 1.6, hot: 0, ph: Math.random() * 6.28 }));
    const base = light ? [70, 119, 210] : [255, 255, 255];
    let w = 0, h = 0, raf = 0;
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.clientWidth; h = canvas.clientHeight;
      canvas.width = w * dpr; canvas.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    const ro = new ResizeObserver(resize); ro.observe(canvas);
    const t0 = performance.now();
    const loop = (now: number) => {
      const t = Math.max(0, (now - t0) / 1000);
      const tg = all[Math.min(all.length - 1, Math.max(0, idx.current))];
      const S = Math.min(w, h * 1.5) * scale, cx = w / 2, cy = h / 2;
      ctx.clearRect(0, 0, w, h);
      for (let i = 0; i < N; i++) {
        const p = P[i], g = tg[i];
        p.x += (g.x + Math.sin(t * 1.3 + p.ph) * 0.006 - p.x) * 0.07;
        p.y += (g.y + Math.cos(t * 1.1 + p.ph) * 0.006 - p.y) * 0.07;
        p.hot += ((g.hot ? 1 : 0) - p.hot) * 0.08;
        const r = 1.15 + p.hot * 1.25;
        const c0 = Math.round(base[0] + (255 - base[0]) * p.hot), c1 = Math.round(base[1] + (150 - base[1]) * p.hot), c2 = Math.round(base[2] + (118 - base[2]) * p.hot);
        ctx.fillStyle = `rgba(${c0},${c1},${c2},${0.55 + 0.45 * p.hot})`;
        ctx.beginPath(); ctx.arc(cx + p.x * S, cy + p.y * S, r, 0, 6.283); ctx.fill();
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => { cancelAnimationFrame(raf); ro.disconnect(); };
  }, [scale, light]);

  return <canvas ref={ref} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} aria-hidden="true" />;
}
