/* The ballpark at night: mowed grass, skinned infield, fence, tiered stands with a low-poly crowd, light towers,
   and the backdrop that tells the air: the volcanoes over CDMX or a sea horizon. Feet; home plate at the origin,
   center field toward -z. */
import { useLayoutEffect, useMemo, useRef } from 'react';
import { Line } from '@react-three/drei';
import * as THREE from 'three';
import { dirtTexture, grassTexture, skyTexture } from './textures';
import { MOUND_H, MOUND_Z, type Palette, type ParkSide, type Vec3 } from './sceneModel';

const BASE = 90 / Math.SQRT2;
const FENCE_R = 335;
const FLAT: [number, number, number] = [-Math.PI / 2, 0, 0];

function tint(hex: string, toward: string, t: number): string {
  return `#${new THREE.Color(hex).lerp(new THREE.Color(toward), t).getHexString()}`;
}

export function Sky({ park }: { park: ParkSide }) {
  const tex = useMemo(
    () => skyTexture('#07090e', park === 'harp' ? '#1a2233' : '#16283a', park === 'harp' ? '#4a3a32' : '#2e4656'),
    [park],
  );
  return (
    <mesh scale={[-1, 1, 1]}>
      <sphereGeometry args={[1700, 24, 16]} />
      <meshBasicMaterial map={tex} side={THREE.BackSide} fog={false} depthWrite={false} />
    </mesh>
  );
}

/** CDMX: Popocatépetl (the cone) and Iztaccíhuatl (the long ridge) with snow; sea level: dark water to the horizon. */
export function Backdrop({ park }: { park: ParkSide }) {
  if (park === 'harp') {
    const rock = '#2b3446';
    const snow = '#b9bec8';
    return (
      <group>
        <group position={[-470, 150, -1350]} scale={[1.15, 1.7, 1.15]}>
          <mesh>
            <coneGeometry args={[520, 520, 9]} />
            <meshBasicMaterial color={rock} fog={false} />
          </mesh>
          <mesh position={[0, 185, 0]}>
            <coneGeometry args={[170, 150, 9]} />
            <meshBasicMaterial color={snow} fog={false} />
          </mesh>
        </group>
        <group position={[560, 80, -1450]} scale={[2.8, 1.05, 1.1]}>
          <mesh>
            <coneGeometry args={[300, 520, 7]} />
            <meshBasicMaterial color={'#252d3d'} fog={false} />
          </mesh>
          <mesh position={[0, 205, 0]}>
            <coneGeometry args={[110, 110, 7]} />
            <meshBasicMaterial color={'#a9aeb8'} fog={false} />
          </mesh>
        </group>
        <mesh position={[0, 0, -1100]} rotation={FLAT}>
          <planeGeometry args={[4000, 900]} />
          <meshStandardMaterial color="#151a20" roughness={1} />
        </mesh>
      </group>
    );
  }
  return (
    <group>
      <mesh position={[0, -1.5, -1050]} rotation={FLAT}>
        <planeGeometry args={[4000, 1300]} />
        <meshStandardMaterial color="#0e1b25" roughness={0.18} metalness={0.55} />
      </mesh>
      {[-420, -90, 260, 610].map((x, i) => (
        <mesh key={x} position={[x, 3, -1350 - i * 40]}>
          <boxGeometry args={[8, 2.5, 2]} />
          <meshStandardMaterial color="#e8e6e1" emissive="#e8e6e1" emissiveIntensity={0.6} />
        </mesh>
      ))}
    </group>
  );
}

function Plate({ color }: { color: string }) {
  const shape = useMemo(() => {
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
  return (
    <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0.07, 0]} receiveShadow>
      <shapeGeometry args={[shape]} />
      <meshStandardMaterial color={color} roughness={0.7} side={THREE.DoubleSide} />
    </mesh>
  );
}

