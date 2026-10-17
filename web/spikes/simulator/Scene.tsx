/* The 3D scene (react-three-fiber only; no Motion in this tree, per web/DESIGN.md). Low-poly, flat shading.
   World units are feet: x = catcher's right, y up, z toward the catcher; home plate's back tip at the origin. */
import { useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Html, Line } from '@react-three/drei';
import * as THREE from 'three';
import { DT, PLATE_FRONT_FT, positionAt, type Flight, type Vec3 } from './flight';
import { fmt, toWorld, type Hand, type Throw } from './model';

export type View = 'catcher' | 'pitcher' | 'lateral' | 'broadcast';

/* Colors come from tokens.css at runtime; the fallbacks are the same values (feat/hack-039). */
function token(name: string, fallback: string) {
  if (typeof document === 'undefined') return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}
function palette() {
  return {
    bg: token('--bg', '#0c0c0e'),
    surface: token('--surface-2', '#1c1c21'),
    fg: token('--fg', '#f1f1f3'),
    red: token('--red', '#c8102e'),
    sea: token('--sea', '#c9ccd3'),
    grass: token('--grass', '#2f4a35'),
    grassDark: token('--grass-dark', '#263d2c'),
    dirt: token('--dirt', '#6b4f3a'),
    chalk: token('--chalk', '#e8e6e1'),
    ball: token('--ball', '#efece6'),
  };
}
type Palette = ReturnType<typeof palette>;

const BALL_R = 2.9 / 2 / 12;
const ZONE = { half: 17 / 24, bottom: 1.5, top: 3.5 };
const PLATE_Z = -PLATE_FRONT_FT;
const MOUND_H = 10 / 12;

export const VIEWS: Record<View, { pos: Vec3; target: Vec3; fov: number }> = {
  catcher: { pos: [0, 6.0, 20], target: [0, 2.5, -25], fov: 21 },
  pitcher: { pos: [1.2, 12, -82], target: [0, 2.6, 0], fov: 12 },
  lateral: { pos: [-88, 5, -30], target: [0, 3.8, -30], fov: 34 },
  broadcast: { pos: [-10, 14, -170], target: [0, 3.0, 0], fov: 5.2 },
};

/* ---------- camera ---------- */
/** On wide screens the right rail and the readout cover part of the canvas: shift the frame so the scene centers in
 *  the free area. */
const FRAME_SHIFT = { x: 150, y: 30, minWidth: 900 };

function CameraRig({ view, reduced }: { view: View; reduced: boolean }) {
  const { camera, size } = useThree();
  useEffect(() => {
    const cam = camera as THREE.PerspectiveCamera;
    if (size.width >= FRAME_SHIFT.minWidth) cam.setViewOffset(size.width, size.height, FRAME_SHIFT.x, FRAME_SHIFT.y, size.width, size.height);
    else cam.clearViewOffset();
  }, [camera, size]);
  const target = useRef(new THREE.Vector3(...VIEWS[view].target));
  const first = useRef(true);
  useFrame((_, dt) => {
    const v = VIEWS[view];
    const cam = camera as THREE.PerspectiveCamera;
    const snap = reduced || first.current;
    first.current = false;
    const k = snap ? 1 : 1 - Math.exp(-4.5 * Math.min(dt, 0.1));
    cam.position.lerp(new THREE.Vector3(...v.pos), k);
    target.current.lerp(new THREE.Vector3(...v.target), k);
    cam.fov += (v.fov - cam.fov) * k;
    cam.updateProjectionMatrix();
    cam.lookAt(target.current);
  });
  return null;
}

/* ---------- field ---------- */
function Flat({ color, ...props }: { color: string } & JSX.IntrinsicElements['mesh']) {
  return (
    <mesh {...props}>
      {props.children}
      <meshStandardMaterial color={color} flatShading roughness={0.95} />
    </mesh>
  );
}

