/* r3f only. Motion stays out of this tree (web/DESIGN.md). */
import { useEffect, useLayoutEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { CameraControls, Line } from '@react-three/drei';
import * as THREE from 'three';
import {
  BALL_R,
  MOUND_H,
  MOUND_Z,
  VIEWS,
  ZONE,
  batterFrame,
  cameraMoves,
  cameraSmoothTime,
  palette,
  pointAt,
  skylineProfile,
  type Hand,
  type Palette,
  type ParkSide,
  type Vec3,
  type ViewId,
} from './sceneModel';

const BASE = 90 / Math.SQRT2;

export interface WorldProps {
  view: ViewId;
  hand: Hand;
  park: ParkSide;
  harpPath: Vec3[];
  seaPath: Vec3[];
  reduced: boolean;
  free: boolean;
  playId: number;
  devStats: boolean;
  fpsNode: React.RefObject<HTMLParagraphElement | null>;
  onNoWebGL2: () => void;
}

function Air({ park, bg }: { park: ParkSide; bg: string }) {
  const scene = useThree((s) => s.scene);
  useLayoutEffect(() => {
    scene.background = new THREE.Color(bg);
    scene.fog = new THREE.Fog(bg, park === 'harp' ? 80 : 130, park === 'harp' ? 470 : 640);
  }, [scene, park, bg]);
  return null;
}

function CameraRig({ view, reduced, free }: { view: ViewId; reduced: boolean; free: boolean }) {
  const ref = useRef<CameraControls>(null);
  const camera = useThree((s) => s.camera);
  useLayoutEffect(() => {
    const controls = ref.current;
    if (!controls) return;
    const orbit = free && !reduced;
    controls.mouseButtons.left = orbit ? 1 : 0;
    controls.mouseButtons.right = 0;
    controls.mouseButtons.middle = 0;
    controls.mouseButtons.wheel = orbit ? 16 : 0;
    controls.touches.one = orbit ? 32 : 0;
    controls.touches.two = 0;
    controls.touches.three = 0;
    const shot = VIEWS[view];
    const persp = camera as THREE.PerspectiveCamera;
    persp.fov = shot.fov;
    persp.updateProjectionMatrix();
    controls.smoothTime = cameraSmoothTime(reduced);
    void controls.setLookAt(
      shot.pos[0], shot.pos[1], shot.pos[2],
      shot.target[0], shot.target[1], shot.target[2],
      cameraMoves(reduced),
    );
  }, [camera, free, reduced, view]);
  return <CameraControls ref={ref} smoothTime={cameraSmoothTime(reduced)} />;
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
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.05, 0]}>
      <shapeGeometry args={[shape]} />
      <meshStandardMaterial color={color} roughness={0.9} />
    </mesh>
  );
}

function dirtMap(): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 32;
  canvas.height = 32;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    ctx.fillStyle = '#6b4f3a';
    ctx.fillRect(0, 0, 32, 32);
    for (let i = 0; i < 32; i += 1) {
      ctx.fillStyle = i % 2 === 0 ? '#5c4332' : '#7d6248';
      ctx.fillRect((i * 7) % 32, (i * 13) % 32, 2, 2);
    }
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(3, 3);
  return tex;
}

