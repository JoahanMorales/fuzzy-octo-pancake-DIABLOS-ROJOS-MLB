/* Low-poly players driven by keyframed joint positions (feet). Each frame the limbs are re-aimed between their two
   joints, so a pose is just a table of points and the windup is a blend between poses. No skinning, ~25 meshes. */
import { Suspense, useLayoutEffect, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { batterFrame, MOUND_H, MOUND_Z, type Hand, type Vec3 } from './sceneModel';
import { Mannequin } from './mannequin';

const FT = 3.28084;

type Joint =
  | 'pelvis' | 'chest' | 'neck' | 'head'
  | 'hipL' | 'kneeL' | 'ankleL' | 'toeL' | 'hipR' | 'kneeR' | 'ankleR' | 'toeR'
  | 'shoulderL' | 'elbowL' | 'handL' | 'shoulderR' | 'elbowR' | 'handR';
export type Pose = Record<Joint, Vec3>;

interface Part { a: Joint; b: Joint; r0: number; r1: number; mat: 'jersey' | 'pants' | 'skin' | 'dark' }

const PARTS: Part[] = [
  { a: 'pelvis', b: 'chest', r0: 0.5, r1: 0.62, mat: 'jersey' },
  { a: 'chest', b: 'neck', r0: 0.62, r1: 0.2, mat: 'jersey' },
  { a: 'hipL', b: 'kneeL', r0: 0.25, r1: 0.2, mat: 'pants' },
  { a: 'kneeL', b: 'ankleL', r0: 0.2, r1: 0.14, mat: 'pants' },
  { a: 'ankleL', b: 'toeL', r0: 0.15, r1: 0.12, mat: 'dark' },
  { a: 'hipR', b: 'kneeR', r0: 0.25, r1: 0.2, mat: 'pants' },
  { a: 'kneeR', b: 'ankleR', r0: 0.2, r1: 0.14, mat: 'pants' },
  { a: 'ankleR', b: 'toeR', r0: 0.15, r1: 0.12, mat: 'dark' },
  { a: 'shoulderL', b: 'elbowL', r0: 0.15, r1: 0.12, mat: 'jersey' },
  { a: 'elbowL', b: 'handL', r0: 0.12, r1: 0.09, mat: 'skin' },
  { a: 'shoulderR', b: 'elbowR', r0: 0.15, r1: 0.12, mat: 'jersey' },
  { a: 'elbowR', b: 'handR', r0: 0.12, r1: 0.09, mat: 'skin' },
  { a: 'shoulderL', b: 'shoulderR', r0: 0.2, r1: 0.2, mat: 'jersey' },
  { a: 'hipL', b: 'hipR', r0: 0.27, r1: 0.27, mat: 'pants' },
];
const JOINTS: Joint[] = ['kneeL', 'kneeR', 'elbowL', 'elbowR', 'shoulderL', 'shoulderR', 'handL', 'handR'];

const UP = new THREE.Vector3(0, 1, 0);

export function blend(a: Pose, b: Pose, t: number): Pose {
  const out = {} as Pose;
  for (const k of Object.keys(a) as Joint[]) {
    const p = a[k], q = b[k];
    out[k] = [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t, p[2] + (q[2] - p[2]) * t];
  }
  return out;
}

/** Piecewise blend through keyframes at times ts (seconds), smoothstep inside each segment. */
export function sample(keys: Pose[], ts: number[], t: number): Pose {
  if (t <= ts[0]) return keys[0];
  for (let i = 1; i < ts.length; i++) {
    if (t <= ts[i]) {
      const u = (t - ts[i - 1]) / (ts[i] - ts[i - 1]);
      return blend(keys[i - 1], keys[i], u * u * (3 - 2 * u));
    }
  }
  return keys[keys.length - 1];
}

export interface Look { jersey: string; pants: string; skin: string; dark: string; helmet: string }

function Rig({ pose, look, helmet, extra }: { pose: React.MutableRefObject<Pose>; look: Look; helmet: boolean; extra?: React.ReactNode }) {
  const mats = useMemo(() => ({
    jersey: new THREE.MeshStandardMaterial({ color: look.jersey, roughness: 0.75, flatShading: true }),
    pants: new THREE.MeshStandardMaterial({ color: look.pants, roughness: 0.8, flatShading: true }),
    skin: new THREE.MeshStandardMaterial({ color: look.skin, roughness: 0.65, flatShading: true }),
    dark: new THREE.MeshStandardMaterial({ color: look.dark, roughness: 0.5, flatShading: true }),
    helmet: new THREE.MeshStandardMaterial({ color: look.helmet, roughness: 0.25, metalness: 0.1, flatShading: true }),
  }), [look]);
  const limbs = useRef<(THREE.Mesh | null)[]>([]);
  const joints = useRef<(THREE.Mesh | null)[]>([]);
  const head = useRef<THREE.Group>(null);
  const tmp = useMemo(() => ({ a: new THREE.Vector3(), b: new THREE.Vector3(), d: new THREE.Vector3() }), []);

  const apply = () => {
    const p = pose.current;
    PARTS.forEach((part, i) => {
      const m = limbs.current[i];
      if (!m) return;
      tmp.a.set(...p[part.a]);
      tmp.b.set(...p[part.b]);
      tmp.d.subVectors(tmp.b, tmp.a);
      const len = Math.max(tmp.d.length(), 1e-3);
      m.position.addVectors(tmp.a, tmp.b).multiplyScalar(0.5);
      m.quaternion.setFromUnitVectors(UP, tmp.d.normalize());
      m.scale.set(1, len, 1);
    });
    JOINTS.forEach((j, i) => joints.current[i]?.position.set(...p[j]));
    head.current?.position.set(...p.head);
  };
  useLayoutEffect(apply);
  useFrame(apply);

  return (
    <group>
      {PARTS.map((part, i) => (
        <mesh key={`${part.a}-${part.b}`} ref={(el) => { limbs.current[i] = el; }} material={mats[part.mat]} castShadow>
          <cylinderGeometry args={[part.r1, part.r0, 1, 7]} />
        </mesh>
      ))}
      {JOINTS.map((j, i) => (
        <mesh key={j} ref={(el) => { joints.current[i] = el; }} material={j.startsWith('hand') ? mats.skin : mats.jersey} castShadow>
          <icosahedronGeometry args={[j.startsWith('knee') ? 0.21 : j.startsWith('hand') ? 0.12 : 0.15, 0]} />
        </mesh>
      ))}
      <group ref={head}>
        <mesh material={mats.skin} castShadow>
          <icosahedronGeometry args={[0.33, 1]} />
        </mesh>
        {helmet ? (
          <mesh material={mats.helmet} position={[0, 0.07, 0]} castShadow>
            <sphereGeometry args={[0.39, 10, 6, 0, Math.PI * 2, 0, Math.PI / 1.9]} />
          </mesh>
        ) : (
          <mesh material={mats.helmet} position={[0, 0.13, 0]} castShadow>
            <sphereGeometry args={[0.36, 10, 5, 0, Math.PI * 2, 0, Math.PI / 2]} />
          </mesh>
        )}
      </group>
      {extra}
    </group>
  );
}

/* ---------- batter: chest toward +x (the plate), pitcher toward -z; mirrored with scale.x for a lefty ---------- */
const STANCE: Pose = {
  pelvis: [0, 3.0, 0], chest: [0.22, 4.75, 0.05], neck: [0.3, 5.2, 0], head: [0.36, 5.62, -0.06],
  hipL: [0.02, 3.0, -0.42], kneeL: [0.42, 1.65, -0.95], ankleL: [0.2, 0.3, -1.3], toeL: [0.75, 0.12, -1.3],
  hipR: [0.02, 3.0, 0.42], kneeR: [0.36, 1.65, 0.98], ankleR: [0.08, 0.3, 1.22], toeR: [0.62, 0.12, 1.22],
  shoulderL: [0.26, 4.95, -0.68], elbowL: [0.8, 4.5, -0.08], handL: [0.48, 5.12, 0.56],
  shoulderR: [0.26, 4.95, 0.7], elbowR: [0.38, 4.55, 1.05], handR: [0.48, 5.06, 0.62],
};
const LOAD: Pose = {
  ...STANCE,
  chest: [0.18, 4.72, 0.18], head: [0.34, 5.6, 0.0], shoulderL: [0.24, 4.92, -0.56],
  handL: [0.4, 5.22, 0.8], handR: [0.4, 5.16, 0.86], elbowL: [0.78, 4.55, 0.12], elbowR: [0.36, 4.6, 1.2],
  kneeL: [0.38, 1.85, -0.85], ankleL: [0.22, 0.6, -1.15], toeL: [0.7, 0.45, -1.2],
};
const STRIDE: Pose = {
  ...STANCE,
  kneeL: [0.46, 1.6, -1.25], ankleL: [0.26, 0.3, -1.75], toeL: [0.8, 0.12, -1.8],
  chest: [0.24, 4.7, 0.0], handL: [0.44, 5.18, 0.74], handR: [0.44, 5.12, 0.8],
};

export function Batter({ hand, reduced, playId, look, windup }: { hand: Hand; reduced: boolean; playId: number; look: Look; windup: number }) {
  const ref = useRef<THREE.Group>(null);
  const pose = useRef<Pose>(STANCE);
  const swap = useRef({ from: hand, to: hand, t: 1 });
  const clock = useRef({ id: -1, t0: 0 });
  if (swap.current.to !== hand) swap.current = { from: swap.current.to, to: hand, t: reduced ? 1 : 0 };
  const bat = useRef<THREE.Mesh>(null);
  const batRig = useRef<THREE.Mesh>(null);
  useFrame((st, dt) => {
    const g = ref.current;
    if (!g) return;
    const s = swap.current;
    s.t = reduced ? 1 : Math.min(1, s.t + dt / 0.72);
    const f = batterFrame(s.from, s.to, s.t);
    g.position.set(f.x, f.y, f.z);
    g.scale.set(f.mirror, 1, 1);
    if (clock.current.id !== playId) clock.current = { id: playId, t0: st.clock.elapsedTime };
    const t = reduced ? 0 : st.clock.elapsedTime - clock.current.t0;
    pose.current = sample([STANCE, LOAD, STRIDE, STANCE], [windup * 0.45, windup * 0.95, windup + 0.5, windup + 1.6], t);
    const b = bat.current;
    if (b) {
      const p = pose.current;
      const grip = new THREE.Vector3(...p.handL).lerp(new THREE.Vector3(...p.handR), 0.5);
      const tip = grip.clone().add(new THREE.Vector3(-0.6, 2.45, 0.85));
      b.position.copy(grip).lerp(tip, 0.5);
      b.quaternion.setFromUnitVectors(UP, tip.clone().sub(grip).normalize());
    }
  });
  // batter space (chest toward +x, catcher toward +z) -> rig space (meters, rig faces +z, his right at -x)
  const toRig = (q: Vec3) => new THREE.Vector3(-q[2] / FT, q[1] / FT, q[0] / FT);
  const placeBat = (l: THREE.Vector3, r: THREE.Vector3) => {
    const m = batRig.current;
    if (!m) return;
    const grip = l.clone().lerp(r, 0.5);
    const dir = new THREE.Vector3(-0.42, 0.88, -0.22).normalize();
    m.position.copy(grip).addScaledVector(dir, 0.4);
    m.quaternion.setFromUnitVectors(UP, dir);
  };
  const fallback = (
    <Rig pose={pose} look={look} helmet
      extra={(
        <mesh ref={bat} castShadow>
          <cylinderGeometry args={[0.115, 0.05, 2.75, 8]} />
          <meshStandardMaterial color="#b0875c" roughness={0.45} flatShading />
        </mesh>
      )}
    />
  );
  return (
    <group ref={ref}>
      <Suspense fallback={fallback}>
        <group rotation={[0, Math.PI / 2, 0]}>
          <Mannequin pose={pose} look={look} toRig={toRig} helmet onPosed={placeBat}>
            <mesh ref={batRig} castShadow>
              <cylinderGeometry args={[0.034, 0.014, 0.86, 14]} />
              <meshStandardMaterial color="#b0875c" roughness={0.4} />
            </mesh>
          </Mannequin>
        </group>
      </Suspense>
    </group>
  );
}

/* ---------- pitcher: local +z toward home, +x = arm side, y from the mound top ---------- */
function pitcherKeys(hand: Vec3): Pose[] {
  const set: Pose = {
    pelvis: [0, 3.05, 0.1], chest: [0.05, 4.85, 0.15], neck: [0.05, 5.25, 0.2], head: [0.05, 5.66, 0.25],
    hipL: [-0.35, 3.0, 0.1], kneeL: [-0.4, 1.6, 0.25], ankleL: [-0.42, 0.25, 0.3], toeL: [-0.42, 0.1, 0.85],
    hipR: [0.35, 3.0, 0.05], kneeR: [0.4, 1.6, 0.0], ankleR: [0.42, 0.25, -0.05], toeR: [0.9, 0.1, 0.0],
    shoulderL: [-0.68, 4.85, 0.2], elbowL: [-0.5, 4.1, 0.55], handL: [0.0, 4.35, 0.75],
    shoulderR: [0.68, 4.85, 0.15], elbowR: [0.55, 4.1, 0.55], handR: [0.08, 4.4, 0.78],
  };
  const lift: Pose = {
    ...set,
    pelvis: [0.05, 3.1, -0.1], chest: [0.1, 4.9, -0.15], neck: [0.1, 5.3, -0.12], head: [0.1, 5.7, -0.1],
    hipL: [-0.3, 3.05, -0.05], kneeL: [-0.25, 4.0, 0.55], ankleL: [-0.35, 2.75, 0.45], toeL: [-0.3, 2.65, 0.95],
    shoulderL: [-0.6, 4.9, -0.1], elbowL: [-0.75, 4.35, 0.35], handL: [-0.1, 4.6, 0.55],
    shoulderR: [0.66, 4.9, -0.2], elbowR: [0.6, 4.25, 0.25], handR: [0.1, 4.6, 0.55],
  };
  const cock: Pose = {
    pelvis: [0.05, 2.75, 1.4], chest: [0.12, 4.5, 1.6], neck: [0.1, 4.95, 1.75], head: [0.08, 5.35, 1.95],
    hipL: [-0.32, 2.75, 1.55], kneeL: [-0.4, 1.7, 3.2], ankleL: [-0.42, 0.25, 3.7], toeL: [-0.42, 0.1, 4.25],
    hipR: [0.32, 2.75, 1.25], kneeR: [0.55, 1.35, 0.6], ankleR: [0.5, 0.25, -0.05], toeR: [0.95, 0.1, 0.0],
    shoulderL: [-0.6, 4.55, 1.9], elbowL: [-1.15, 4.6, 2.4], handL: [-1.0, 4.4, 2.9],
    shoulderR: [0.65, 4.55, 1.35], elbowR: [1.4, 4.75, 0.9], handR: [1.25, 5.6, 0.3],
  };
  const sh: Vec3 = [0.68, 4.75, 3.85];
  const release: Pose = {
    pelvis: [0.05, 2.7, 2.3], chest: [0.18, 4.45, 3.65], neck: [0.15, 4.85, 3.95], head: [0.12, 5.2, 4.25],
    hipL: [-0.32, 2.7, 2.45], kneeL: [-0.42, 1.8, 3.95], ankleL: [-0.42, 0.24, 4.5], toeL: [-0.42, 0.1, 5.05],
    hipR: [0.32, 2.7, 2.15], kneeR: [0.6, 1.35, 1.25], ankleR: [0.55, 0.35, 0.15], toeR: [0.95, 0.15, 0.2],
    shoulderL: [-0.55, 4.6, 3.75], elbowL: [-0.98, 4.0, 3.55], handL: [-0.72, 3.62, 3.2],
    shoulderR: sh, elbowR: [(sh[0] + hand[0]) / 2 + 0.2, (sh[1] + hand[1]) / 2 + 0.25, (sh[2] + hand[2]) / 2], handR: hand,
  };
  const follow: Pose = {
    ...release,
    chest: [0.0, 4.05, 4.1], neck: [-0.05, 4.4, 4.45], head: [-0.1, 4.75, 4.75],
    shoulderR: [0.45, 4.3, 4.3], elbowR: [-0.2, 3.5, 4.9], handR: [-0.85, 2.9, 4.6],
    hipR: [0.3, 2.85, 2.5], kneeR: [0.5, 2.6, 1.6], ankleR: [0.45, 2.9, 0.7], toeR: [0.8, 2.9, 0.7],
  };
  return [set, lift, cock, release, follow];
}

export function Pitcher({ throws, release, reduced, playId, look, windup }: {
  throws: Hand; release: Vec3; reduced: boolean; playId: number; look: Look; windup: number;
}) {
  const mirror = throws === 'R' ? -1 : 1; // local +x = arm side; a righty's arm side is the catcher's left (-x)
  const hand: Vec3 = [release[0] * mirror, release[1] - MOUND_H, release[2] - MOUND_Z];
  const keys = useMemo(() => pitcherKeys(hand), [hand[0], hand[1], hand[2]]); // eslint-disable-line react-hooks/exhaustive-deps
  const times = [0, windup * 0.4, windup * 0.82, windup, windup + 0.45];
  const pose = useRef<Pose>(reduced ? keys[3] : keys[0]);
  const clock = useRef({ id: -1, t0: 0 });
  useFrame((st) => {
    if (clock.current.id !== playId) clock.current = { id: playId, t0: st.clock.elapsedTime };
    pose.current = reduced ? keys[3] : sample(keys, times, st.clock.elapsedTime - clock.current.t0);
  });
  // pitcher space (+z toward home, +x arm side) -> rig space (meters; the rig's right hand is at -x)
  const toRig = (q: Vec3) => new THREE.Vector3(-q[0] / FT, q[1] / FT, q[2] / FT);
  return (
    <group position={[0, MOUND_H, MOUND_Z]}>
      <Suspense fallback={<group scale={[mirror, 1, 1]}><Rig pose={pose} look={look} helmet={false} /></group>}>
        <group scale={[throws === 'R' ? 1 : -1, 1, 1]}>
          <Mannequin pose={pose} look={look} toRig={toRig} helmet />
        </group>
      </Suspense>
    </group>
  );
}
