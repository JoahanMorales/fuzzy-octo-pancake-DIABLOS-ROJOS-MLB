/* Day game: a custom sky shader with procedural clouds, a grass shader with real mowing stripes (their
   brightness flips with the view direction, as on a real field), clay infield, and the horizon that tells the air:
   the volcanoes behind CDMX in a deep high-altitude blue, or the sea under a hazier low-altitude sky.
   Feet; home plate's back tip at the origin, center field toward -z. */
import { useEffect, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Line } from '@react-three/drei';
import * as THREE from 'three';
import { MOUND_H, MOUND_Z, type Palette, type ParkSide, type Vec3 } from './sceneModel';

const BASE = 90 / Math.SQRT2;
const FENCE_R = 335;

/** Sun high over the third-base side, behind the catcher's left shoulder (a classic day-game broadcast light). */
export const SUN = new THREE.Vector3(-0.42, 0.72, 0.55).normalize();

/* ---------------------------------- sky ---------------------------------- */

const SKY_VERT = /* glsl */ `
  varying vec3 vDir;
  void main() { vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
const SKY_FRAG = /* glsl */ `
  uniform vec3 zenith; uniform vec3 mid; uniform vec3 horizon; uniform vec3 sunDir; uniform float cover;
  varying vec3 vDir;
  float h1(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float n2(vec2 p) { vec2 i = floor(p), f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(h1(i), h1(i + vec2(1, 0)), u.x), mix(h1(i + vec2(0, 1)), h1(i + vec2(1, 1)), u.x), u.y); }
  float fbm(vec2 p) { float v = 0.0, a = 0.5; for (int i = 0; i < 6; i++) { v += a * n2(p); p = p * 2.02 + 31.0; a *= 0.5; } return v; }
  void main() {
    vec3 d = normalize(vDir);
    float h = max(d.y, 0.0);
    vec3 col = mix(horizon, mid, smoothstep(0.0, 0.18, h));
    col = mix(col, zenith, smoothstep(0.15, 0.8, h));
    // sun: disc, bright halo and a wide warm glow
    float s = max(dot(d, normalize(sunDir)), 0.0);
    col += vec3(1.0, 0.95, 0.85) * (pow(s, 1800.0) * 6.0 + pow(s, 120.0) * 0.6 + pow(s, 8.0) * 0.12);
    // clouds: fbm on a dome projection, denser toward the horizon so the cameras see them
    vec2 uv = d.xz / (d.y + 0.12) * 1.6;
    float c = fbm(uv + fbm(uv * 0.5) * 1.3);
    float band = smoothstep(0.0, 0.05, d.y) * (1.0 - smoothstep(0.35, 0.7, d.y));
    float a = smoothstep(cover, cover + 0.22, c) * band;
    vec3 cloud = mix(vec3(0.97, 0.98, 1.0), vec3(0.72, 0.78, 0.88), smoothstep(cover + 0.1, cover + 0.45, c));
    cloud += vec3(1.0, 0.92, 0.8) * pow(s, 6.0) * 0.25;
    col = mix(col, cloud, a * 0.92);
    if (d.y < 0.0) col = horizon;
    float n = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453);
    gl_FragColor = vec4(col + (n - 0.5) / 255.0, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;

export function DaySky({ park }: { park: ParkSide }) {
  const harp = park === 'harp';
  // thinner air at 2,240 m scatters less: a deeper blue and a cleaner horizon than at sea level
  const uniforms = useMemo(() => ({
    zenith: { value: new THREE.Color(harp ? '#0f4fb8' : '#2a6cc4') },
    mid: { value: new THREE.Color(harp ? '#3d86e0' : '#62a0e3') },
    horizon: { value: new THREE.Color(harp ? '#a9cff5' : '#cfe1f2') },
    sunDir: { value: SUN.clone() },
    cover: { value: harp ? 0.6 : 0.54 },
  }), [harp]);
  return (
    <mesh renderOrder={-2}>
      <sphereGeometry args={[3000, 64, 32]} />
      <shaderMaterial vertexShader={SKY_VERT} fragmentShader={SKY_FRAG} uniforms={uniforms} side={THREE.BackSide}
        depthWrite={false} fog={false} />
    </mesh>
  );
}

/* --------------------------------- grass --------------------------------- */

const NOISE_GLSL = /* glsl */ `
  float gh(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float gn(vec2 p) { vec2 i = floor(p), f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(gh(i), gh(i + vec2(1, 0)), u.x), mix(gh(i + vec2(0, 1)), gh(i + vec2(1, 1)), u.x), u.y); }
  float gfbm(vec2 p) { float v = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { v += a * gn(p); p = p * 2.1 + 9.0; a *= 0.5; } return v; }
`;

/** MeshStandardMaterial with the color computed per pixel from the world position (keeps three's lighting,
 *  shadows and fog). `kind` picks the grass stripes or the clay. */
function useGroundMaterial(kind: 'grass' | 'clay', c: Palette) {
  return useMemo(() => {
    const m = new THREE.MeshStandardMaterial({ roughness: kind === 'grass' ? 0.82 : 0.95, metalness: 0 });
    const grassA = new THREE.Color('#5f9443'), grassB = new THREE.Color('#4c8136'), clay = new THREE.Color('#b27a4e');
    void c;
    m.onBeforeCompile = (sh) => {
      sh.uniforms.uA = { value: kind === 'grass' ? grassA : clay };
      sh.uniforms.uB = { value: kind === 'grass' ? grassB : new THREE.Color('#8f5d38') };
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vWorld;')
        .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvWorld = (modelMatrix * vec4(transformed, 1.0)).xyz;');
      const grass = /* glsl */ `
        // mowing stripes 18 ft wide, aligned with the line home -> center field; the blades of alternate stripes lean
        // opposite ways, so each stripe looks light or dark depending on where the camera looks from
        float s = mod(floor((vWorld.x + 6.0) / 12.0), 2.0);
        float t = mod(floor((vWorld.z) / 12.0), 2.0);
        vec3 toCam = normalize(cameraPosition - vWorld);
        // soft edge between stripes (a mower leaves a 6 in blend, not a hard line)
        float ex = smoothstep(0.0, 0.04, abs(fract((vWorld.x + 6.0) / 12.0) - 0.5) * 2.0 - 0.96 + 0.04);
        float lean = (s * 2.0 - 1.0) * (0.25 + 0.2 * toCam.z) + (t * 2.0 - 1.0) * toCam.x * 0.06;
        vec3 g = mix(uB, uA, clamp(0.5 + lean * (1.0 - ex * 0.5), 0.0, 1.0));
        float patchy = gfbm(vWorld.xz * 0.02);
        float clumps = gfbm(vWorld.xz * 0.6);
        float fine = gn(vWorld.xz * 6.0) * 0.6 + gn(vWorld.xz * 15.0) * 0.4;
        float dist = length(cameraPosition - vWorld);
        float fade = clamp(dist / 140.0, 0.0, 1.0);
        g *= 0.9 + 0.16 * patchy;
        g *= mix(0.84 + 0.3 * fine * (0.7 + 0.6 * clumps), 1.0, fade);
        // yellowish dry tint far away, like real turf in the sun
        g = mix(g, g * vec3(1.06, 1.04, 0.86), smoothstep(150.0, 600.0, dist) * 0.5);
        diffuseColor.rgb = g;`;
      const clayCol = /* glsl */ `
        float p = gfbm(vWorld.xz * 0.35);
        float grit = gn(vWorld.xz * 14.0);
        vec3 g = mix(uB, uA, 0.35 + 0.6 * p);
        g *= 0.9 + 0.18 * grit;
        diffuseColor.rgb = g;`;
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', `#include <common>\nvarying vec3 vWorld;\nuniform vec3 uA;\nuniform vec3 uB;\n${NOISE_GLSL}`)
        .replace('#include <color_fragment>', `#include <color_fragment>\n${kind === 'grass' ? grass : clayCol}`);
    };
    m.customProgramCacheKey = () => `ground-${kind}`;
    return m;
  }, [kind, c]);
}

export function GrassField({ c }: { c: Palette }) {
  const grass = useGroundMaterial('grass', c);
  const clay = useGroundMaterial('clay', c);
  const plate = useMemo(() => {
    const inch = 1 / 12;
    const s = new THREE.Shape();
    s.moveTo(0, 0);
    s.lineTo(-8.5 * inch, 8.5 * inch);
    s.lineTo(-8.5 * inch, 17 * inch);
    s.lineTo(8.5 * inch, 17 * inch);
    s.lineTo(8.5 * inch, 8.5 * inch);
    s.closePath();
    return s;
  }, []);
  const box = (sx: number): Vec3[] => {
    const zMid = -0.7, xi = sx * 1.21, xo = sx * 5.21;
    return [[xi, 0.07, zMid + 3], [xo, 0.07, zMid + 3], [xo, 0.07, zMid - 3], [xi, 0.07, zMid - 3], [xi, 0.07, zMid + 3]];
  };
  const flat: [number, number, number] = [-Math.PI / 2, 0, 0];
  return (
    <group>
      <mesh rotation={flat} receiveShadow material={grass}>
        <circleGeometry args={[1600, 96]} />
      </mesh>
      <mesh rotation={flat} position={[0, 0.02, 0]} receiveShadow material={clay}>
        <ringGeometry args={[FENCE_R - 16, FENCE_R + 1, 128]} />
      </mesh>
      <mesh rotation={flat} position={[0, 0.03, MOUND_Z]} receiveShadow material={clay}>
        <circleGeometry args={[95, 96]} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, Math.PI / 4]} position={[0, 0.045, -BASE]} receiveShadow material={grass}>
        <planeGeometry args={[80, 80]} />
      </mesh>
      <mesh rotation={flat} position={[0, 0.055, -0.8]} receiveShadow material={clay}>
        <circleGeometry args={[13, 64]} />
      </mesh>
      <mesh position={[0, MOUND_H / 2 + 0.04, MOUND_Z]} receiveShadow castShadow material={clay}>
        <cylinderGeometry args={[2.6, 9, MOUND_H, 48]} />
      </mesh>
      <mesh position={[0, MOUND_H + 0.06, MOUND_Z]}>
        <boxGeometry args={[2, 0.08, 0.5]} />
        <meshStandardMaterial color={c.chalk} roughness={0.5} />
      </mesh>
      {([[BASE, -BASE], [0, -BASE * 2], [-BASE, -BASE]] as const).map(([x, z]) => (
        <mesh key={`${x}${z}`} position={[x, 0.2, z]} rotation={[0, Math.PI / 4, 0]} castShadow receiveShadow>
          <boxGeometry args={[1.25, 0.25, 1.25]} />
          <meshStandardMaterial color="#f6f4ee" roughness={0.5} />
        </mesh>
      ))}
      <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0.07, 0]} receiveShadow>
        <shapeGeometry args={[plate]} />
        <meshStandardMaterial color="#f6f4ee" roughness={0.45} side={THREE.DoubleSide} />
      </mesh>
      {[-1, 1].map((s) => (
        <mesh key={s} rotation={[-Math.PI / 2, 0, (s * Math.PI) / 4]}
          position={[(s * FENCE_R) / Math.SQRT2 / 2, 0.065, -FENCE_R / Math.SQRT2 / 2]}>
          <planeGeometry args={[0.33, FENCE_R]} />
          <meshStandardMaterial color="#f6f4ee" roughness={0.6} />
        </mesh>
      ))}
      {[box(-1), box(1)].map((pts, i) => <Line key={i} points={pts} color="#f6f4ee" lineWidth={1.6} />)}
      <Ballpark />
    </group>
  );
}