function Field({ c, park }: { c: Palette; park: ParkSide }) {
  const profile = skylineProfile(park);
  const dirt = useMemo(dirtMap, []);
  const tall = Math.max(...profile.stand);
  const crown = profile.stand.indexOf(tall);
  return (
    <group>
      {Array.from({ length: 12 }, (_, i) => (
        <mesh key={i} rotation={[-Math.PI / 2, 0, 0]} position={[-220 + i * 40, 0, -70]} receiveShadow>
          <planeGeometry args={[40, 300]} />
          <meshStandardMaterial color={i % 2 === 0 ? c.grass : c.grassDark} roughness={1} />
        </mesh>
      ))}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, -1.2]}>
        <circleGeometry args={[11, 22]} />
        <meshStandardMaterial color={c.dirt} map={dirt} roughness={1} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.025, MOUND_Z]}>
        <circleGeometry args={[16, 18]} />
        <meshStandardMaterial color={c.dirt} map={dirt} roughness={1} />
      </mesh>
      <mesh position={[0, MOUND_H / 2, MOUND_Z]}>
        <cylinderGeometry args={[2.4, 7.2, MOUND_H, 6]} />
        <meshStandardMaterial color={c.dirt} flatShading roughness={1} />
      </mesh>
      <mesh position={[0, MOUND_H + 0.05, MOUND_Z]}>
        <boxGeometry args={[2, 0.06, 0.5]} />
        <meshStandardMaterial color={c.chalk} roughness={0.8} />
      </mesh>
      <Plate color={c.chalk} />
      {([ [BASE, -BASE], [0, -BASE * 2], [-BASE, -BASE] ] as const).map(([x, z]) => (
        <mesh key={`${x}${z}`} position={[x, 0.16, z]} rotation={[0, Math.PI / 4, 0]}>
          <boxGeometry args={[1.2, 0.22, 1.2]} />
          <meshStandardMaterial color={c.chalk} roughness={0.85} />
        </mesh>
      ))}
      <Line points={[[0, 0.07, 0], [170 / Math.SQRT2, 0.07, -170 / Math.SQRT2]]} color={c.chalk} lineWidth={1.5} />
      <Line points={[[0, 0.07, 0], [-170 / Math.SQRT2, 0.07, -170 / Math.SQRT2]]} color={c.chalk} lineWidth={1.5} />
      {[ -1, 1 ].map((s) => (
        <mesh key={s} position={[s * 118, 9, -118]}>
          <boxGeometry args={[0.35, 18, 0.35]} />
          <meshStandardMaterial color={c.red} flatShading />
        </mesh>
      ))}
      <mesh position={[0, 6, -128]}>
        <boxGeometry args={[240, 12, 1.6]} />
        <meshStandardMaterial color={c.surface2} flatShading />
      </mesh>
      {profile.stand.map((h, i) => {
        const x = -90 + i * 30;
        return (
          <group key={h + i}>
            <mesh position={[x, h / 2, -148]}>
              <boxGeometry args={[24, h, 18]} />
              <meshStandardMaterial color={c.surface} flatShading />
            </mesh>
            {Array.from({ length: 5 }, (_, k) => (
              <mesh key={k} position={[x - 8 + k * 4, h + 0.7, -140]} castShadow>
                <boxGeometry args={[1.1, 1.3, 0.8]} />
                <meshStandardMaterial color={k % 2 === 0 ? c.red : c.chalk} flatShading />
              </mesh>
            ))}
            {i === crown ? (
              <mesh position={[x, h + 0.45, -148]}>
                <boxGeometry args={[24, 0.9, 18]} />
                <meshStandardMaterial color={c.red} flatShading />
              </mesh>
            ) : null}
          </group>
        );
      })}
      {profile.ridges ? (
        <group>
          <mesh position={[0, 42, -260]}>
            <planeGeometry args={[720, 100]} />
            <meshBasicMaterial color={c.surface} />
          </mesh>
          {([[-78, 24, 36], [-20, 40, 44], [36, 28, 32], [88, 18, 26]] as const).map(([x, h, r]) => (
            <mesh key={x} position={[x, h / 2, -200]}>
              <coneGeometry args={[r, h, 5]} />
              <meshBasicMaterial color={c.bg} />
            </mesh>
          ))}
        </group>
      ) : (
          <mesh position={[0, 4, -230]} rotation={[-0.2, 0, 0]}>
            <planeGeometry args={[640, 22]} />
            <meshBasicMaterial color={c.sea} transparent opacity={0.35} />
          </mesh>
        )}
      {[ -1, 1 ].map((s) => (
        <group key={s} position={[s * 86, 0, -36]}>
          <mesh position={[0, 16, 0]}>
            <boxGeometry args={[1.1, 32, 1.1]} />
            <meshStandardMaterial color={c.surface2} flatShading />
          </mesh>
          <mesh position={[0, 32.5, 0]} rotation={[0.45, s * -0.35, 0]}>
            <boxGeometry args={[16, 2.4, 0.8]} />
            <meshStandardMaterial color={c.chalk} emissive={c.chalk} emissiveIntensity={0.7} flatShading />
          </mesh>
        </group>
      ))}
    </group>
  );
}

function ZoneMark({ c, hand }: { c: Palette; hand: Hand }) {
  const { half: h, bottom: b, top: t, z } = ZONE;
  const width = (h * 2) / 3;
  const x = (hand === 'R' ? -1 : 1) * (h - width / 2);
  const third = (t - b) / 3;
  return (
    <group>
      <mesh position={[x, (b + t) / 2, z]}>
        <planeGeometry args={[width, t - b]} />
        <meshBasicMaterial color={c.red} transparent opacity={0.28} side={THREE.DoubleSide} depthWrite={false} />
      </mesh>
      <Line points={[[-h, b, z], [h, b, z], [h, t, z], [-h, t, z], [-h, b, z]]} color={c.fg} lineWidth={1.6} />
      {[1, 2].map((i) => (
        <group key={i}>
          <Line points={[[-h + (2 * h * i) / 3, b, z], [-h + (2 * h * i) / 3, t, z]]} color={c.fg} lineWidth={1} transparent opacity={0.35} />
          <Line points={[[-h, b + third * i, z], [h, b + third * i, z]]} color={c.fg} lineWidth={1} transparent opacity={0.35} />
        </group>
      ))}
    </group>
  );
}

