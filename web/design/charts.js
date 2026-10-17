// Broadcast pitch graphics for the design lock (HACK-039). Same release thrown in two airs:
// sea level = neutral grey, dashed (reference); Harp Helú air = Diablos red, solid (the story).
// Example numbers only (riding four-seam, ~5.3 in of ride lost): the product reads them from the model.
const FT = 12;
const PITCH = { release: 6.0, extension: 6.3, mound: 60.5, plateZ: 1.42, v: 94.0 };
const IVB = { sea: 18.0, cdmx: 12.7 }; // inches of induced vertical break (example)
const HB = { sea: 8.0, cdmx: 6.1 };

function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

// Height (ft) along the flight, s in [0,1] from release to the front of the plate.
function heightAt(s, ivbIn) {
  const drop = 4.6;              // gravity + approach angle drop without spin (ft), example
  const ride = ivbIn / FT;       // spin-induced lift accumulates as s^2 (constant acceleration)
  return PITCH.release - drop * s * s - 0.15 * s + ride * s * s;
}
function sideAt(s, hbIn) { return -0.35 * s + (hbIn / FT) * s * s; }

function setup(canvas) {
  const dpr = window.devicePixelRatio || 1, r = canvas.getBoundingClientRect();
  canvas.width = Math.round(r.width * dpr); canvas.height = Math.round(r.height * dpr);
  const g = canvas.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { g, w: r.width, h: r.height };
}

function dot(g, x, y, r, fill, ring) {
  g.beginPath(); g.arc(x, y, r + 2, 0, Math.PI * 2); g.fillStyle = ring; g.fill();
  g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fillStyle = fill; g.fill();
}

function label(g, x, y, text, color, align = 'left', weight = 500, size = 12) {
  g.font = `${weight} ${size}px Geist, 'Segoe UI', sans-serif`; g.fillStyle = color; g.textAlign = align; g.textBaseline = 'middle';
  g.fillText(text, x, y);
}