/* ---------------------------------- wall --------------------------------- */

const ARC = { start: Math.PI - 1.15, len: 2.3 };
const WALL_H = 10;

/** Padded outfield wall painted on a canvas: panels with seams, a darker kick plate, and a few signs. The batter's eye
 *  (center field) stays plain. One texture covers the whole arc; a second canvas carries the seams as a bump map. */
function wallTextures() {
  const W = 4096, H = 64;
  const mk = () => { const cv = document.createElement('canvas'); cv.width = W; cv.height = H; return cv; };
  const cv = mk(), bc = mk();
  const g = cv.getContext('2d'), b = bc.getContext('2d');
  if (g && b) {
    const ft = W / (FENCE_R * ARC.len);
    const grad = g.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, '#2b5e41');
    grad.addColorStop(0.55, '#225238');
    grad.addColorStop(0.82, '#1a432d');
    grad.addColorStop(0.83, '#14331f');
    grad.addColorStop(1, '#102a1a');
    g.fillStyle = grad;
    g.fillRect(0, 0, W, H);
    b.fillStyle = '#7a7a7a';
    b.fillRect(0, 0, W, H);
    // the pad bulges between seams: brighter in the middle of each 8 ft panel in the bump map
    for (let x = 0; x < W; x += 8 * ft) {
      const pg = b.createLinearGradient(x, 0, x + 8 * ft, 0);
      pg.addColorStop(0, '#505050');
      pg.addColorStop(0.5, '#b4b4b4');
      pg.addColorStop(1, '#505050');
      b.fillStyle = pg;
      b.fillRect(x, 0, 8 * ft, H * 0.83);
      g.fillStyle = 'rgba(0,0,0,0.42)';
      g.fillRect(x, 0, 2, H);
      g.fillStyle = 'rgba(255,255,255,0.07)';
      g.fillRect(x + 2, 0, 1, H);
    }
    g.fillStyle = 'rgba(0,0,0,0.3)';
    g.fillRect(0, H * 0.1, W, 1);
    // fine vinyl grain
    for (let i = 0; i < 9000; i++) {
      g.fillStyle = Math.random() < 0.5 ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.04)';
      g.fillRect(Math.random() * W, Math.random() * H, 2, 1);
    }
    const signs: [u: number, w: number, text: string, bg: string, fg: string][] = [
      [0.12, 56, 'DIABLOS ROJOS', '#b3122b', '#ffffff'],
      [0.27, 46, 'STUFF+ 2240', '#16161a', '#f3f1ec'],
      [0.73, 46, '2240 m', '#f3f1ec', '#b3122b'],
      [0.88, 56, 'DIABLOS ROJOS', '#b3122b', '#ffffff'],
    ];
    for (const [u, w, text, bg, fg] of signs) {
      const sw = w * ft, x0 = u * W - sw / 2, y0 = H * 0.16, sh = H * 0.6;
      g.fillStyle = bg;
      g.fillRect(x0, y0, sw, sh);
      g.fillStyle = 'rgba(255,255,255,0.12)';
      g.fillRect(x0, y0, sw, 2);
      g.fillStyle = fg;
      g.font = `800 ${Math.round(sh * 0.62)}px "Segoe UI", Arial, sans-serif`;
      g.textAlign = 'center';
      g.textBaseline = 'middle';
      g.fillText(text, u * W, y0 + sh * 0.54, sw * 0.9);
      b.fillStyle = '#9a9a9a';
      b.fillRect(x0, y0, sw, sh);
    }
  }
  const tex = (c: HTMLCanvasElement, color: boolean) => {
    const t = new THREE.CanvasTexture(c);
    if (color) t.colorSpace = THREE.SRGBColorSpace;
    // the arc's u runs right field -> left field: flip so the signs read from inside the park
    t.wrapS = THREE.RepeatWrapping;
    t.repeat.x = -1;
    t.anisotropy = 8;
    return t;
  };
  return { map: tex(cv, true), bump: tex(bc, false) };
}