function Field({ c }: { c: Palette }) {
  const plate = useMemo(() => {
    const s = new THREE.Shape();
    s.moveTo(-ZONE.half, PLATE_FRONT_FT);
    s.lineTo(ZONE.half, PLATE_FRONT_FT);
    s.lineTo(ZONE.half, ZONE.half);
    s.lineTo(0, 0);
    s.lineTo(-ZONE.half, ZONE.half);
    s.closePath();
    return s;
  }, []);
  const flat: [number, number, number] = [-Math.PI / 2, 0, 0];
  const boxes = useMemo(() => {
    const zMid = -PLATE_FRONT_FT / 2;
    const box = (sx: number): Vec3[] => {
      const xi = sx * (ZONE.half + 0.5), xo = sx * (ZONE.half + 4.5);
      return [[xi, 0.07, zMid + 3], [xo, 0.07, zMid + 3], [xo, 0.07, zMid - 3], [xi, 0.07, zMid - 3], [xi, 0.07, zMid + 3]];
    };
    return [box(-1), box(1)];
  }, []);
  return (
    <group>
      <Flat color={c.grass} rotation={flat}>
        <circleGeometry args={[620, 48]} />
      </Flat>
      {[-3, -1, 1, 3, 5, 7].map((i) => (
        <Flat key={i} color={c.grassDark} rotation={[-Math.PI / 2, 0, 0]} position={[i * 26, 0.01, -260]}>
          <planeGeometry args={[13, 300]} />
        </Flat>
      ))}
      <Flat color={c.dirt} rotation={flat} position={[0, 0.03, -60.5]}>
        <circleGeometry args={[95, 40]} />
      </Flat>
      <Flat color={c.grass} rotation={[-Math.PI / 2, 0, Math.PI / 4]} position={[0, 0.05, -63.64]}>
        <planeGeometry args={[78, 78]} />
      </Flat>
      <Flat color={c.dirt} rotation={flat} position={[0, 0.07, -0.7]}>
        <circleGeometry args={[13, 24]} />
      </Flat>
      {/* mound and rubber */}
      <Flat color={c.dirt} position={[0, MOUND_H / 2 + 0.05, -60.5]}>
        <cylinderGeometry args={[2.6, 9, MOUND_H, 14]} />
      </Flat>
      <Flat color={c.chalk} position={[0, MOUND_H + 0.08, -60.5]}>
        <boxGeometry args={[2, 0.08, 0.5]} />
      </Flat>
      {/* bases */}
      {([[63.64, -63.64], [0, -127.28], [-63.64, -63.64]] as const).map(([x, z]) => (
        <Flat key={`${x}${z}`} color={c.chalk} position={[x, 0.25, z]} rotation={[0, Math.PI / 4, 0]}>
          <boxGeometry args={[1.25, 0.3, 1.25]} />
        </Flat>
      ))}
      {/* home plate, foul lines, batter's boxes */}
      <Flat color={c.chalk} rotation={[Math.PI / 2, 0, 0]} position={[0, 0.09, 0]}>
        <shapeGeometry args={[plate]} />
      </Flat>
      {[-1, 1].map((s) => (
        <Flat key={s} color={c.chalk} position={[(s * 330) / Math.SQRT2 / 2, 0.08, -330 / Math.SQRT2 / 2]} rotation={[-Math.PI / 2, 0, (s * Math.PI) / 4]}>
          <planeGeometry args={[0.33, 330]} />
        </Flat>
      ))}
      {boxes.map((pts, i) => (
        <Line key={i} points={pts} color={c.chalk} lineWidth={1.4} />
      ))}
      <Stadium c={c} />
    </group>
  );
}

