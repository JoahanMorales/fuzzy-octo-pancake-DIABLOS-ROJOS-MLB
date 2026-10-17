/* Procedural canvas textures for the stadium (no image files, no photoreal assets). Built once per page. */
import * as THREE from 'three';

function canvas(w: number, h: number) {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  return { c, g: c.getContext('2d') };
}

function finish(c: HTMLCanvasElement, repeat: [number, number] = [1, 1], srgb = true): THREE.CanvasTexture {
  const t = new THREE.CanvasTexture(c);
  t.wrapS = THREE.RepeatWrapping;
  t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(repeat[0], repeat[1]);
  t.anisotropy = 8;
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/** Deterministic noise so the texture is the same on every load. */
function rng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

/** Mowed outfield: wide stripes plus a faint cross pattern, the classic broadcast look. */
export function grassTexture(light: string, dark: string): THREE.CanvasTexture {
  const { c, g } = canvas(512, 512);
  if (g) {
    const stripes = 8;
    for (let i = 0; i < stripes; i++) {
      g.fillStyle = i % 2 ? dark : light;
      g.fillRect((i * 512) / stripes, 0, 512 / stripes, 512);
    }
    const r = rng(7);
    for (let k = 0; k < 9000; k++) {
      g.fillStyle = r() > 0.5 ? 'rgba(255,255,255,0.035)' : 'rgba(0,0,0,0.05)';
      g.fillRect(r() * 512, r() * 512, 1.5, 1.5);
    }
  }
  return finish(c, [12, 12]);
}

export function dirtTexture(base: string): THREE.CanvasTexture {
  const { c, g } = canvas(256, 256);
  if (g) {
    g.fillStyle = base;
    g.fillRect(0, 0, 256, 256);
    const r = rng(11);
    for (let k = 0; k < 7000; k++) {
      const v = r();
      g.fillStyle = v > 0.6 ? 'rgba(255,230,200,0.06)' : v > 0.3 ? 'rgba(0,0,0,0.10)' : 'rgba(60,40,25,0.12)';
      const s = 1 + r() * 2.5;
      g.fillRect(r() * 256, r() * 256, s, s);
    }
  }
  return finish(c, [10, 10]);
}

/** Baseball leather with the two-lobe seam and stitches, laid out for a sphere's equirectangular UVs. */
export function ballTexture(leather: string, seam: string): THREE.CanvasTexture {
  const W = 512;
  const H = 256;
  const { c, g } = canvas(W, H);
  if (g) {
    g.fillStyle = leather;
    g.fillRect(0, 0, W, H);
    // seam: the standard tennis-ball curve, lat = 0.4 * sin(2 * lon) (in radians of latitude), sampled densely
    const pts: [number, number][] = [];
    for (let i = 0; i <= 400; i++) {
      const lon = (i / 400) * Math.PI * 2;
      const lat = 0.42 * Math.sin(2 * lon);
      pts.push([(lon / (Math.PI * 2)) * W, H / 2 - (lat / Math.PI) * H]);
    }
    g.strokeStyle = 'rgba(0,0,0,0.12)';
    g.lineWidth = 7;
    g.beginPath();
    pts.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y)));
    g.stroke();
    g.strokeStyle = seam;
    g.lineWidth = 2.2;
    for (let i = 2; i < pts.length - 2; i += 4) {
      const [x0, y0] = pts[i - 2];
      const [x1, y1] = pts[i + 2];
      const nx = -(y1 - y0);
      const ny = x1 - x0;
      const n = Math.hypot(nx, ny) || 1;
      const [x, y] = pts[i];
      g.beginPath();
      g.moveTo(x - (nx / n) * 6 - (x1 - x0) * 0.15, y - (ny / n) * 6 - (y1 - y0) * 0.15);
      g.lineTo(x + (nx / n) * 6 + (x1 - x0) * 0.15, y + (ny / n) * 6 + (y1 - y0) * 0.15);
      g.stroke();
    }
  }
  return finish(c);
}

/** Night sky: near-black zenith, a cool glow at the horizon from the park lights. */
export function skyTexture(zenith: string, horizon: string, glow: string): THREE.CanvasTexture {
  const { c, g } = canvas(4, 256);
  if (g) {
    const grad = g.createLinearGradient(0, 0, 0, 256);
    // canvas top = sphere top; the horizon (sphere equator) is the canvas middle
    grad.addColorStop(0, zenith);
    grad.addColorStop(0.28, zenith);
    grad.addColorStop(0.44, horizon);
    grad.addColorStop(0.5, glow);
    grad.addColorStop(0.56, horizon);
    grad.addColorStop(1, zenith);
    g.fillStyle = grad;
    g.fillRect(0, 0, 4, 256);
  }
  const t = finish(c);
  t.wrapS = THREE.ClampToEdgeWrapping;
  t.wrapT = THREE.ClampToEdgeWrapping;
  return t;
}