/* Stands behind home plate: one sloped ring painted in the shader (concrete risers, red seats, aisles, and a crowd
   where each seat is filled or empty by a hash), so thousands of fans cost one draw call. */
const STAND = { r0: 70, r1: 205, y0: 6, rise: 62, start: -1.05, len: 2.1 };
const CROWD_FRAG = /* glsl */ `
  float r = length(vWorld.xz);
  float ang = atan(vWorld.x, vWorld.z);
  float rr = (r - ${STAND.r0.toFixed(1)}) / 2.9;
  float row = floor(rr), fr = fract(rr);
  float along = ang * r / 1.9;
  float seat = floor(along), fs = fract(along);
  float aisle = step(abs(fract(ang * 9.0) - 0.5), 0.022);
  vec3 concrete = vec3(0.45, 0.44, 0.42);
  vec3 col = mix(vec3(0.62, 0.11, 0.15), vec3(0.5, 0.08, 0.12), gh(vec2(row, seat)));
  col = mix(col, concrete * 0.75, step(fr, 0.24));
  float h = gh(vec2(seat * 1.37, row * 3.11));
  float k = gh(vec2(row * 7.3, seat * 0.71));
  // shirts: lots of Diablos red, then white, black, a few blues and yellows
  vec3 shirt = k < 0.34 ? vec3(0.75, 0.08, 0.12) : k < 0.58 ? vec3(0.92, 0.91, 0.88) : k < 0.78 ? vec3(0.08, 0.08, 0.09)
    : k < 0.9 ? vec3(0.16, 0.3, 0.62) : vec3(0.9, 0.72, 0.18);
  vec3 skin = mix(vec3(0.42, 0.28, 0.2), vec3(0.72, 0.52, 0.4), gh(vec2(seat, row * 1.9)));
  float body = step(0.2, fs) * step(fs, 0.8) * step(0.3, fr) * step(fr, 0.8);
  float head = step(length(vec2((fs - 0.5) * 1.3, fr - 0.88)), 0.14);
  float full = step(h, 0.66) * (1.0 - aisle);
  col = mix(col, col * 0.55, full * step(0.24, fr) * step(fr, 0.32));
  col = mix(col, shirt, body * full);
  col = mix(col, skin, head * full * (1.0 - body));
  col = mix(col, concrete, aisle);
  // far away the pattern turns to noise: fade to its average color
  float blur = smoothstep(0.35, 0.9, fwidth(rr));
  col = mix(col, vec3(0.5, 0.2, 0.2), blur);
  diffuseColor.rgb = col;`;