function Stadium({ c }: { c: Palette }) {
  return (
    <group>
      {/* outfield wall and stands: faceted rings around home plate */}
      <Flat color="#15181a" position={[0, 5, 0]}>
        <cylinderGeometry args={[340, 340, 10, 40, 1, true, Math.PI * 0.62, Math.PI * 0.76]} />
      </Flat>
      <mesh position={[0, 40, 0]}>
        <cylinderGeometry args={[470, 355, 70, 40, 1, true, Math.PI * 0.45, Math.PI * 1.1]} />
        <meshStandardMaterial color={c.surface} flatShading side={THREE.DoubleSide} roughness={1} />
      </mesh>
      {/* light towers: two banks, the only lights in the park */}
      {[-1, 1].map((s) => (
        <group key={s} position={[s * 230, 0, -170]}>
          <Flat color="#202329" position={[0, 60, 0]}>
            <boxGeometry args={[3, 120, 3]} />
          </Flat>
          <mesh position={[0, 122, 0]} rotation={[0.35, -s * 0.6, 0]}>
            <boxGeometry args={[30, 12, 2]} />
            <meshStandardMaterial color={c.chalk} emissive={c.chalk} emissiveIntensity={0.9} flatShading />
          </mesh>
        </group>
      ))}
    </group>
  );
}

/* ---------- figures ---------- */
function Limb({ from, to, r0, r1 = r0, color }: { from: Vec3; to: Vec3; r0: number; r1?: number; color: string }) {
  const { pos, quat, len } = useMemo(() => {
    const a = new THREE.Vector3(...from), b = new THREE.Vector3(...to);
    const d = b.clone().sub(a);
    return {
      pos: a.clone().add(b).multiplyScalar(0.5),
      quat: new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.clone().normalize()),
      len: d.length(),
    };
  }, [from, to]);
  return (
    <mesh position={pos} quaternion={quat}>
      <cylinderGeometry args={[r1, r0, len, 6]} />
      <meshStandardMaterial color={color} flatShading roughness={0.8} />
    </mesh>
  );
}

const JERSEY_HOME = '#d9d7d2';
const JERSEY_AWAY = '#8d9097';
const HELMET = '#23252b';
const BAT = '#a07a52';
const SKIN = '#9a7a62';

/** A limb through several joints (cylinders plus a small joint ball to hide the seams). */
function Chain({ pts, r, color }: { pts: Vec3[]; r: number; color: string }) {
  return (
    <group>
      {pts.slice(1).map((p, i) => (
        <Limb key={i} from={pts[i]} to={p} r0={r} r1={r * 0.85} color={color} />
      ))}
      {pts.slice(1, -1).map((p, i) => (
        <mesh key={`j${i}`} position={p}>
          <icosahedronGeometry args={[r * 0.95, 0]} />
          <meshStandardMaterial color={color} flatShading />
        </mesh>
      ))}
    </group>
  );
}

function Box({ at, size, color, rot }: { at: Vec3; size: Vec3; color: string; rot?: Vec3 }) {
  return (
    <mesh position={at} rotation={rot}>
      <boxGeometry args={size} />
      <meshStandardMaterial color={color} flatShading roughness={0.85} />
    </mesh>
  );
}

