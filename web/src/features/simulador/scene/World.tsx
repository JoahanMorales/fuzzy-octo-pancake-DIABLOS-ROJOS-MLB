/* r3f only. Motion stays out of this tree (web/DESIGN.md). */
import { useLayoutEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { CameraControls, Line } from '@react-three/drei';
import * as THREE from 'three';
import { Batter, Pitcher, type Look } from './figures';
import { Backdrop, Field, Sky, Stands } from './stadium';
import { ballTexture } from './textures';
import {
  BALL_R,
  VIEWS,
  ZONE,
  cameraMoves,
  cameraSmoothTime,
  palette,
  pointAt,
  type Hand,
  type Palette,
  type ParkSide,
  type Vec3,
  type ViewId,
} from './sceneModel';


export interface WorldProps {
  view: ViewId;
  hand: Hand;
  throws: Hand;
  spin: number;
  axis: number;
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
    scene.fog = new THREE.Fog(bg, park === 'harp' ? 420 : 520, park === 'harp' ? 1900 : 2300);
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

function ZoneMark({ c, hand }: { c: Palette; hand: Hand }) {
  const { half: h, bottom: b, top: t, z } = ZONE;
  const width = (h * 2) / 3;
  const x = (hand === 'R' ? -1 : 1) * (h - width / 2);
  const third = (t - b) / 3;
  return (
    <group>
      <mesh position={[x, (b + t) / 2, z]}>
        <planeGeometry args={[width, t - b]} />
        <meshBasicMaterial color={c.red} transparent opacity={0.1} side={THREE.DoubleSide} depthWrite={false} />
      </mesh>
      <Line points={[[-h, b, z], [h, b, z], [h, t, z], [-h, t, z], [-h, b, z]]} color={c.fg} lineWidth={1.6} transparent opacity={0.85} />
      {[1, 2].map((i) => (
        <group key={i}>
          <Line points={[[-h + (2 * h * i) / 3, b, z], [-h + (2 * h * i) / 3, t, z]]} color={c.fg} lineWidth={1} transparent opacity={0.25} />
          <Line points={[[-h, b + third * i, z], [h, b + third * i, z]]} color={c.fg} lineWidth={1} transparent opacity={0.25} />
        </group>
      ))}
    </group>
  );
}

/** Seconds of windup before the ball leaves the hand (the flight animation starts then). */
const WINDUP = 0.9;
/** The 1.7 s on screen show a ~0.42 s flight: the spin is slowed by the same factor. */
const SLOW = 1.7 / 0.42;

const HOME: Look = { jersey: '#e9e6df', pants: '#d8d4cb', skin: '#9a7a62', dark: '#1d2230', helmet: '#1d2230' };
const AWAY: Look = { jersey: '#8f949c', pants: '#7d828a', skin: '#8c6e58', dark: '#1d2230', helmet: '#2a2f3a' };

function spinAxis(axisDeg: number, throws: Hand): THREE.Vector3 {
  // Trackman spin axis in the catcher's view: 180 = pure backspin (rotation about -x), 90/270 = sidespin.
  const phi = ((axisDeg - 180) * Math.PI) / 180;
  return new THREE.Vector3(-Math.cos(phi) * (throws === 'R' ? 1 : -1), Math.sin(phi), 0).normalize();
}

function Paths({ harp, sea, reduced, playId, c, spin, axis, throws }: {
  harp: Vec3[]; sea: Vec3[]; reduced: boolean; playId: number; c: Palette; spin: number; axis: number; throws: Hand;
}) {
  const live = useRef<THREE.Group>(null);
  const ghost = useRef<THREE.Mesh>(null);
  const start = useRef(-1);
  const leather = useMemo(() => ballTexture(c.ball, c.red), [c]);
  const w = useMemo(() => spinAxis(axis, throws), [axis, throws]);
  const q = useMemo(() => new THREE.Quaternion(), []);
  useLayoutEffect(() => {
    start.current = -1;
    const u = reduced ? 1 : 0;
    const a = pointAt(harp, u);
    const b = pointAt(sea, u);
    live.current?.position.set(a[0], a[1], a[2]);
    ghost.current?.position.set(b[0], b[1], b[2]);
  }, [harp, sea, playId, reduced]);
  useFrame(({ clock }, dt) => {
    if (start.current < 0) start.current = clock.elapsedTime;
    const t = clock.elapsedTime - start.current - WINDUP;
    const u = reduced ? 1 : Math.min(1, Math.max(0, t) / 1.7);
    const a = pointAt(harp, u);
    const b = pointAt(sea, u);
    const flying = !reduced && t >= 0;
    if (live.current) {
      live.current.visible = reduced || t >= 0;
      live.current.position.set(a[0], a[1], a[2]);
      if (flying && u < 1) live.current.quaternion.premultiply(q.setFromAxisAngle(w, ((spin / 60) * 2 * Math.PI * Math.min(dt, 0.05)) / SLOW));
    }
    if (ghost.current) {
      ghost.current.visible = reduced || t >= 0;
      ghost.current.position.set(b[0], b[1], b[2]);
    }
  });
  return (
    <group>
      <Line points={sea} color={c.sea} lineWidth={2} dashed dashSize={0.8} gapSize={0.45} transparent opacity={0.85} />
      <Line points={harp} color={c.red} lineWidth={2.5} />
      <mesh position={sea[sea.length - 1]}>
        <ringGeometry args={[BALL_R * 0.7, BALL_R * 1.05, 24]} />
        <meshBasicMaterial color={c.sea} side={THREE.DoubleSide} />
      </mesh>
      <mesh position={harp[harp.length - 1]}>
        <circleGeometry args={[BALL_R * 1.05, 24]} />
        <meshBasicMaterial color={c.red} side={THREE.DoubleSide} />
      </mesh>
      <mesh ref={ghost}>
        <sphereGeometry args={[BALL_R, 16, 12]} />
        <meshStandardMaterial color={c.sea} transparent opacity={0.5} />
      </mesh>
      <group ref={live}>
        <mesh castShadow>
          <sphereGeometry args={[BALL_R, 32, 20]} />
          <meshStandardMaterial map={leather} roughness={0.55} />
        </mesh>
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
  const release = props.harpPath[0] ?? [-1.8, 6, -54.2];
  return (
    <>
      <Air park={props.park} bg={props.park === 'harp' ? '#141a26' : '#12202b'} />
      <Sky park={props.park} />
      <hemisphereLight args={['#6d7fa0', '#1f3324', 0.55]} />
      <directionalLight
        position={[-150, 170, -40]}
        intensity={2.1}
        color="#fff4e6"
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-bias={-0.0004}
        shadow-camera-near={50}
        shadow-camera-far={420}
        shadow-camera-left={-75}
        shadow-camera-right={75}
        shadow-camera-top={75}
        shadow-camera-bottom={-75}
      />
      <directionalLight position={[160, 150, -90]} intensity={1.15} color="#f2f0ff" />
      <directionalLight position={[0, 90, 160]} intensity={0.45} color="#c9d4ff" />
      <CameraRig view={props.view} reduced={props.reduced} free={props.free} />
      <Backdrop park={props.park} />
      <Stands c={c} />
      <Field c={c} />
      <ZoneMark c={c} hand={props.hand} />
      <Pitcher throws={props.throws} release={release} reduced={props.reduced} playId={props.playId} look={AWAY} windup={WINDUP} />
      <Batter hand={props.hand} reduced={props.reduced} playId={props.playId} look={HOME} windup={WINDUP} />
      <Paths harp={props.harpPath} sea={props.seaPath} reduced={props.reduced} playId={props.playId} c={c}
        spin={props.spin} axis={props.axis} throws={props.throws} />
      {props.devStats ? <Fps node={props.fpsNode} /> : null}
    </>
  );
}

export default function World(props: WorldProps) {
  return (
    <div className="sim-world">
      <Canvas
        dpr={[1, 1.5]}
        frameloop="always"
        gl={{ antialias: true, powerPreference: 'high-performance', stencil: false, alpha: false }}
        camera={{ position: VIEWS.catcher.pos, fov: VIEWS.catcher.fov, near: 0.2, far: 4000 }}
        shadows
        onCreated={({ gl }) => {
          gl.shadowMap.enabled = true;
          gl.shadowMap.type = THREE.PCFSoftShadowMap;
          gl.toneMapping = THREE.ACESFilmicToneMapping;
          gl.toneMappingExposure = 1.15;
          if (!gl.capabilities.isWebGL2) props.onNoWebGL2();
        }}
      >
        <Stage {...props} />
      </Canvas>
    </div>
  );
}