function useCrowdMaterial() {
  return useMemo(() => {
    const m = new THREE.MeshStandardMaterial({ roughness: 0.9, metalness: 0, side: THREE.DoubleSide });
    m.onBeforeCompile = (sh) => {
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vWorld;')
        .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvWorld = (modelMatrix * vec4(transformed, 1.0)).xyz;');
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', `#include <common>\nvarying vec3 vWorld;\n${NOISE_GLSL}`)
        .replace('#include <color_fragment>', `#include <color_fragment>\n${CROWD_FRAG}`);
    };
    m.customProgramCacheKey = () => 'crowd';
    return m;
  }, []);
}

function Grandstand() {
  const crowd = useCrowdMaterial();
  useEffect(() => () => crowd.dispose(), [crowd]);
  const { r0, r1, y0, rise, start, len } = STAND;
  const top = y0 + rise;
  const cols = Array.from({ length: 7 }, (_, i) => start + 0.08 + (i * (len - 0.16)) / 6);
  return (
    <group>
      {/* backstop wall */}
      <mesh position={[0, y0 / 2, 0]} receiveShadow>
        <cylinderGeometry args={[r0 - 1, r0 - 1, y0, 96, 1, true, start, len]} />
        <meshStandardMaterial color="#3a7853" emissive="#1b3a28" roughness={0.8} side={THREE.BackSide} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, y0, 0]}>
        <ringGeometry args={[r0 - 1.1, r0 + 0.2, 96, 1, start - Math.PI / 2, len]} />
        <meshStandardMaterial color="#e9c43a" roughness={0.6} />
      </mesh>
      <mesh position={[0, y0 + rise / 2, 0]} material={crowd}>
        <cylinderGeometry args={[r1, r0, rise, 160, 1, true, start, len]} />
      </mesh>
      {/* back wall, roof and its columns */}
      <mesh position={[0, top + 9, 0]}>
        <cylinderGeometry args={[r1, r1, 18, 96, 1, true, start, len]} />
        <meshStandardMaterial color="#2a2a2e" roughness={0.9} side={THREE.DoubleSide} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, top + 18, 0]}>
        <ringGeometry args={[r1 - 62, r1 + 2, 96, 1, start - Math.PI / 2, len]} />
        <meshStandardMaterial color="#d9d9dc" roughness={0.7} side={THREE.DoubleSide} />
      </mesh>
      <mesh position={[0, top + 17.2, 0]}>
        <cylinderGeometry args={[r1 - 62, r1 - 62, 1.6, 96, 1, true, start, len]} />
        <meshStandardMaterial color="#b3122b" roughness={0.6} side={THREE.DoubleSide} />
      </mesh>
      {cols.map((a) => (
        <mesh key={a} position={[Math.sin(a) * (r1 - 4), (top + 18) / 2 + 20, Math.cos(a) * (r1 - 4)]}>
          <cylinderGeometry args={[0.8, 0.8, top + 18 - 40, 8]} />
          <meshStandardMaterial color="#cfcfd2" roughness={0.6} />
        </mesh>
      ))}
    </group>
  );
}