function Head({ at, color }: { at: Vec3; color: string }) {
  return (
    <group position={at}>
      <mesh>
        <icosahedronGeometry args={[0.34, 0]} />
        <meshStandardMaterial color={SKIN} flatShading />
      </mesh>
      <mesh position={[0, 0.08, 0]}>
        <sphereGeometry args={[0.4, 8, 4, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshStandardMaterial color={color} flatShading />
      </mesh>
    </group>
  );
}

/** Batter in local coords: chest toward +x (the plate), pitcher toward -z. Mirrored with scale.x for a lefty. */
function BatterBody() {
  const j = JERSEY_HOME;
  return (
    <group>
      <Chain pts={[[0, 3.05, -0.42], [0.38, 1.65, -0.95], [0.18, 0.28, -1.3]]} r={0.22} color={j} />
      <Chain pts={[[0, 3.05, 0.42], [0.32, 1.65, 0.98], [0.06, 0.28, 1.22]]} r={0.22} color={j} />
      <Box at={[0.42, 0.14, -1.3]} size={[0.85, 0.28, 0.36]} color={HELMET} />
      <Box at={[0.3, 0.14, 1.22]} size={[0.85, 0.28, 0.36]} color={HELMET} />
      <Box at={[0, 3.12, 0]} size={[0.72, 0.55, 1.12]} color={j} />
      <Limb from={[0.04, 3.3, 0]} to={[0.24, 4.85, 0.04]} r0={0.5} r1={0.6} color={j} />
      <Box at={[0.26, 4.98, 0.04]} size={[0.55, 0.36, 1.42]} color={j} />
      <Limb from={[0.3, 5.1, 0]} to={[0.33, 5.42, -0.01]} r0={0.16} color={SKIN} />
      <Head at={[0.34, 5.7, -0.02]} color={HELMET} />
      <Chain pts={[[0.26, 4.98, -0.66], [0.78, 4.52, -0.08], [0.46, 5.12, 0.56]]} r={0.13} color={j} />
      <Chain pts={[[0.26, 4.98, 0.7], [0.36, 4.55, 1.05], [0.46, 5.08, 0.62]]} r={0.13} color={j} />
      <Limb from={[0.46, 5.1, 0.6]} to={[-0.16, 7.62, 1.45]} r0={0.05} r1={0.115} color={BAT} />
    </group>
  );
}

/** Pitcher at release, local coords: +z toward home plate, +x = arm side, y from the mound top. The throwing hand is
 *  at the release point (side, height, extension) so the ball leaves from it. */
function PitcherBody({ side, height, ext }: { side: number; height: number; ext: number }) {
  const j = JERSEY_AWAY;
  const hand: Vec3 = [side, height - MOUND_H, ext];
  const shoulder: Vec3 = [0.75, 4.75, 3.9];
  const elbow: Vec3 = [(shoulder[0] + hand[0]) / 2 + 0.15, (shoulder[1] + hand[1]) / 2 + 0.3, (shoulder[2] + hand[2]) / 2];
  return (
    <group>
      <Chain pts={[[0.35, 3.0, 2.0], [0.62, 1.5, 1.2], [0.55, 0.32, 0.1]]} r={0.22} color={j} />
      <Chain pts={[[-0.35, 3.0, 2.3], [-0.42, 1.85, 3.9], [-0.42, 0.24, 4.5]]} r={0.22} color={j} />
      <Box at={[0.55, 0.15, 0.25]} size={[0.36, 0.28, 0.85]} color={HELMET} rot={[0.5, 0, 0]} />
      <Box at={[-0.42, 0.14, 4.75]} size={[0.36, 0.28, 0.85]} color={HELMET} />
      <Box at={[0, 3.08, 2.15]} size={[1.1, 0.55, 0.7]} color={j} />
      <Limb from={[0, 3.25, 2.2]} to={[0.18, 4.6, 3.75]} r0={0.5} r1={0.6} color={j} />
      <Box at={[0.15, 4.72, 3.85]} size={[1.45, 0.36, 0.55]} color={j} rot={[0.5, 0, 0]} />
      <Head at={[0.12, 5.25, 4.3]} color={HELMET} />
      <Chain pts={[shoulder, elbow, hand]} r={0.13} color={j} />
      <Chain pts={[[-0.55, 4.7, 3.8], [-0.98, 4.05, 3.6], [-0.7, 3.62, 3.25]]} r={0.13} color={j} />
      <Box at={[-0.66, 3.55, 3.2]} size={[0.32, 0.42, 0.24]} color="#3b2c22" />
    </group>
  );
}

const BATTER_X = 2.9;
const BATTER_Z = -0.7;
const SWITCH_S = 0.75;

/** Walks behind the plate and mirrors (scale.x through 0) when the side changes. */
function Batter({ side, reduced }: { side: Hand; reduced: boolean }) {
  const ref = useRef<THREE.Group>(null);
  const anim = useRef({ from: side, to: side, t: 1 });
  if (anim.current.to !== side) anim.current = { from: anim.current.to, to: side, t: reduced ? 1 : 0 };
  useFrame((_, dt) => {
    const g = ref.current;
    if (!g) return;
    const a = anim.current;
    a.t = Math.min(1, a.t + dt / SWITCH_S);
    const u = a.t < 0.5 ? 2 * a.t * a.t : 1 - (-2 * a.t + 2) ** 2 / 2;
    const sx = (h: Hand) => (h === 'R' ? -1 : 1);
    const x0 = sx(a.from) * BATTER_X, x1 = sx(a.to) * BATTER_X;
    const arc = Math.sin(Math.PI * u);
    g.position.set(x0 + (x1 - x0) * u, 0.6 * arc, BATTER_Z + 3.4 * arc);
    const m0 = a.from === 'R' ? 1 : -1, m1 = a.to === 'R' ? 1 : -1;
    const m = m0 + (m1 - m0) * u;
    g.scale.set(Math.abs(m) < 0.02 ? 0.02 * Math.sign(m1) : m, 1, 1);
  });
  return (
    <group ref={ref}>
      <BatterBody />
    </group>
  );
}

/* ---------- zone, balls, trails ---------- */
function Zone({ c }: { c: Palette }) {
  const z = PLATE_Z;
  const { half: h, bottom: b, top: t } = ZONE;
  const third = (t - b) / 3;
  return (
    <group>
      <Line points={[[-h, b, z], [h, b, z], [h, t, z], [-h, t, z], [-h, b, z]]} color={c.fg} lineWidth={1.6} transparent opacity={0.7} />
      {[1, 2].map((i) => (
        <group key={i}>
          <Line points={[[-h + (2 * h * i) / 3, b, z], [-h + (2 * h * i) / 3, t, z]]} color={c.fg} lineWidth={1} transparent opacity={0.2} />
          <Line points={[[-h, b + third * i, z], [h, b + third * i, z]]} color={c.fg} lineWidth={1} transparent opacity={0.2} />
        </group>
      ))}
    </group>
  );
}

type Line2Like = THREE.Object3D & { geometry: THREE.InstancedBufferGeometry };

function Trail({ points, color, dashed, width, opacity = 1, lineRef }: {
  points: Vec3[]; color: string; dashed?: boolean; width: number; opacity?: number; lineRef: React.MutableRefObject<Line2Like | null>;
}) {
  return (
    <Line
      ref={lineRef as never}
      points={points}
      color={color}
      lineWidth={width}
      dashed={dashed}
      dashSize={0.9}
      gapSize={0.6}
      transparent={opacity < 1}
      opacity={opacity}
    />
  );
}

export interface PitchFrameProps {
  thrown: Throw;
  hand: Hand;
  playId: number;
  slow: number;
  reduced: boolean;
  onLanded: () => void;
}

function Pitch({ thrown, hand, playId, slow, reduced, onLanded, c }: PitchFrameProps & { c: Palette }) {
  const world = (f: Flight) => f.pos.map((p) => toWorld(p, hand));
  const seaPts = useMemo(() => world(thrown.sea), [thrown, hand]); // eslint-disable-line react-hooks/exhaustive-deps
  const hhPts = useMemo(() => world(thrown.hh), [thrown, hand]); // eslint-disable-line react-hooks/exhaustive-deps
  const seaBall = useRef<THREE.Mesh>(null);
  const hhBall = useRef<THREE.Mesh>(null);
  const seaLine = useRef<Line2Like | null>(null);
  const hhLine = useRef<Line2Like | null>(null);
  const dots = useRef<THREE.Group>(null);
  const start = useRef<{ id: number; t0: number; landed: boolean }>({ id: -1, t0: 0, landed: false });

  useFrame(({ clock }) => {
    const s = start.current;
    if (s.id !== playId) start.current = { id: playId, t0: clock.elapsedTime, landed: false };
    const t = reduced ? 10 : (clock.elapsedTime - start.current.t0) * slow;
    const place = (m: THREE.Mesh | null, f: Flight) => m && m.position.set(...toWorld(positionAt(f, t), hand));
    place(seaBall.current, thrown.sea);
    place(hhBall.current, thrown.hh);
    const reveal = (l: Line2Like | null, f: Flight) => {
      if (l) l.geometry.instanceCount = Math.max(0, Math.min(f.t.length - 1, Math.ceil(t / DT)));
    };
    reveal(seaLine.current, thrown.sea);
    reveal(hhLine.current, thrown.hh);
    const done = t >= Math.max(thrown.sea.flight_time, thrown.hh.flight_time);
    if (dots.current) dots.current.visible = done;
    if (done && !start.current.landed) {
      start.current.landed = true;
      onLanded();
    }
  });

  const sEnd = seaPts[seaPts.length - 1], hEnd = hhPts[hhPts.length - 1];
  const mid: Vec3 = [(sEnd[0] + hEnd[0]) / 2, (sEnd[1] + hEnd[1]) / 2, PLATE_Z + 0.02];
  const labelLeft = hEnd[0] < sEnd[0];
  return (
    <group>
      <Trail points={seaPts} color={c.sea} dashed width={2} opacity={0.85} lineRef={seaLine} />
      <Trail points={hhPts} color={c.red} width={2.5} lineRef={hhLine} />
      <mesh ref={seaBall}>
        <icosahedronGeometry args={[BALL_R, 1]} />
        <meshStandardMaterial color={c.sea} transparent opacity={0.5} flatShading />
      </mesh>
      <mesh ref={hhBall}>
        <icosahedronGeometry args={[BALL_R, 1]} />
        <meshStandardMaterial color={c.ball} flatShading emissive={c.ball} emissiveIntensity={0.15} />
      </mesh>
      <group ref={dots} visible={false}>
        <mesh position={[sEnd[0], sEnd[1], PLATE_Z + 0.03]}>
          <ringGeometry args={[BALL_R * 0.72, BALL_R, 24]} />
          <meshBasicMaterial color={c.sea} />
        </mesh>
        <mesh position={[hEnd[0], hEnd[1], PLATE_Z + 0.04]}>
          <circleGeometry args={[BALL_R, 24]} />
          <meshBasicMaterial color={c.red} />
        </mesh>
        <Line points={[[sEnd[0], sEnd[1], PLATE_Z + 0.02], [hEnd[0], hEnd[1], PLATE_Z + 0.02]]} color={c.fg} lineWidth={1.2} dashed dashSize={0.05} gapSize={0.04} />
        <Html position={mid} center={false} zIndexRange={[5, 0]} style={{ pointerEvents: 'none' }}>
          <div className={`plate-tag ${labelLeft ? 'is-left' : ''}`}>{fmt(thrown.plateGapIn)} in</div>
        </Html>
      </group>
    </group>
  );
}

export interface SceneProps extends PitchFrameProps {
  view: View;
  batter: Hand;
}

export default function Scene(props: SceneProps) {
  const c = useMemo(palette, []);
  const { thrown, hand } = props;
  return (
    <Canvas
      dpr={[1, 2]}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
      camera={{ position: VIEWS.catcher.pos, fov: VIEWS.catcher.fov, near: 0.3, far: 1600 }}
      onCreated={({ scene }) => {
        scene.background = new THREE.Color(c.bg);
        scene.fog = new THREE.Fog(c.bg, 280, 760);
      }}
    >
      <hemisphereLight args={['#3b4250', c.bg, 0.7]} />
      <pointLight position={[-230, 125, -170]} intensity={1.25} decay={0} color="#fff6e8" />
      <pointLight position={[230, 125, -170]} intensity={1.25} decay={0} color="#fff6e8" />
      <pointLight position={[0, 60, 80]} intensity={0.45} decay={0} />
      <CameraRig view={props.view} reduced={props.reduced} />
      <Field c={c} />
      <Zone c={c} />
      <Batter side={props.batter} reduced={props.reduced} />
      <group position={[0, MOUND_H + 0.05, -60.5]} scale={[hand === 'R' ? -1 : 1, 1, 1]}>
        <PitcherBody side={thrown.pitch.release.rel_side_ft} height={thrown.pitch.release.rel_height_ft} ext={thrown.pitch.release.extension_ft} />
      </group>
      <Pitch {...props} c={c} />
    </Canvas>
  );
}