export function Field({ c }: { c: Palette }) {
  const grass = useMemo(() => grassTexture(tint(c.grass, '#7fbf6a', 0.16), tint(c.grassDark, '#5d9a52', 0.08)), [c]);
  const dirt = useMemo(() => dirtTexture(tint(c.dirt, '#c08a5a', 0.12)), [c]);
  const box = (sx: number): Vec3[] => {
    const zMid = -0.7;
    const xi = sx * 1.21, xo = sx * 5.21;
    return [[xi, 0.08, zMid + 3], [xo, 0.08, zMid + 3], [xo, 0.08, zMid - 3], [xi, 0.08, zMid - 3], [xi, 0.08, zMid + 3]];
  };
  return (
    <group>
      <mesh rotation={FLAT} receiveShadow>
        <circleGeometry args={[900, 72]} />
        <meshStandardMaterial map={grass} roughness={0.95} />
      </mesh>
      {/* warning track and infield skin */}
      <mesh rotation={FLAT} position={[0, 0.02, 0]} receiveShadow>
        <ringGeometry args={[FENCE_R - 16, FENCE_R + 2, 96]} />
        <meshStandardMaterial map={dirt} roughness={1} />
      </mesh>
      <mesh rotation={FLAT} position={[0, 0.03, MOUND_Z]} receiveShadow>
        <circleGeometry args={[95, 64]} />
        <meshStandardMaterial map={dirt} roughness={1} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, Math.PI / 4]} position={[0, 0.045, -BASE]} receiveShadow>
        <planeGeometry args={[80, 80]} />
        <meshStandardMaterial map={grass} roughness={0.95} />
      </mesh>
      <mesh rotation={FLAT} position={[0, 0.06, -0.8]} receiveShadow>
        <circleGeometry args={[13, 40]} />
        <meshStandardMaterial map={dirt} roughness={1} />
      </mesh>
      {/* mound and rubber */}
      <mesh position={[0, MOUND_H / 2 + 0.05, MOUND_Z]} receiveShadow castShadow>
        <cylinderGeometry args={[2.6, 9, MOUND_H, 24]} />
        <meshStandardMaterial map={dirt} roughness={1} />
      </mesh>
      <mesh position={[0, MOUND_H + 0.08, MOUND_Z]} receiveShadow>
        <boxGeometry args={[2, 0.08, 0.5]} />
        <meshStandardMaterial color={c.chalk} roughness={0.6} />
      </mesh>
      <Plate color={c.chalk} />
      {([[BASE, -BASE], [0, -BASE * 2], [-BASE, -BASE]] as const).map(([x, z]) => (
        <mesh key={`${x}${z}`} position={[x, 0.2, z]} rotation={[0, Math.PI / 4, 0]} castShadow receiveShadow>
          <boxGeometry args={[1.25, 0.25, 1.25]} />
          <meshStandardMaterial color={c.chalk} roughness={0.6} />
        </mesh>
      ))}
      {[-1, 1].map((s) => (
        <mesh key={s} rotation={[-Math.PI / 2, 0, (s * Math.PI) / 4]}
          position={[(s * FENCE_R) / Math.SQRT2 / 2, 0.075, -FENCE_R / Math.SQRT2 / 2]}>
          <planeGeometry args={[0.33, FENCE_R]} />
          <meshStandardMaterial color={c.chalk} roughness={0.6} />
        </mesh>
      ))}
      {[box(-1), box(1)].map((pts, i) => <Line key={i} points={pts} color={c.chalk} lineWidth={1.4} />)}
    </group>
  );
}

