/* Broadcast tracking look (Statcast-style): a dark field drawn with chalk lines under a night sky, a glass strike
   zone, the two flights as light tubes with "pearls" every 1/30 s, and labels hung in the scene. Units are feet;
   home plate's back tip at the origin, the mound toward -z. Harp Helú air = red, sea level = grey (web/DESIGN.md). */
import { Suspense, useLayoutEffect, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html, Line } from '@react-three/drei';
import * as THREE from 'three';
import { STANCE, type Look, type Pose } from './figures';
import { Mannequin } from './mannequin';
import { batterFrame, BALL_R, MOUND_H, MOUND_Z, ZONE, type Hand, type Palette, type ParkSide, type Vec3 } from './sceneModel';

const FT = 3.28084;
const BASE = 90 / Math.SQRT2;
/** Path points are every 4 RK4 steps of 1/240 s. */
export const PATH_DT = 4 / 240;

/* ---------------------------------- sky ---------------------------------- */

const SKY_VERT = /* glsl */ `
  varying vec3 vDir;
  void main() {
    vDir = normalize(position);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }`;
const SKY_FRAG = /* glsl */ `
  uniform vec3 zenith; uniform vec3 mid; uniform vec3 horizon; uniform vec3 glow; uniform vec3 moonDir; uniform vec3 moonColor;
  varying vec3 vDir;
  void main() {
    float h = vDir.y;
    vec3 col = mix(mid, zenith, smoothstep(0.08, 0.75, h));
    col = mix(horizon, col, smoothstep(-0.02, 0.22, h));
    // city / sea glow hugging the horizon
    col += glow * exp(-max(h, 0.0) * 14.0) * 0.9;
    // moon halo
    float m = max(dot(normalize(vDir), normalize(moonDir)), 0.0);
    col += moonColor * (pow(m, 900.0) * 1.6 + pow(m, 40.0) * 0.12);
    if (h < 0.0) col = mix(horizon, vec3(0.02, 0.025, 0.03), smoothstep(0.0, -0.25, h));
    // dither so the gradient never bands
    float n = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453);
    col += (n - 0.5) / 255.0;
    gl_FragColor = vec4(col, 1.0);
  }`;

export function NightSky({ park }: { park: ParkSide }) {
  const uniforms = useMemo(() => {
    const harp = park === 'harp';
    return {
      zenith: { value: new THREE.Color(harp ? '#050a1a' : '#04101e') },
      mid: { value: new THREE.Color(harp ? '#142347' : '#123352') },
      horizon: { value: new THREE.Color(harp ? '#33395a' : '#24506c') },
      glow: { value: new THREE.Color(harp ? '#b0683a' : '#4d7f9c') },
      moonDir: { value: new THREE.Vector3(harp ? -0.55 : 0.45, harp ? 0.42 : 0.3, -1) },
      moonColor: { value: new THREE.Color('#f2efe6') },
    };
  }, [park]);
  const stars = useMemo(() => {
    let s = 2240;
    const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
    const n = 1400;
    const pos = new Float32Array(n * 3);
    const col = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const u = r(), v = 0.08 + 0.92 * r();
      const th = u * Math.PI * 2, ph = Math.asin(v);
      const R = 1500;
      pos.set([R * Math.cos(ph) * Math.sin(th), R * Math.sin(ph), R * Math.cos(ph) * Math.cos(th)], i * 3);
      const b = 0.45 + 0.55 * r() * r();
      col.set([b, b, b * (0.92 + 0.08 * r())], i * 3);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    return g;
  }, []);
  const moon = uniforms.moonDir.value.clone().normalize().multiplyScalar(1450);
  return (
    <group>
      <mesh renderOrder={-2}>
        <sphereGeometry args={[1700, 48, 24]} />
        <shaderMaterial vertexShader={SKY_VERT} fragmentShader={SKY_FRAG} uniforms={uniforms} side={THREE.BackSide}
          depthWrite={false} fog={false} />
      </mesh>
      <points geometry={stars} renderOrder={-1}>
        <pointsMaterial size={2.2} sizeAttenuation={false} vertexColors transparent opacity={0.9} depthWrite={false} fog={false} />
      </points>
      <mesh position={moon}>
        <circleGeometry args={[26, 48]} />
        <meshBasicMaterial color="#f4f1e8" fog={false} toneMapped={false} />
      </mesh>
    </group>
  );
}

