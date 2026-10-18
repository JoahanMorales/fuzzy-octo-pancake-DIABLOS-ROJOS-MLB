/* What lives around the park: the city between the outfield and the volcanoes (one instanced mesh, windows painted
   in the shader), jacaranda and ash trees behind the wall, six light towers and the scoreboard. Everything is a few
   draw calls; detail comes from shaders and canvas textures, not geometry. Feet, home plate at the origin. */
import { useEffect, useMemo } from 'react';
import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import type { ParkSide } from './sceneModel';

const FENCE_R = 335;

/** Deterministic random numbers, so the city is the same on every load. */
function rng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/* --------------------------------- city ---------------------------------- */

const WINDOWS_FRAG = /* glsl */ `
  // floors every 11 ft, window columns every 7 ft along the facade; roofs stay plain
  float wall = 1.0 - step(0.6, abs(vN.y));
  float along = dot(vWorld.xz, normalize(vec2(-vN.z, vN.x) + 1e-5));
  float fy = fract(vWorld.y / 11.0), fx = fract(along / 7.0);
  float win = step(0.3, fy) * step(fy, 0.82) * step(0.18, fx) * step(fx, 0.82) * wall * step(6.0, vWorld.y);
  float lit = fract(sin(dot(floor(vec2(along / 7.0, vWorld.y / 11.0)), vec2(12.9898, 78.233))) * 43758.5453);
  vec3 glass = mix(vec3(0.2, 0.27, 0.36), vec3(0.55, 0.66, 0.78), step(0.72, lit));
  diffuseColor.rgb = mix(diffuseColor.rgb, glass, win * 0.85);
  // a darker band at street level
  diffuseColor.rgb *= mix(0.72, 1.0, smoothstep(0.0, 8.0, vWorld.y));`;

function useWindowMaterial() {
  return useMemo(() => {
    const m = new THREE.MeshStandardMaterial({ roughness: 0.85, metalness: 0 });
    m.onBeforeCompile = (sh) => {
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vWorld;\nvarying vec3 vN;')
        .replace('#include <worldpos_vertex>', `#include <worldpos_vertex>
          vec4 wp = vec4(transformed, 1.0);
          mat3 nm = mat3(modelMatrix);
          #ifdef USE_INSTANCING
            wp = instanceMatrix * wp;
            nm = nm * mat3(instanceMatrix);
          #endif
          vWorld = (modelMatrix * wp).xyz;
          vN = normalize(nm * normal);`);
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vWorld;\nvarying vec3 vN;')
        .replace('#include <color_fragment>', `#include <color_fragment>\n${WINDOWS_FRAG}`);
    };
    m.customProgramCacheKey = () => 'city-windows';
    return m;
  }, []);
}

/** Mid-rise blocks in Mexico City colours (concrete, cream, terracotta, pale pink, blue-grey), a few towers. */
function City() {
  const mat = useWindowMaterial();
  const mesh = useMemo(() => {
    const rand = rng(2240);
    const palette = ['#d8d2c4', '#c9b79c', '#b9826a', '#e3d6c8', '#a9b2bd', '#d9b8b0', '#8f969e', '#efe9df'].map((h) => new THREE.Color(h));
    const geo = new THREE.BoxGeometry(1, 1, 1);
    geo.translate(0, 0.5, 0);
    const n = 620;
    const m = new THREE.InstancedMesh(geo, mat, n);
    const o = new THREE.Object3D();
    let k = 0;
    for (let i = 0; i < n * 3 && k < n; i++) {
      const a = Math.PI + (rand() * 2 - 1) * 1.65;
      const r = 620 + Math.pow(rand(), 0.8) * 800;
      const x = Math.sin(a) * r, z = Math.cos(a) * r;
      if (z > -120) continue;
      // keep the middle low so the volcanoes stay in view; a few towers out on the sides
      const tower = rand() < 0.06 && Math.abs(x) > 520;
      const h = tower ? 80 + rand() * 70 : 12 + Math.pow(rand(), 2) * (Math.abs(x) > 400 ? 45 : 26);
      const w = 30 + rand() * 50, d = 30 + rand() * 50;
      o.position.set(x, 0, z);
      o.rotation.set(0, a + (rand() - 0.5) * 0.3, 0);
      o.scale.set(w, h, d);
      o.updateMatrix();
      m.setMatrixAt(k, o.matrix);
      m.setColorAt(k, palette[Math.floor(rand() * palette.length)]);
      k++;
    }
    m.count = k;
    m.instanceMatrix.needsUpdate = true;
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
    return m;
  }, [mat]);
  useEffect(() => () => { mesh.geometry.dispose(); mat.dispose(); }, [mesh, mat]);
  return <primitive object={mesh} />;
}

/* --------------------------------- trees --------------------------------- */