/** Fence, foul poles, three tiers of stands with a crowd (one instanced mesh), and six light towers. */
export function Stands({ c }: { c: Palette }) {
  const arc = { start: Math.PI - 1.15, len: 2.3 };
  const tiers = [
    { r0: FENCE_R + 6, r1: FENCE_R + 40, y0: 10, y1: 34 },
    { r0: FENCE_R + 44, r1: FENCE_R + 78, y0: 40, y1: 66 },
    { r0: FENCE_R + 82, r1: FENCE_R + 112, y0: 72, y1: 96 },
  ];
  const crowd = useRef<THREE.InstancedMesh>(null);
  const seats = useMemo(() => {
    const out: { p: Vec3; s: number; col: string }[] = [];
    const cols = ['#d8d6d0', '#9aa0aa', '#2e3440', '#5b6372', '#e8e6e1', '#7a6e62', '#3d4a5a', '#b9b3a8'];
    let k = 0;
    for (const t of tiers) {
      for (let row = 0; row < 4; row++) {
        const u = (row + 0.5) / 4;
        const r = t.r0 + (t.r1 - t.r0) * u;
        const y = t.y0 + (t.y1 - t.y0) * u + 1.6;
        const n = Math.floor((arc.len * r) / 3.2);
        for (let i = 0; i < n; i++) {
          if ((i * 7 + row * 3 + k) % 9 === 0) continue; // empty seats
          const th = arc.start + (i / n) * arc.len;
          out.push({ p: [r * Math.sin(th), y, r * Math.cos(th)], s: 0.85 + ((i * 13 + row) % 5) * 0.07, col: cols[(i * 5 + row * 11 + k) % cols.length] });
        }
      }
      k += 1;
    }
    return out;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useLayoutEffect(() => {
    const m = crowd.current;
    if (!m) return;
    const o = new THREE.Object3D();
    const col = new THREE.Color();
    seats.forEach((s, i) => {
      o.position.set(...s.p);
      o.rotation.set(0, Math.atan2(s.p[0], s.p[2]), 0);
      o.scale.set(1.4 * s.s, 2.6 * s.s, 1.1 * s.s);
      o.updateMatrix();
      m.setMatrixAt(i, o.matrix);
      m.setColorAt(i, col.set(s.col));
    });
    m.instanceMatrix.needsUpdate = true;
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
  }, [seats]);

  const towers: { at: Vec3 }[] = [-1, 1].flatMap((s) => [
    { at: [s * 300, 0, -60] as Vec3 },
    { at: [s * 310, 0, -300] as Vec3 },
    { at: [s * 120, 0, -470] as Vec3 },
  ]);

  return (
    <group>
      {/* padded fence */}
      <mesh position={[0, 5, 0]} receiveShadow>
        <cylinderGeometry args={[FENCE_R, FENCE_R, 10, 96, 1, true, arc.start, arc.len]} />
        <meshStandardMaterial color="#1d3326" side={THREE.DoubleSide} roughness={0.9} />
      </mesh>
      <mesh position={[0, 10.1, 0]}>
        <cylinderGeometry args={[FENCE_R + 0.2, FENCE_R + 0.2, 0.35, 96, 1, true, arc.start, arc.len]} />
        <meshStandardMaterial color={c.chalk} side={THREE.DoubleSide} />
      </mesh>
      {[-1, 1].map((s) => (
        <mesh key={s} position={[(s * FENCE_R) / Math.SQRT2, 20, -FENCE_R / Math.SQRT2]}>
          <cylinderGeometry args={[0.35, 0.35, 40, 8]} />
          <meshStandardMaterial color="#d9c441" roughness={0.5} />
        </mesh>
      ))}
      {tiers.map((t, i) => (
        <mesh key={i} position={[0, (t.y0 + t.y1) / 2, 0]} receiveShadow>
          <cylinderGeometry args={[t.r1, t.r0, t.y1 - t.y0, 96, 1, true, arc.start, arc.len]} />
          <meshStandardMaterial color={i % 2 ? '#22252c' : '#1a1c21'} side={THREE.DoubleSide} roughness={1} flatShading />
        </mesh>
      ))}
      <instancedMesh ref={crowd} args={[undefined, undefined, seats.length]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial roughness={0.9} flatShading />
      </instancedMesh>
      {towers.map(({ at }, i) => (
        <group key={i} position={at}>
          <mesh position={[0, 70, 0]}>
            <cylinderGeometry args={[1.2, 2.2, 140, 6]} />
            <meshStandardMaterial color="#2a2d33" flatShading />
          </mesh>
          <group position={[0, 142, 0]} rotation={[0, Math.atan2(-at[0], -at[2]), 0]}>
            <group rotation={[0.42, 0, 0]}>
            <mesh>
              <boxGeometry args={[34, 14, 1.5]} />
              <meshStandardMaterial color="#2a2d33" flatShading />
            </mesh>
            {Array.from({ length: 12 }, (_, k) => (
              <mesh key={k} position={[-13.5 + (k % 6) * 5.4, k < 6 ? 3.2 : -3.2, 0.9]}>
                <boxGeometry args={[4.4, 5, 0.4]} />
                <meshStandardMaterial color="#fff6e8" emissive="#fff3e0" emissiveIntensity={2.2} toneMapped={false} />
              </mesh>
            ))}
            </group>
          </group>
        </group>
      ))}
    </group>
  );
}