/** CDMX: Popocatépetl and Iztaccíhuatl as silhouettes with moonlit snow; sea level: dark water with a moon path. */
export function Horizon({ park }: { park: ParkSide }) {
  if (park === 'harp') {
    const ridge = (x: number, z: number, r: number, h: number, sx: number, snow: number, seg: number) => (
      <group position={[x, h / 2 - 20, z]} scale={[sx, 1, 1]}>
        <mesh>
          <coneGeometry args={[r, h, seg]} />
          <meshBasicMaterial color="#121729" fog={false} />
        </mesh>
        <mesh position={[0, h / 2 - (h * snow) / 2, 0]}>
          <coneGeometry args={[r * snow, h * snow, seg]} />
          <meshBasicMaterial color="#9aa2b5" fog={false} />
        </mesh>
      </group>
    );
    return (
      <group>
        {ridge(-560, -1550, 420, 330, 1.25, 0.22, 11)}
        {ridge(640, -1600, 260, 250, 3.0, 0.16, 9)}
        {ridge(40, -1500, 900, 90, 2.4, 0.0001, 7)}
        {/* city lights strip at the foot of the mountains */}
        {Array.from({ length: 120 }, (_, i) => (
          <mesh key={i} position={[-1300 + i * 22 + ((i * 37) % 11), 3 + ((i * 13) % 6), -1350 - ((i * 53) % 90)]}>
            <boxGeometry args={[2.4, 2.4, 2.4]} />
            <meshBasicMaterial color={i % 5 === 0 ? '#f3d9a6' : '#d9a865'} fog={false} toneMapped={false} />
          </mesh>
        ))}
      </group>
    );
  }
  return (
    <group>
      <mesh position={[0, -2, -1000]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[4000, 1400]} />
        <meshStandardMaterial color="#061420" roughness={0.12} metalness={0.7} fog={false} />
      </mesh>
      <mesh position={[650, -1.5, -1000]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[60, 1300]} />
        <meshBasicMaterial color="#c9ccd3" transparent opacity={0.08} fog={false} depthWrite={false} />
      </mesh>
    </group>
  );
}

/* --------------------------------- field --------------------------------- */

function circle(cx: number, cz: number, r: number, n = 96, y = 0.05): Vec3[] {
  return Array.from({ length: n + 1 }, (_, i) => {
    const a = (i / n) * Math.PI * 2;
    return [cx + r * Math.cos(a), y, cz + r * Math.sin(a)] as Vec3;
  });
}

export function TrackedField({ c }: { c: Palette }) {
  const chalk = c.chalk;
  const grid = useMemo(() => {
    const g = new THREE.GridHelper(600, 120, '#1b2230', '#121821');
    (g.material as THREE.Material).transparent = true;
    (g.material as THREE.Material).opacity = 0.55;
    return g;
  }, []);
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
  const arc = (r: number) => Array.from({ length: 61 }, (_, i) => {
    const a = -Math.PI / 4 + (i / 60) * (Math.PI / 2);
    return [r * Math.sin(a), 0.05, MOUND_Z - r * Math.cos(a)] as Vec3;
  });
  const box = (sx: number): Vec3[] => {
    const zMid = -0.7, xi = sx * 1.21, xo = sx * 5.21;
    return [[xi, 0.06, zMid + 3], [xo, 0.06, zMid + 3], [xo, 0.06, zMid - 3], [xi, 0.06, zMid - 3], [xi, 0.06, zMid + 3]];
  };
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]}>
        <circleGeometry args={[1400, 64]} />
        <meshBasicMaterial color="#0b1219" />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, MOUND_Z]}>
        <circleGeometry args={[95, 64]} />
        <meshBasicMaterial color="#121a24" />
      </mesh>
      <primitive object={grid} position={[0, 0, -150]} />
      {[-1, 1].map((s) => <Line key={s} points={[[0, 0.05, 0], [s * 240, 0.05, -240]]} color={chalk} lineWidth={1.6} transparent opacity={0.75} />)}
      <Line points={arc(95)} color={chalk} lineWidth={1} transparent opacity={0.25} />
      <Line points={circle(0, MOUND_Z, 9)} color={chalk} lineWidth={1.4} transparent opacity={0.6} />
      <Line points={circle(0, -0.8, 13)} color={chalk} lineWidth={1} transparent opacity={0.3} />
      {[box(-1), box(1)].map((pts, i) => <Line key={i} points={pts} color={chalk} lineWidth={1.4} transparent opacity={0.7} />)}
      {([[BASE, -BASE], [0, -BASE * 2], [-BASE, -BASE]] as const).map(([x, z]) => (
        <mesh key={`${x}${z}`} position={[x, 0.05, z]} rotation={[-Math.PI / 2, 0, Math.PI / 4]}>
          <planeGeometry args={[1.25, 1.25]} />
          <meshBasicMaterial color={chalk} transparent opacity={0.8} />
        </mesh>
      ))}
      <mesh position={[0, MOUND_H + 0.02, MOUND_Z]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[2, 0.5]} />
        <meshBasicMaterial color={chalk} />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0.06, 0]}>
        <shapeGeometry args={[plate]} />
        <meshBasicMaterial color={chalk} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