/** Round canopies behind the wall and the stands: ash greens with jacaranda purple mixed in. */
function Trees({ jacaranda }: { jacaranda: boolean }) {
  const mesh = useMemo(() => {
    const rand = rng(77);
    const geo = new THREE.IcosahedronGeometry(1, 3);
    // squash and jitter the canopy so it is not a perfect ball
    const p = geo.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < p.count; i++) {
      const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
      // lumpy leaf clusters: low-frequency bumps from the direction, so shared vertices move together
      const j = 0.82 + 0.12 * Math.sin(x * 5.1 + y * 3.7) * Math.cos(z * 4.3 - y * 2.9) + 0.08 * Math.sin(x * 11 + z * 9);
      p.setXYZ(i, x * j, y * j * 0.78 + 1.45, z * j);
    }
    geo.computeVertexNormals();
    // canopy and trunk in one geometry: vertex colour white for leaves (the instance colour shows), brown for the trunk
    const trunk = new THREE.CylinderGeometry(0.1, 0.16, 1.1, 6).toNonIndexed();
    trunk.translate(0, 0.55, 0);
    const paint = (g: THREE.BufferGeometry, hex: string) => {
      const c = new THREE.Color(hex), n = g.attributes.position.count, col = new Float32Array(n * 3);
      for (let i = 0; i < n; i++) col.set([c.r, c.g, c.b], i * 3);
      g.setAttribute('color', new THREE.BufferAttribute(col, 3));
      g.deleteAttribute('uv');
    };
    paint(geo, '#ffffff');
    paint(trunk, '#4a3a2c');
    const tree = mergeGeometries([geo, trunk]) ?? geo;
    const mat = new THREE.MeshStandardMaterial({ roughness: 0.95, vertexColors: true });
    const n = 240;
    const m = new THREE.InstancedMesh(tree, mat, n);
    const o = new THREE.Object3D();
    const greens = ['#3f6b35', '#4d7a3c', '#355c2f', '#5b8445'].map((h) => new THREE.Color(h));
    const purples = ['#8a6bc7', '#9b7fd4', '#7a5cb5'].map((h) => new THREE.Color(h));
    for (let i = 0; i < n; i++) {
      const behindHome = i % 4 === 0;
      const a = behindHome ? (rand() * 2 - 1) * 1.25 : Math.PI + (rand() * 2 - 1) * 1.3;
      const r = behindHome ? 225 + rand() * 60 : FENCE_R + 70 + rand() * 160;
      const s = 6 + rand() * 5;
      o.position.set(Math.sin(a) * r, 0, Math.cos(a) * r);
      o.rotation.set(0, rand() * 6.28, 0);
      o.scale.set(s, s, s);
      o.updateMatrix();
      m.setMatrixAt(i, o.matrix);
      const purple = jacaranda && rand() < 0.3;
      m.setColorAt(i, (purple ? purples : greens)[Math.floor(rand() * (purple ? purples.length : greens.length))]);
    }
    m.instanceMatrix.needsUpdate = true;
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
    return m;
  }, [jacaranda]);
  useEffect(() => () => { mesh.geometry.dispose(); (mesh.material as THREE.Material).dispose(); }, [mesh]);
  return <primitive object={mesh} />;
}

/* ------------------------------ light towers ----------------------------- */