/** Outfield wall with thickness (padded face, cap, yellow home-run line), the batter's eye and the foul poles. */
function Ballpark() {
  const { map, bump } = useMemo(wallTextures, []);
  useEffect(() => () => { map.dispose(); bump.dispose(); }, [map, bump]);
  const capStart = ARC.start - Math.PI / 2;
  return (
    <group>
      <mesh position={[0, WALL_H / 2, 0]} receiveShadow castShadow>
        <cylinderGeometry args={[FENCE_R - 1, FENCE_R - 1, WALL_H, 192, 1, true, ARC.start, ARC.len]} />
        <meshStandardMaterial map={map} bumpMap={bump} bumpScale={1.5} roughness={0.78} side={THREE.BackSide} />
      </mesh>
      <mesh position={[0, WALL_H / 2, 0]}>
        <cylinderGeometry args={[FENCE_R + 1, FENCE_R + 1, WALL_H, 96, 1, true, ARC.start, ARC.len]} />
        <meshStandardMaterial color="#173a27" roughness={0.9} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, WALL_H, 0]} receiveShadow>
        <ringGeometry args={[FENCE_R - 1.05, FENCE_R + 1.05, 192, 1, capStart, ARC.len]} />
        <meshStandardMaterial color="#e9c43a" roughness={0.55} />
      </mesh>
      <mesh position={[0, WALL_H - 0.25, 0]}>
        <cylinderGeometry args={[FENCE_R - 1.04, FENCE_R - 1.04, 0.5, 192, 1, true, ARC.start, ARC.len]} />
        <meshStandardMaterial color="#e9c43a" roughness={0.55} side={THREE.BackSide} />
      </mesh>
      <Grandstand />
      {/* batter's eye: a dark, plain block behind center field */}
      <mesh position={[0, 8, -FENCE_R - 10]} castShadow receiveShadow>
        <boxGeometry args={[64, 16, 12]} />
        <meshStandardMaterial color="#1a3a27" roughness={0.95} />
      </mesh>
      <mesh position={[0, 16.2, -FENCE_R - 10]}>
        <boxGeometry args={[64.4, 0.5, 12.4]} />
        <meshStandardMaterial color="#e9c43a" roughness={0.6} />
      </mesh>
      {[-1, 1].map((s) => (
        <mesh key={s} position={[(s * FENCE_R) / Math.SQRT2, 22, -FENCE_R / Math.SQRT2]} castShadow>
          <cylinderGeometry args={[0.4, 0.4, 44, 10]} />
          <meshStandardMaterial color="#e9c43a" roughness={0.5} />
        </mesh>
      ))}
    </group>
  );
}