function drawSide(canvas) {
  const { g, w, h } = setup(canvas);
  const C = { sea: css('--sea'), red: css('--red'), fg: css('--fg'), muted: css('--fg-muted'), faint: css('--fg-faint'),
    line: css('--line'), surface: css('--surface'), chalk: css('--chalk'), dirt: css('--dirt') };
  const pad = { l: 52, r: 150, t: 40, b: 46 };
  const dist = PITCH.mound - PITCH.extension; // release to plate, ft
  const X = (d) => pad.l + (d / dist) * (w - pad.l - pad.r);
  const Y = (z) => h - pad.b - (z / 6.6) * (h - pad.t - pad.b);

  // recessive grid + axes
  g.lineWidth = 1; g.strokeStyle = C.line;
  for (const z of [0, 2, 4, 6]) { g.beginPath(); g.moveTo(pad.l, Y(z)); g.lineTo(w - pad.r + 8, Y(z)); g.stroke(); }
  for (const z of [0, 2, 4, 6]) label(g, pad.l - 10, Y(z), `${z}`, C.faint, 'right', 400, 11);
  for (const d of [0, 10, 20, 30, 40, 50]) label(g, X(d), h - pad.b + 16, `${d}`, C.faint, 'center', 400, 11);
  label(g, pad.l, h - 10, 'Distancia desde la salida (ft)', C.muted, 'left', 400, 11);
  g.save(); g.translate(14, Y(3.5)); g.rotate(-Math.PI / 2); label(g, 0, 0, 'Altura (ft)', C.muted, 'center', 400, 11); g.restore();

  // context: strike-zone band at the plate, plate tick, mound edge
  g.fillStyle = 'rgba(232,230,225,0.07)'; g.fillRect(X(dist) - 6, Y(3.5), 12, Y(1.6) - Y(3.5));
  g.strokeStyle = C.chalk; g.globalAlpha = 0.5; g.strokeRect(X(dist) - 6, Y(3.5), 12, Y(1.6) - Y(3.5)); g.globalAlpha = 1;
  label(g, X(dist), Y(3.5) - 12, 'Zona', C.faint, 'center', 400, 11);
  g.fillStyle = C.dirt; g.globalAlpha = 0.55; g.beginPath(); g.moveTo(pad.l - 6, Y(0)); g.quadraticCurveTo(X(2.5), Y(0.95), X(9), Y(0)); g.fill(); g.globalAlpha = 1;

  // flights: ghost trail (time samples) + path, sea first so CDMX sits on top
  const runs = [['sea', IVB.sea, C.sea, [6, 5], 2], ['cdmx', IVB.cdmx, C.red, [], 2.5]];
  const ends = {};
  for (const [key, ivb, col, dash, lw] of runs) {
    g.setLineDash(dash); g.strokeStyle = col; g.lineWidth = lw; g.beginPath();
    for (let i = 0; i <= 80; i++) { const s = i / 80, x = X(s * dist), y = Y(heightAt(s, ivb)); i ? g.lineTo(x, y) : g.moveTo(x, y); }
    g.stroke(); g.setLineDash([]);
    if (key === 'cdmx') for (let k = 1; k <= 6; k++) { const s = k / 7; g.globalAlpha = 0.12 + 0.1 * k; dot(g, X(s * dist), Y(heightAt(s, ivb)), 3, col, C.surface); }
    g.globalAlpha = 1;
    ends[key] = [X(dist), Y(heightAt(1, ivb))];
  }
  dot(g, ...ends.sea, 6, C.sea, C.surface); dot(g, ...ends.cdmx, 6, C.red, C.surface);
  dot(g, X(0), Y(PITCH.release), 5, C.fg, C.surface);
  label(g, X(0) + 10, Y(PITCH.release) - 14, 'Salida', C.muted, 'left', 400, 11);

  // direct labels (text in text tokens; the swatch carries identity) + the delta bracket
  const bx = ends.cdmx[0] + 14, lx = bx + 14;
  g.strokeStyle = C.fg; g.lineWidth = 1.25; g.beginPath();
  g.moveTo(bx - 4, ends.sea[1]); g.lineTo(bx, ends.sea[1]); g.lineTo(bx, ends.cdmx[1]); g.lineTo(bx - 4, ends.cdmx[1]); g.stroke();
  g.fillStyle = C.sea; g.fillRect(lx, ends.sea[1] - 1, 12, 2);
  label(g, lx + 18, ends.sea[1], 'Nivel del mar', C.fg, 'left', 500, 12);
  g.fillStyle = C.red; g.fillRect(lx, ends.cdmx[1] - 1, 12, 2);
  label(g, lx + 18, ends.cdmx[1], 'Harp Helú', C.fg, 'left', 500, 12);
  label(g, lx, ends.cdmx[1] + 30, `−${(IVB.sea - IVB.cdmx).toFixed(1)} in`, C.fg, 'left', 600, 20);
  label(g, lx, ends.cdmx[1] + 50, 'de ride', C.muted, 'left', 400, 11);
}