function lampTexture() {
  const cv = document.createElement('canvas');
  cv.width = 256;
  cv.height = 128;
  const g = cv.getContext('2d');
  if (g) {
    g.fillStyle = '#2b2e33';
    g.fillRect(0, 0, 256, 128);
    for (let r = 0; r < 4; r++) {
      for (let c = 0; c < 8; c++) {
        const x = 16 + c * 32, y = 16 + r * 32;
        const lens = g.createRadialGradient(x - 3, y - 3, 1, x, y, 13);
        lens.addColorStop(0, '#ffffff');
        lens.addColorStop(0.4, '#dfe6ee');
        lens.addColorStop(1, '#7d858f');
        g.fillStyle = lens;
        g.beginPath();
        g.arc(x, y, 12, 0, Math.PI * 2);
        g.fill();
      }
    }
  }
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

const TOWERS: [angle: number, r: number, h: number][] = [
  [0.95, 230, 110], [-0.95, 230, 110],
  [Math.PI - 1.05, FENCE_R + 40, 100], [Math.PI + 1.05, FENCE_R + 40, 100],
  [Math.PI - 0.5, FENCE_R + 45, 100], [Math.PI + 0.5, FENCE_R + 45, 100],
];

function LightTowers() {
  const lamp = useMemo(lampTexture, []);
  useEffect(() => () => lamp.dispose(), [lamp]);
  const steel = useMemo(() => new THREE.MeshStandardMaterial({ color: '#b9bec5', roughness: 0.45, metalness: 0.6 }), []);
  const face = useMemo(() => new THREE.MeshStandardMaterial({ map: lamp, emissiveMap: lamp, emissive: '#ffffff',
    emissiveIntensity: 0.25, roughness: 0.3, metalness: 0.2 }), [lamp]);
  const heads = useMemo(() => [steel, steel, steel, steel, face, steel], [steel, face]);
  useEffect(() => () => { steel.dispose(); face.dispose(); }, [steel, face]);
  return (
    <group>
      {TOWERS.map(([a, r, h]) => {
        const x = Math.sin(a) * r, z = Math.cos(a) * r;
        return (
          <group key={a} position={[x, 0, z]} rotation={[0, Math.atan2(-x, -z), 0]}>
            <mesh position={[0, h / 2, 0]} material={steel} castShadow>
              <cylinderGeometry args={[1.1, 2.2, h, 10]} />
            </mesh>
            {/* catwalk and the lamp bank, tilted down toward the infield */}
            <mesh position={[0, h - 1, 1.5]} material={steel}>
              <boxGeometry args={[34, 0.6, 4]} />
            </mesh>
            <mesh position={[0, h + 8, 1]} rotation={[0.28, 0, 0]} material={heads}>
              <boxGeometry args={[32, 16, 1.6]} />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

/* ------------------------------- scoreboard ------------------------------ */

function boardTexture(harp: boolean) {
  const W = 1024, H = 512;
  const cv = document.createElement('canvas');
  cv.width = W;
  cv.height = H;
  const g = cv.getContext('2d');
  if (g) {
    g.fillStyle = '#0d0e10';
    g.fillRect(0, 0, W, H);
    g.fillStyle = '#b3122b';
    g.fillRect(0, 0, W, 120);
    g.fillStyle = '#ffffff';
    g.font = '800 78px "Segoe UI", Arial, sans-serif';
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    g.fillText('DIABLOS ROJOS', W / 2, 62);
    // empty line score: innings, runs, hits, errors (no numbers: nothing here is real data)
    const cols = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'C', 'H', 'E'];
    g.font = '700 34px "Segoe UI", Arial, sans-serif';
    g.fillStyle = '#e9c43a';
    cols.forEach((c, i) => g.fillText(c, 250 + i * 62, 170));
    g.fillStyle = '#f3f1ec';
    g.textAlign = 'left';
    g.fillText('VISITA', 40, 240);
    g.fillText('DIABLOS', 40, 310);
    g.textAlign = 'center';
    g.fillStyle = '#3a3d42';
    for (let r = 0; r < 2; r++) cols.forEach((_, i) => g.fillRect(226 + i * 62, 214 + r * 70, 48, 52));
    g.fillStyle = '#e9c43a';
    g.font = '800 54px "Segoe UI", Arial, sans-serif';
    g.fillText('STUFF+ 2240', W / 2, 420);
    g.fillStyle = '#9aa0a8';
    g.font = '600 28px "Segoe UI", Arial, sans-serif';
    g.fillText(harp ? 'aire de la Ciudad de México' : 'aire a nivel del mar', W / 2, 474);
  }
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

function Scoreboard({ harp }: { harp: boolean }) {
  const tex = useMemo(() => boardTexture(harp), [harp]);
  const frame = useMemo(() => new THREE.MeshStandardMaterial({ color: '#1b1c1f', roughness: 0.7 }), []);
  const screen = useMemo(() => new THREE.MeshStandardMaterial({ map: tex, emissiveMap: tex, emissive: '#ffffff',
    emissiveIntensity: 0.55, roughness: 0.4 }), [tex]);
  const mats = useMemo(() => [frame, frame, frame, frame, screen, frame], [frame, screen]);
  useEffect(() => () => { tex.dispose(); frame.dispose(); screen.dispose(); }, [tex, frame, screen]);
  const a = Math.PI + 0.72, r = FENCE_R + 40;
  const x = Math.sin(a) * r, z = Math.cos(a) * r;
  return (
    <group position={[x, 0, z]} rotation={[0, Math.atan2(-x, -z), 0]}>
      {[-24, 24].map((px) => (
        <mesh key={px} position={[px, 14, -1]} material={frame} castShadow>
          <boxGeometry args={[3, 28, 3]} />
        </mesh>
      ))}
      <mesh position={[0, 28 + 18, 0]} material={mats} castShadow>
        <boxGeometry args={[72, 36, 3]} />
      </mesh>
    </group>
  );
}

/** Everything outside the field. The city and the jacarandas belong to CDMX; the sea-level park keeps open water. */
export function Surroundings({ park }: { park: ParkSide }) {
  const harp = park === 'harp';
  return (
    <group>
      {harp ? <City /> : null}
      <Trees jacaranda={harp} />
      <LightTowers />
      <Scoreboard harp={harp} />
    </group>
  );
}
