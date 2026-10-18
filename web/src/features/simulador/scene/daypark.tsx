/* Day game: physical sky (three's Preetham Sky), procedural clouds, a grass shader with real mowing stripes (their
   brightness flips with the view direction, as on a real field), clay infield, and the horizon that tells the air:
   the volcanoes behind CDMX in a deep high-altitude blue, or the sea under a hazier low-altitude sky.
   Feet; home plate's back tip at the origin, center field toward -z. */
import { useMemo } from 'react';
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

/** Outfield wall and foul poles: enough to frame the field without hiding the sky or the mountains. */
function Ballpark() {
  const arc = { start: Math.PI - 1.15, len: 2.3 };
  return (
    <group>
      <mesh position={[0, 5, 0]} receiveShadow castShadow>
        <cylinderGeometry args={[FENCE_R, FENCE_R, 10, 128, 1, true, arc.start, arc.len]} />
        <meshStandardMaterial color="#1f4a32" roughness={0.85} side={THREE.DoubleSide} />
      </mesh>
      <mesh position={[0, 10.1, 0]}>
        <cylinderGeometry args={[FENCE_R + 0.15, FENCE_R + 0.15, 0.4, 128, 1, true, arc.start, arc.len]} />
        <meshStandardMaterial color="#e9c43a" roughness={0.6} side={THREE.DoubleSide} />
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

/** CDMX: Popocatépetl and Iztaccíhuatl far away, blue with distance and snow-capped; sea level: open water. */
export function DayHorizon({ park }: { park: ParkSide }) {
  if (park === 'harp') {
    const peak = (x: number, z: number, r: number, h: number, sx: number, snow: number, seg: number) => (
      <group position={[x, h / 2 - 30, z]} scale={[sx, 1, 1]}>
        <mesh>
          <coneGeometry args={[r, h, seg]} />
          <meshStandardMaterial color="#6d82a3" roughness={1} />
        </mesh>
        <mesh position={[0, h / 2 - (h * snow) / 2, 0]}>
          <coneGeometry args={[r * snow * 1.02, h * snow, seg]} />
          <meshStandardMaterial color="#f2f5fa" roughness={0.8} />
        </mesh>
      </group>
    );
    return (
      <group>
        {peak(-600, -1700, 470, 380, 1.25, 0.24, 24)}
        {peak(700, -1780, 280, 290, 3.0, 0.17, 18)}
        {peak(60, -1550, 1000, 110, 2.3, 0.0001, 14)}
      </group>
    );
  }
  return (
    <mesh position={[0, -1, -1400]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[6000, 1800]} />
      <meshStandardMaterial color="#1f5f86" roughness={0.08} metalness={0.6} />
    </mesh>
  );
}