function drawCatcher(canvas) {
  const { g, w, h } = setup(canvas);
  const C = { sea: css('--sea'), red: css('--red'), fg: css('--fg'), muted: css('--fg-muted'), chalk: css('--chalk'), bg: '#0f0f12' };
  // catcher's view: 1 ft = px pixels at the plate; zone 17 in wide, 1.6 to 3.5 ft high
  const px = Math.min(h * 0.62 / 2.6, w * 0.32 / 1.42), cx = w * 0.46, zb = h * 0.78;
  const Xft = (x) => cx + x * px, Yft = (z) => zb - (z - 1.6) * px;
  const zl = Xft(-17 / 24), zr = Xft(17 / 24), zt = Yft(3.5);
  const loc = { sea: [Xft(sideAt(1, HB.sea)), Yft(heightAt(1, IVB.sea))], cdmx: [Xft(sideAt(1, HB.cdmx)), Yft(heightAt(1, IVB.cdmx))] };
  const ball = (2.9 / FT) * px / 2;

  // home plate, foreshortened, just under the zone; zone frame and 3x3 grid in chalk
  const pw = zr - zl, py = zb + px * 0.35;
  g.fillStyle = C.chalk; g.globalAlpha = 0.16; g.beginPath();
  g.moveTo(zl, py); g.lineTo(zr, py); g.lineTo(zr, py + pw * 0.07); g.lineTo(cx, py + pw * 0.15); g.lineTo(zl, py + pw * 0.07); g.closePath(); g.fill();
  g.globalAlpha = 1; g.strokeStyle = C.chalk; g.lineWidth = 1;
  g.globalAlpha = 0.16;
  for (let i = 1; i < 3; i++) {
    g.beginPath(); g.moveTo(zl + pw * i / 3, zt); g.lineTo(zl + pw * i / 3, zb);
    g.moveTo(zl, zt + (zb - zt) * i / 3); g.lineTo(zr, zt + (zb - zt) * i / 3); g.stroke();
  }
  g.globalAlpha = 0.85; g.lineWidth = 2; g.strokeRect(zl, zt, pw, zb - zt); g.globalAlpha = 1;

  // flight tubes: from the release (far, small) to the plate (near, ball size), getting wider and brighter
  const rel = [cx + px * 0.55, h * 0.1];
  for (const [key, col] of [['sea', C.sea], ['cdmx', C.red]]) {
    const [ex, ey] = loc[key], bend = key === 'cdmx' ? 0.10 : 0.16;
    let prev = rel;
    for (let i = 1; i <= 28; i++) {
      const t = i / 28, mx = rel[0] + (ex - rel[0]) * t, my = rel[1] + (ey - rel[1]) * t - Math.sin(Math.PI * t) * (ey - rel[1]) * bend;
      g.strokeStyle = col; g.globalAlpha = 0.08 + 0.5 * t * t; g.lineCap = 'round';
      g.lineWidth = 1 + (ball * 1.5) * t * t; g.beginPath(); g.moveTo(...prev); g.lineTo(mx, my); g.stroke(); prev = [mx, my];
    }
  }
  g.globalAlpha = 1; g.lineCap = 'butt';
  dot(g, ...loc.sea, ball, C.sea, C.bg);
  dot(g, ...loc.cdmx, ball, C.red, C.bg);

  // movement lost: thin arrow between ball edges
  const [sx, sy] = loc.sea, [rx, ry] = loc.cdmx, ang = Math.atan2(ry - sy, rx - sx), d = Math.hypot(rx - sx, ry - sy);
  if (d > 2 * ball + 12) {
    const a0 = [sx + Math.cos(ang) * (ball + 4), sy + Math.sin(ang) * (ball + 4)], a1 = [rx - Math.cos(ang) * (ball + 4), ry - Math.sin(ang) * (ball + 4)];
    g.strokeStyle = C.fg; g.lineWidth = 1.5; g.beginPath(); g.moveTo(...a0); g.lineTo(...a1); g.stroke();
    g.fillStyle = C.fg; g.beginPath(); g.moveTo(...a1);
    g.lineTo(a1[0] - Math.cos(ang - 0.5) * 8, a1[1] - Math.sin(ang - 0.5) * 8); g.lineTo(a1[0] - Math.cos(ang + 0.5) * 8, a1[1] - Math.sin(ang + 0.5) * 8); g.fill();
  }

  // labels in a column right of the zone (text tokens; swatches carry identity)
  const lx = zr + 28;
  g.fillStyle = C.sea; g.fillRect(lx, sy - 1, 12, 2); label(g, lx + 18, sy, 'Nivel del mar', C.fg, 'left', 500, 13);
  g.fillStyle = C.red; g.fillRect(lx, ry - 1, 12, 2); label(g, lx + 18, ry, 'Harp Helú', C.fg, 'left', 500, 13);
  label(g, lx, ry + 34, `−${(IVB.sea - IVB.cdmx).toFixed(1)} in`, C.fg, 'left', 600, 22);
  label(g, lx, ry + 58, `de ride  ·  −${(HB.sea - HB.cdmx).toFixed(1)} in de corrida`, C.muted, 'left', 400, 12);
}

function drawAll() {
  const side = document.getElementById('side'), catcher = document.getElementById('catcher');
  if (side) drawSide(side);
  if (catcher) drawCatcher(catcher);
}