/** Glass strike zone: a box over the plate, brighter front edges, a faint 3 x 3 grid on the front face. */
export function ZoneGlass({ c }: { c: Palette }) {
  const { half: h, bottom: b, top: t, z } = ZONE;
  const d = 17 / 12;
  const third = (t - b) / 3;
  return (
    <group>
      <mesh position={[0, (b + t) / 2, z / 2]}>
        <boxGeometry args={[2 * h, t - b, d]} />
        <meshBasicMaterial color={c.fg} transparent opacity={0.045} depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      <Line points={[[-h, b, z], [h, b, z], [h, t, z], [-h, t, z], [-h, b, z]]} color={c.fg} lineWidth={2} transparent opacity={0.9} />
      <Line points={[[-h, b, 0], [h, b, 0], [h, t, 0], [-h, t, 0], [-h, b, 0]]} color={c.fg} lineWidth={1} transparent opacity={0.3} />
      {([[-h, b], [h, b], [h, t], [-h, t]] as const).map(([x, y]) => (
        <Line key={`${x}${y}`} points={[[x, y, z], [x, y, 0]]} color={c.fg} lineWidth={1} transparent opacity={0.3} />
      ))}
      {[1, 2].map((i) => (
        <group key={i}>
          <Line points={[[-h + (2 * h * i) / 3, b, z], [-h + (2 * h * i) / 3, t, z]]} color={c.fg} lineWidth={1} transparent opacity={0.22} />
          <Line points={[[-h, b + third * i, z], [h, b + third * i, z]]} color={c.fg} lineWidth={1} transparent opacity={0.22} />
        </group>
      ))}
    </group>
  );
}

/* --------------------------------- flights -------------------------------- */

/** A tube along the path that widens toward the catcher (like broadcast tracking), revealed with drawRange. */
function useWideTube(points: Vec3[], r0: number, r1: number, radial = 10) {
  return useMemo(() => {
    const curve = new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(...p)));
    const segs = Math.max(8, points.length * 2);
    const g = new THREE.TubeGeometry(curve, segs, 1, radial, false);
    const pos = g.attributes.position as THREE.BufferAttribute;
    const c = new THREE.Vector3(), v = new THREE.Vector3();
    for (let i = 0; i <= segs; i++) {
      curve.getPointAt(i / segs, c);
      const r = r0 + (r1 - r0) * (i / segs);
      for (let j = 0; j <= radial; j++) {
        const k = i * (radial + 1) + j;
        v.fromBufferAttribute(pos, k).sub(c).multiplyScalar(r).add(c);
        pos.setXYZ(k, v.x, v.y, v.z);
      }
    }
    pos.needsUpdate = true;
    g.computeVertexNormals();
    return { g, segs, radial };
  }, [points, r0, r1, radial]);
}

export interface FlightTiming { windup: number; duration: number }