/* -------------------------------- horizon -------------------------------- */

const hash2 = (x: number, y: number) => { const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453; return s - Math.floor(s); };
function vnoise(x: number, y: number) {
  const ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy;
  const ux = fx * fx * (3 - 2 * fx), uy = fy * fy * (3 - 2 * fy);
  const a = hash2(ix, iy), b = hash2(ix + 1, iy), c = hash2(ix, iy + 1), d = hash2(ix + 1, iy + 1);
  return a + (b - a) * ux + (c - a) * uy + (a - b - c + d) * ux * uy;
}
function fbm2(x: number, y: number, oct = 5) {
  let v = 0, a = 0.5;
  for (let i = 0; i < oct; i++) { v += a * vnoise(x, y); x = x * 2.03 + 17; y = y * 2.03 + 9; a *= 0.5; }
  return v;
}
/** Ridged noise: sharp crests and valleys, the look of eroded volcanic slopes. */
function ridged2(x: number, y: number, oct = 5) {
  let v = 0, a = 0.5;
  for (let i = 0; i < oct; i++) {
    const n = 1 - Math.abs(vnoise(x, y) * 2 - 1);
    v += a * n * n;
    x = x * 2.07 + 5; y = y * 2.07 + 23; a *= 0.5;
  }
  return v;
}
const smooth = (e0: number, e1: number, x: number) => { const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t); };
const gauss = (d: number, s: number) => Math.exp(-(d * d) / (2 * s * s));

/** Height (ft) of the volcano range at a world point. Seen from the city, Iztaccíhuatl (a long ridge: head, chest,
 *  knees, feet) sits left of Popocatépetl (a regular cone with a crater). Heights are exaggerated for the cameras'
 *  narrow vertical field; the shapes are what matter. */
function volcanoHeight(x: number, z: number) {
  const px = x - 620, pz = (z + 1950) * 1.15;
  const pd = Math.hypot(px, pz);
  const flank = Math.max(0, 1 - pd / 680);
  let popo = 300 * Math.pow(flank, 1.9) - 9 * gauss(pd, 16);
  // radial gullies down the cone
  popo -= ridged2(Math.atan2(pz, px) * 9, pd * 0.006, 3) * 26 * flank * (1 - flank) * 2.2;
  const ix = x + 560, iz = z + 2000;
  // one continuous crest with the four summits rising from it
  let izta = 178 * smooth(-560, -330, ix) * (1 - smooth(360, 600, ix)) * gauss(iz, 230);
  for (const [cx, h, sx] of [[-330, 34, 70], [-95, 66, 110], [165, 46, 95], [400, 6, 80]] as const) {
    izta += h * gauss(ix - cx, sx) * gauss(iz, 200);
  }
  const hills = 26 + 80 * fbm2(x * 0.0016, z * 0.0016, 4);
  const mass = Math.max(popo, izta);
  let h = Math.max(hills, mass + hills * 0.35);
  h += (ridged2(x * 0.0055, z * 0.0055) - 0.32) * (14 + mass * 0.2);
  // sink the near edge and the sides below the ground so no edge ever shows
  const f = smooth(-1440, -1680, z) * smooth(1580, 1250, Math.abs(x));
  return h * f - 40 * (1 - f);
}