function Batter({ hand, reduced, c }: { hand: Hand; reduced: boolean; c: Palette }) {
  const ref = useRef<THREE.Group>(null);
  const anim = useRef({ from: hand, to: hand, t: 1 });
  useLayoutEffect(() => {
    const frame = batterFrame(hand, hand, 1);
    ref.current?.position.set(frame.x, frame.y, frame.z);
    ref.current?.scale.set(frame.mirror, 1, 1);
  }, [hand]);
  useEffect(() => {
    const prev = anim.current.to;
    anim.current = { from: prev, to: hand, t: reduced || prev === hand ? 1 : 0 };
  }, [hand, reduced]);
  useFrame((_, dt) => {
    const node = ref.current;
    if (!node) return;
    const a = anim.current;
    if (reduced) a.t = 1;
    else if (a.t < 1) a.t = Math.min(1, a.t + dt / 0.72);
    const frame = batterFrame(a.from, a.to, a.t);
    node.position.set(frame.x, frame.y, frame.z);
    node.scale.set(frame.mirror, 1, 1);
  });
  return (
    <group ref={ref}>
      <mesh position={[-0.28, 1.15, 0]}>
        <boxGeometry args={[0.28, 2.1, 0.28]} />
        <meshStandardMaterial color={c.dirt} flatShading />
      </mesh>
      <mesh position={[0.28, 1.15, 0]}>
        <boxGeometry args={[0.28, 2.1, 0.28]} />
        <meshStandardMaterial color={c.dirt} flatShading />
      </mesh>
      <mesh position={[0, 2.7, 0]}>
        <boxGeometry args={[1.15, 1.35, 0.55]} />
        <meshStandardMaterial color={c.chalk} flatShading />
      </mesh>
      <mesh position={[0, 2.12, 0]}>
        <boxGeometry args={[1.18, 0.16, 0.58]} />
        <meshStandardMaterial color={c.red} flatShading />
      </mesh>
      <mesh position={[0, 3.72, 0]}>
        <boxGeometry args={[0.48, 0.48, 0.48]} />
        <meshStandardMaterial color={c.surface2} flatShading />
      </mesh>
      <mesh position={[0.9, 2.5, 0.4]} rotation={[0.25, 0, -0.85]}>
        <boxGeometry args={[0.12, 2.3, 0.12]} />
        <meshStandardMaterial color={c.dirt} flatShading />
      </mesh>
    </group>
  );
}

function Seams({ color }: { color: string }) {
  return (
    <group>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[BALL_R * 0.92, BALL_R * 0.08, 6, 18]} />
        <meshStandardMaterial color={color} roughness={0.55} />
      </mesh>
      <mesh rotation={[0.4, 0.2, Math.PI / 2.6]}>
        <torusGeometry args={[BALL_R * 0.92, BALL_R * 0.08, 6, 18]} />
        <meshStandardMaterial color={color} roughness={0.55} />
      </mesh>
    </group>
  );
}

function Pitcher({ playId, reduced, c }: { playId: number; reduced: boolean; c: Palette }) {
  const arm = useRef<THREE.Group>(null);
  const start = useRef(-1);
  useLayoutEffect(() => {
    start.current = -1;
  }, [playId]);
  useFrame(({ clock }) => {
    const node = arm.current;
    if (!node) return;
    if (reduced) {
      node.rotation.x = -0.35;
      return;
    }
    if (start.current < 0) start.current = clock.elapsedTime;
    const u = Math.min(1, (clock.elapsedTime - start.current) / 0.7);
    node.rotation.x = -0.25 - Math.sin(u * Math.PI) * 1.35;
  });
  return (
    <group position={[0.4, MOUND_H, MOUND_Z + 0.3]}>
      <mesh position={[0, 1.7, 0]} castShadow>
        <boxGeometry args={[0.7, 1.5, 0.4]} />
        <meshStandardMaterial color={c.chalk} flatShading />
      </mesh>
      <mesh position={[0, 2.7, 0]} castShadow>
        <boxGeometry args={[0.36, 0.36, 0.36]} />
        <meshStandardMaterial color={c.surface2} flatShading />
      </mesh>
      <group ref={arm} position={[0.42, 2.15, 0.1]}>
        <mesh position={[0, -0.45, 0]} castShadow>
          <boxGeometry args={[0.14, 1.15, 0.14]} />
          <meshStandardMaterial color={c.dirt} flatShading />
        </mesh>
      </group>
    </group>
  );
}