function Trail({ points, color, glow, opacity, r0, r1, reduced, startRef, timing }: {
  points: Vec3[]; color: string; glow: boolean; opacity: number; r0: number; r1: number; reduced: boolean;
  startRef: React.MutableRefObject<number>; timing: FlightTiming;
}) {
  const { g, segs, radial } = useWideTube(points, r0, r1);
  const pearls = useRef<THREE.InstancedMesh>(null);
  const every = 2; // a pearl every 2 points = 1/30 s
  const n = Math.ceil(points.length / every);
  useLayoutEffect(() => {
    const m = pearls.current;
    if (!m) return;
    const o = new THREE.Object3D();
    for (let i = 0; i < n; i++) {
      const p = points[Math.min(points.length - 1, i * every)];
      o.position.set(...p);
      o.scale.setScalar(0.75 + 0.35 * (i / Math.max(1, n - 1)));
      o.updateMatrix();
      m.setMatrixAt(i, o.matrix);
    }
    m.instanceMatrix.needsUpdate = true;
  }, [points, n]);
  useFrame(({ clock }) => {
    const t = clock.elapsedTime - startRef.current - timing.windup;
    const u = reduced || startRef.current < 0 ? 1 : Math.min(1, Math.max(0, t / timing.duration));
    g.setDrawRange(0, Math.floor(u * segs) * radial * 6);
    if (pearls.current) pearls.current.count = Math.floor(u * n);
  });
  return (
    <group>
      <mesh geometry={g}>
        {glow ? (
          <meshStandardMaterial color={color} emissive={color} emissiveIntensity={1.6} toneMapped={false} transparent opacity={opacity} />
        ) : (
          <meshBasicMaterial color={color} transparent opacity={opacity} depthWrite={false} />
        )}
      </mesh>
      <instancedMesh ref={pearls} args={[undefined, undefined, n]}>
        <sphereGeometry args={[BALL_R, 14, 10]} />
        <meshBasicMaterial color={color} transparent opacity={glow ? 0.55 : 0.35} depthWrite={false} toneMapped={!glow} />
      </instancedMesh>
    </group>
  );
}

function inches(a: Vec3, b: Vec3) {
  return Math.hypot(a[0] - b[0], a[1] - b[1]) * 12;
}

function Tag({ at, children, tone }: { at: Vec3; children: React.ReactNode; tone: 'hh' | 'sea' | 'note' }) {
  return (
    <Html position={at} center={false} zIndexRange={[6, 0]} style={{ pointerEvents: 'none' }}>
      <div className={`sim-tag sim-tag-${tone}`}>{children}</div>
    </Html>
  );
}

/** Both trails, the moving ball, the decision point 150 ms before the plate, plate marks and the gap label. */
export function TrackedFlights({ harp, sea, c, reduced, playId, timing, ball }: {
  harp: Vec3[]; sea: Vec3[]; c: Palette; reduced: boolean; playId: number; timing: FlightTiming; ball: React.ReactNode;
}) {
  const start = useRef(-1);
  useFrame(({ clock }) => {
    if (start.current < 0) start.current = clock.elapsedTime;
  });
  useLayoutEffect(() => { start.current = -1; }, [playId, harp, sea]);
  const back = Math.round(0.15 / PATH_DT); // points before the plate = 150 ms
  const dH = harp[Math.max(0, harp.length - 1 - back)];
  const dS = sea[Math.max(0, sea.length - 1 - back)];
  const eH = harp[harp.length - 1], eS = sea[sea.length - 1];
  const decisionGap = inches(dH, dS);
  const plateGap = inches(eH, eS);
  const rel = harp[0];
  return (
    <group>
      <Trail points={sea} color={c.sea} glow={false} opacity={0.32} r0={0.03} r1={0.07} reduced={reduced} startRef={start} timing={timing} />
      <Trail points={harp} color={c.red} glow opacity={0.85} r0={0.035} r1={0.085} reduced={reduced} startRef={start} timing={timing} />
      {ball}
      {/* release point with a drop line */}
      <mesh position={rel}>
        <ringGeometry args={[BALL_R * 0.9, BALL_R * 1.3, 32]} />
        <meshBasicMaterial color={c.fg} side={THREE.DoubleSide} />
      </mesh>
      <Line points={[rel, [rel[0], 0.05, rel[2]]]} color={c.fg} lineWidth={1} dashed dashSize={0.25} gapSize={0.2} transparent opacity={0.5} />
      {/* decision point: still together here */}
      <Line points={[[dH[0], 0.05, dH[2]], dH]} color={c.fg} lineWidth={1} transparent opacity={0.35} />
      <mesh position={dH} rotation={[0, 0, 0]}>
        <ringGeometry args={[0.22, 0.26, 40]} />
        <meshBasicMaterial color={c.fg} transparent opacity={0.8} side={THREE.DoubleSide} />
      </mesh>
      <Tag at={[dH[0] + 0.35, dH[1] + 0.35, dH[2]]} tone="note">
        <b>punto de decisión</b> · 150 ms antes del plato · separación {decisionGap.toFixed(1)} in
      </Tag>
      {/* plate crossings */}
      <mesh position={[eS[0], eS[1], ZONE.z + 0.02]}>
        <ringGeometry args={[BALL_R * 0.7, BALL_R * 1.1, 32]} />
        <meshBasicMaterial color={c.sea} side={THREE.DoubleSide} />
      </mesh>
      <mesh position={[eH[0], eH[1], ZONE.z + 0.03]}>
        <circleGeometry args={[BALL_R * 1.1, 32]} />
        <meshBasicMaterial color={c.red} side={THREE.DoubleSide} toneMapped={false} />
      </mesh>
      <Line points={[[eS[0], eS[1], ZONE.z + 0.02], [eH[0], eH[1], ZONE.z + 0.02]]} color={c.fg} lineWidth={1.4} />
      <Tag at={[Math.max(eH[0], eS[0]) + 0.25, (eH[1] + eS[1]) / 2, ZONE.z]} tone="hh">
        {plateGap.toFixed(1)} in en el plato
      </Tag>
    </group>
  );
}