function useVolcanoGeometry() {
  return useMemo(() => {
    const g = new THREE.PlaneGeometry(3200, 1000, 320, 100);
    g.rotateX(-Math.PI / 2);
    g.translate(0, 0, -1950);
    const pos = g.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < pos.count; i++) pos.setY(i, volcanoHeight(pos.getX(i), pos.getZ(i)));
    g.computeVertexNormals();
    const nrm = g.attributes.normal as THREE.BufferAttribute;
    const col = new Float32Array(pos.count * 3);
    const snow = new THREE.Color('#f2f6fb'), shade = new THREE.Color('#c9d5e6'), rock = new THREE.Color('#6b778b');
    const dark = new THREE.Color('#4c566a'), forest = new THREE.Color('#3b5646');
    const c = new THREE.Color(), s = new THREE.Color();
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
      const slope = 1 - nrm.getY(i);
      c.copy(rock).lerp(dark, smooth(0.35, 0.75, ridged2(x * 0.02, z * 0.02, 3)) * 0.7);
      c.lerp(forest, 1 - smooth(55, 135, y + 30 * fbm2(x * 0.01, z * 0.01, 3)));
      const line = 158 + 34 * fbm2(x * 0.012, z * 0.012, 4) + slope * 70;
      s.copy(snow).lerp(shade, smooth(0.2, 0.6, slope));
      c.lerp(s, smooth(line - 10, line + 14, y) * (1 - smooth(0.5, 0.85, slope)));
      col.set([c.r, c.g, c.b], i * 3);
    }
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    return g;
  }, []);
}

/** Soft puff texture for Popocatépetl's steam plume. */
function usePuff() {
  return useMemo(() => {
    const cv = document.createElement('canvas');
    cv.width = cv.height = 64;
    const g = cv.getContext('2d');
    if (g) {
      const r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
      r.addColorStop(0, 'rgba(255,255,255,0.9)');
      r.addColorStop(0.5, 'rgba(255,255,255,0.35)');
      r.addColorStop(1, 'rgba(255,255,255,0)');
      g.fillStyle = r;
      g.fillRect(0, 0, 64, 64);
    }
    const t = new THREE.CanvasTexture(cv);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }, []);
}

function Volcanoes() {
  const geo = useVolcanoGeometry();
  const puff = usePuff();
  useEffect(() => () => { geo.dispose(); puff.dispose(); }, [geo, puff]);
  const top = volcanoHeight(620, -1950);
  return (
    <group>
      <mesh geometry={geo}>
        <meshStandardMaterial vertexColors roughness={1} metalness={0} />
      </mesh>
      {/* a thin steam plume drifting east, as Popocatépetl usually shows */}
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <sprite key={i} position={[620 + i * i * 6 + i * 10, top + 14 + i * 13, -1950 + i * 4]} scale={30 + i * 16}>
          <spriteMaterial map={puff} color="#eef2f7" transparent opacity={0.5 - i * 0.065} depthWrite={false} />
        </sprite>
      ))}
    </group>
  );
}

/** CDMX: Iztaccíhuatl and Popocatépetl, blue with distance and snow-capped; sea level: open water. */
export function DayHorizon({ park }: { park: ParkSide }) {
  if (park === 'harp') return <Volcanoes />;
  return (
    <mesh position={[0, -1, -1400]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[6000, 1800]} />
      <meshStandardMaterial color="#1f5f86" roughness={0.08} metalness={0.6} />
    </mesh>
  );
}

/* ------------------------------ grass blades ------------------------------ */