function Paths({ harp, sea, reduced, playId, c }: { harp: Vec3[]; sea: Vec3[]; reduced: boolean; playId: number; c: Palette }) {
  const live = useRef<THREE.Group>(null);
  const ghost = useRef<THREE.Mesh>(null);
  const start = useRef(-1);
  useLayoutEffect(() => {
    start.current = -1;
    const u = reduced ? 1 : 0;
    const a = pointAt(harp, u);
    const b = pointAt(sea, u);
    live.current?.position.set(a[0], a[1], a[2]);
    ghost.current?.position.set(b[0], b[1], b[2]);
    if (live.current && reduced) live.current.rotation.set(0, 0, 0);
  }, [harp, sea, playId, reduced]);
  useFrame(({ clock }) => {
    if (start.current < 0) start.current = clock.elapsedTime;
    const u = reduced ? 1 : Math.min(1, (clock.elapsedTime - start.current) / 1.7);
    const a = pointAt(harp, u);
    const b = pointAt(sea, u);
    live.current?.position.set(a[0], a[1], a[2]);
    ghost.current?.position.set(b[0], b[1], b[2]);
    if (live.current && !reduced) live.current.rotation.x = u * Math.PI * 8;
  });
  return (
    <group>
      <Line points={sea} color={c.sea} lineWidth={2} dashed dashSize={0.8} gapSize={0.45} transparent opacity={0.85} />
      <Line points={harp} color={c.red} lineWidth={2.5} />
      <mesh ref={ghost}>
        <icosahedronGeometry args={[BALL_R, 0]} />
        <meshStandardMaterial color={c.sea} transparent opacity={0.5} flatShading />
      </mesh>
      <group ref={live}>
        <mesh castShadow>
          <sphereGeometry args={[BALL_R, 18, 14]} />
          <meshStandardMaterial color={c.ball} roughness={0.4} />
        </mesh>
        <Seams color={c.red} />
      </group>
    </group>
  );
}

function Fps({ node }: { node: React.RefObject<HTMLParagraphElement | null> }) {
  const acc = useRef({ n: 0, t: -1 });
  useFrame(({ clock }) => {
    const el = node.current;
    if (!el) return;
    if (acc.current.t < 0) acc.current.t = clock.elapsedTime;
    acc.current.n += 1;
    const dt = clock.elapsedTime - acc.current.t;
    if (dt < 0.5) return;
    el.textContent = `${Math.round(acc.current.n / dt)} fps`;
    acc.current.n = 0;
    acc.current.t = clock.elapsedTime;
  });
  return null;
}

function Stage(props: WorldProps) {
  const c = useMemo(palette, []);
  return (
    <>
      <Air park={props.park} bg={c.bg} />
      <hemisphereLight args={['#243044', c.bg, 0.28]} />
      <directionalLight
        position={[28, 70, -10]}
        intensity={1.15}
        color={c.chalk}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
        shadow-camera-near={8}
        shadow-camera-far={180}
        shadow-camera-left={-70}
        shadow-camera-right={70}
        shadow-camera-top={70}
        shadow-camera-bottom={-70}
      />
      <pointLight position={[-86, 34, -36]} intensity={2.4} decay={0} color={c.chalk} />
      <pointLight position={[86, 34, -36]} intensity={2.4} decay={0} color={c.chalk} />
      <CameraRig view={props.view} reduced={props.reduced} free={props.free} />
      <Field c={c} park={props.park} />
      <ZoneMark c={c} hand={props.hand} />
      <Pitcher playId={props.playId} reduced={props.reduced} c={c} />
      <Batter hand={props.hand} reduced={props.reduced} c={c} />
      <Paths harp={props.harpPath} sea={props.seaPath} reduced={props.reduced} playId={props.playId} c={c} />
      {props.devStats ? <Fps node={props.fpsNode} /> : null}
    </>
  );
}

export default function World(props: WorldProps) {
  const c = useMemo(palette, []);
  return (
    <div className="sim-world">
      <Canvas
        dpr={[1, 1.5]}
        frameloop="always"
        gl={{ antialias: true, powerPreference: 'high-performance', stencil: false, alpha: false }}
        camera={{ position: VIEWS.catcher.pos, fov: VIEWS.catcher.fov, near: 0.2, far: 900 }}
        onCreated={({ gl }) => {
          gl.shadowMap.enabled = true;
          gl.shadowMap.type = THREE.PCFSoftShadowMap;
          if (!gl.capabilities.isWebGL2) props.onNoWebGL2();
        }}
      >
        <Stage {...props} />
        <color attach="background" args={[c.bg]} />
      </Canvas>
    </div>
  );
}