/* --------------------------------- batter --------------------------------- */

const GHOST: Look = { jersey: '#c9ccd3', pants: '#c9ccd3', skin: '#c9ccd3', dark: '#e8e6e1', helmet: '#c9ccd3' };
const HOME: Look = { jersey: '#f1efe9', pants: '#e6e2d8', skin: '#9a7a62', dark: '#16161a', helmet: '#b3122b' };
const KIT = { base: '#f3f1ec', trim: '#b3122b', dark: '#16161a', skin: '#a07a5e', number: '24', name: 'Diablos' };

/** Translucent batter in his stance; switches sides with the same walk-behind-the-plate move. */
export function GhostBatter({ hand, reduced, solid = false }: { hand: Hand; reduced: boolean; solid?: boolean }) {
  const ref = useRef<THREE.Group>(null);
  const pose = useRef<Pose>(STANCE);
  const swap = useRef({ from: hand, to: hand, t: 1 });
  if (swap.current.to !== hand) swap.current = { from: swap.current.to, to: hand, t: reduced ? 1 : 0 };
  const bat = useRef<THREE.Mesh>(null);
  useFrame((_, dt) => {
    const g = ref.current;
    if (!g) return;
    const s = swap.current;
    s.t = reduced ? 1 : Math.min(1, s.t + dt / 0.72);
    const f = batterFrame(s.from, s.to, s.t);
    g.position.set(f.x, f.y, f.z);
    g.scale.set(f.mirror, 1, 1);
  });
  const toRig = (q: Vec3) => new THREE.Vector3(-q[2] / FT, q[1] / FT, q[0] / FT);
  const placeBat = (l: THREE.Vector3, r: THREE.Vector3) => {
    const m = bat.current;
    if (!m) return;
    const dir = new THREE.Vector3(-0.42, 0.88, -0.22).normalize();
    m.position.copy(l.clone().lerp(r, 0.5)).addScaledVector(dir, 0.4);
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
  };
  return (
    <group ref={ref}>
      <Suspense fallback={null}>
        <group rotation={[0, Math.PI / 2, 0]}>
          <Mannequin pose={pose} look={solid ? HOME : GHOST} toRig={toRig} onPosed={placeBat} ghost={!solid} helmet={solid} kit={solid ? KIT : undefined}>
            <mesh ref={bat} castShadow={solid}>
              <cylinderGeometry args={[0.034, 0.014, 0.86, 12]} />
              {solid ? <meshStandardMaterial color="#b0875c" roughness={0.4} />
                : <meshBasicMaterial color="#c9ccd3" transparent opacity={0.22} depthWrite={false} />}
            </mesh>
          </Mannequin>
        </group>
      </Suspense>
    </group>
  );
}