const BLADE_VERT = /* glsl */ `
  uniform float uTime; uniform vec3 uSun;
  attribute vec4 aBlade;          // x, z, height, phase
  varying float vT; varying float vShade; varying vec3 vWorld;
  void main() {
    float t = position.y;          // 0 at the root, 1 at the tip
    vT = t;
    float hgt = aBlade.z;
    float ang = aBlade.w * 6.2831;
    vec3 p = vec3(position.x * (1.0 - t) * 0.06, t * hgt, 0.0);
    // random facing, then a curve and a gentle wind that grows toward the tip
    float bend = (0.25 + 0.35 * fract(aBlade.w * 7.3)) * t * t;
    float gust = sin(uTime * 1.6 + aBlade.x * 0.15 + aBlade.y * 0.11) * 0.12 + sin(uTime * 3.1 + aBlade.w * 9.0) * 0.04;
    p.z += (bend + gust * t * t) * hgt;
    float c = cos(ang), s = sin(ang);
    vec3 w = vec3(aBlade.x + p.x * c - p.z * s, p.y, aBlade.y + p.x * s + p.z * c);
    vWorld = w;
    vShade = 0.55 + 0.45 * t;      // fake ambient occlusion: darker roots
    gl_Position = projectionMatrix * viewMatrix * vec4(w, 1.0);
  }`;
const BLADE_FRAG = /* glsl */ `
  uniform vec3 uRoot; uniform vec3 uTip; uniform vec3 fogColor; uniform float fogNear; uniform float fogFar; uniform vec3 uSun;
  varying float vT; varying float vShade; varying vec3 vWorld;
  void main() {
    vec3 col = mix(uRoot, uTip, vT) * vShade;
    // sunlit tips glint when looking toward the sun
    vec3 toCam = normalize(cameraPosition - vWorld);
    col += vec3(0.9, 0.95, 0.6) * pow(max(dot(-toCam, normalize(uSun)), 0.0), 6.0) * vT * 0.25;
    float d = length(cameraPosition - vWorld);
    col = mix(col, fogColor, smoothstep(fogNear, fogFar, d));
    gl_FragColor = vec4(col, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;

function insideGrass(x: number, z: number) {
  // infield grass square (rotated 45°, 80 ft, centered between home and second) minus the mound circle
  const cx = 0, cz = -BASE;
  const rx = (x - cx + (z - cz)) / Math.SQRT2, rz = (-(x - cx) + (z - cz)) / Math.SQRT2;
  const inSquare = Math.abs(rx) < 39 && Math.abs(rz) < 39;
  const onMound = Math.hypot(x, z - MOUND_Z) < 10;
  // outfield grass beyond the infield dirt, in front of the warning track
  const r = Math.hypot(x, z);
  const fair = z < 0 && Math.abs(x) < -z;
  const outfield = fair && Math.hypot(x, z - MOUND_Z) > 96 && r < FENCE_R - 18;
  return (inSquare && !onMound) || outfield;
}

/** One instanced mesh of 3-segment blades, denser near home plate (where the cameras are) and thinning out. */
export function GrassBlades({ count, animate }: { count: number; animate: boolean }) {
  const ref = useRef<THREE.Mesh>(null);
  const geo = useMemo(() => {
    const blade = new THREE.PlaneGeometry(1, 1, 1, 3).translate(0, 0.5, 0);
    const g = new THREE.InstancedBufferGeometry();
    g.index = blade.index;
    g.setAttribute('position', blade.getAttribute('position'));
    const data = new Float32Array(count * 4);
    let s = 7;
    const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
    let k = 0;
    while (k < count) {
      // radius from home plate biased toward the plate: most blades where the camera looks closely
      const rad = 14 + Math.pow(r(), 1.8) * 300;
      const a = (r() - 0.5) * (Math.PI / 2) * 1.02;
      const x = Math.sin(a) * rad, z = -Math.cos(a) * rad;
      if (!insideGrass(x, z)) continue;
      data.set([x, z, 0.22 + r() * 0.16, r()], k * 4);
      k++;
    }
    g.setAttribute('aBlade', new THREE.InstancedBufferAttribute(data, 4));
    g.instanceCount = count;
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, -150), 400);
    return g;
  }, [count]);
  const mat = useMemo(() => new THREE.ShaderMaterial({
    vertexShader: BLADE_VERT,
    fragmentShader: BLADE_FRAG,
    uniforms: {
      uTime: { value: 0 },
      uSun: { value: SUN.clone() },
      uRoot: { value: new THREE.Color('#2c5222') },
      uTip: { value: new THREE.Color('#6c9f4c') },
      fogColor: { value: new THREE.Color('#a9cff5') },
      fogNear: { value: 700 },
      fogFar: { value: 4200 },
    },
    side: THREE.DoubleSide,
  }), []);
  useFrame(({ clock }) => {
    if (animate) mat.uniforms.uTime.value = clock.elapsedTime;
  });
  return <mesh ref={ref} geometry={geo} material={mat} frustumCulled={false} />;
}
