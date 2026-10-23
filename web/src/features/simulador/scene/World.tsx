/* r3f only. Motion stays out of this tree (web/DESIGN.md). */
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { CameraControls, Environment, Lightformer, PerformanceMonitor } from '@react-three/drei';
import { Bloom, BrightnessContrast, EffectComposer, HueSaturation, N8AO, SMAA, ToneMapping, Vignette } from '@react-three/postprocessing';
import { ToneMappingMode } from 'postprocessing';
import * as THREE from 'three';
import { GhostBatter, TrackedFlights, ZoneGlass } from './broadcast';
import { DayHorizon, DaySky, GrassBlades, GrassField, SUN } from './daypark';
import { Surroundings } from './surroundings';
import { ballTexture } from './textures';
import {
  BALL_R,
  VIEWS,
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
    scene.fog = new THREE.Fog(bg, 700, 4200);
  }, [scene, park, bg]);
  return null;
}

function CameraRig({ view, reduced, free }: { view: ViewId; reduced: boolean; free: boolean }) {
  const ref = useRef<CameraControls>(null);
  const camera = useThree((s) => s.camera);
  const size = useThree((s) => s.size);
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
    persp.fov = fovFor(shot.fov, size.width / Math.max(size.height, 1));
    persp.updateProjectionMatrix();
    controls.smoothTime = cameraSmoothTime(reduced);
    void controls.setLookAt(
      shot.pos[0], shot.pos[1], shot.pos[2],
      shot.target[0], shot.target[1], shot.target[2],
      cameraMoves(reduced),
    );
  }, [camera, free, reduced, view, size.width, size.height]);
  return <CameraControls ref={ref} smoothTime={cameraSmoothTime(reduced)} />;
}

/** The views are framed for a landscape canvas (about 5:4 or wider). On a portrait phone canvas the same vertical
 *  FOV crops the batter and the zone, so keep the horizontal FOV of that reference aspect instead (HACK-086). */
const FRAME_ASPECT = 1.25;
export function fovFor(fov: number, aspect: number): number {
  if (!(aspect > 0) || aspect >= FRAME_ASPECT) return fov;
  const half = (fov * Math.PI) / 360;
  return (Math.atan((Math.tan(half) * FRAME_ASPECT) / aspect) * 360) / Math.PI;
}

/** Seconds of windup before the ball leaves the hand (the flight animation starts then). */
const WINDUP = 0.35;
/** The 1.7 s on screen show a ~0.42 s flight: the spin is slowed by the same factor. */
const SLOW = 1.7 / 0.42;


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

/** frameloop="demand": render only while something moves (a throw, a batter switch, a camera move), so an idle
 *  simulator costs nothing on a laptop. CameraControls invalidates by itself while it moves. */
function Animate({ keys }: { keys: unknown[] }) {
  const invalidate = useThree((s) => s.invalidate);
  useEffect(() => {
    let raf = 0;
    const until = performance.now() + 4200;
    const tick = () => {
      invalidate();
      if (performance.now() < until) raf = requestAnimationFrame(tick);
    };
    tick();
    return () => cancelAnimationFrame(raf);
  }, keys); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

function Stage(props: WorldProps) {
  const c = useMemo(palette, []);
  // Adaptive quality: bloom and vignette only if the machine keeps a high frame rate.
  const [rich, setRich] = useState(false);
  const timing = useMemo(() => ({ windup: WINDUP, duration: 1.7 }), []);
  return (
    <>
      <Air park={props.park} bg={props.park === 'harp' ? '#a9cff5' : '#cfe1f2'} />
      <DaySky park={props.park} />
      <DayHorizon park={props.park} />
      <hemisphereLight args={['#bcd6f5', '#3d6b33', 1.1]} />
      <directionalLight
        position={SUN.clone().multiplyScalar(320).toArray()}
        intensity={3.2}
        color="#fff3df"
        castShadow
        shadow-mapSize-width={rich ? 2048 : 1024}
        shadow-mapSize-height={rich ? 2048 : 1024}
        shadow-bias={-0.0004}
        shadow-camera-near={50}
        shadow-camera-far={700}
        shadow-camera-left={-110}
        shadow-camera-right={110}
        shadow-camera-top={110}
        shadow-camera-bottom={-110}
      />
      {/* image-based light from procedural light cards: sky dome, sun, ground bounce (no HDR download) */}
      <Environment resolution={128} frames={1}>
        <Lightformer form="rect" intensity={1.4} color="#9cc6f2" scale={[40, 40, 1]} position={[0, 20, 0]} rotation={[Math.PI / 2, 0, 0]} />
        <Lightformer form="circle" intensity={6} color="#fff1d6" scale={6} position={SUN.clone().multiplyScalar(18).toArray()} />
        <Lightformer form="rect" intensity={0.6} color="#4f8a3a" scale={[40, 40, 1]} position={[0, -6, 0]} rotation={[-Math.PI / 2, 0, 0]} />
      </Environment>
      <CameraRig view={props.view} reduced={props.reduced} free={props.free} />
      <GrassField c={c} />
      <Surroundings park={props.park} />
      <GrassBlades count={rich ? 70000 : 30000} animate={!props.reduced} />
      <ZoneGlass c={c} />
      <GhostBatter hand={props.hand} reduced={props.reduced} solid />
      <TrackedFlights harp={props.harpPath} sea={props.seaPath} c={c} reduced={props.reduced} playId={props.playId}
        timing={timing}
        ball={<Paths harp={props.harpPath} sea={props.seaPath} reduced={props.reduced} playId={props.playId} c={c}
          spin={props.spin} axis={props.axis} throws={props.throws} />} />
      {props.devStats ? <Fps node={props.fpsNode} /> : null}
      <Animate keys={[props.playId, props.view, props.hand, props.park, props.throws, props.harpPath]} />
      <PerformanceMonitor flipflops={2} onIncline={() => setRich(true)} onDecline={() => setRich(false)} />
      {rich ? (
        <EffectComposer multisampling={0}>
          <N8AO halfRes aoRadius={3} distanceFalloff={1} intensity={2.2} color="#1a2418" />
          <Bloom mipmapBlur intensity={0.5} luminanceThreshold={0.85} luminanceSmoothing={0.2} />
          <ToneMapping mode={ToneMappingMode.ACES_FILMIC} />
          <HueSaturation saturation={0.04} />
          <BrightnessContrast contrast={0.08} />
          <Vignette offset={0.3} darkness={0.45} />
          <SMAA />
        </EffectComposer>
      ) : null}
    </>
  );
}

export default function World(props: WorldProps) {
  return (
    <div className="sim-world">
      <Canvas
        dpr={[1, 1.25]}
        frameloop="demand"
        shadows="soft"
        gl={{ antialias: true, powerPreference: 'high-performance', stencil: false, alpha: false }}
        camera={{ position: VIEWS.catcher.pos, fov: VIEWS.catcher.fov, near: 0.2, far: 6000 }}
        onCreated={({ gl }) => {
          gl.toneMapping = THREE.ACESFilmicToneMapping;
          gl.toneMappingExposure = 0.7;
          if (!gl.capabilities.isWebGL2) props.onNoWebGL2();
        }}
      >
        <Stage {...props} />
      </Canvas>
    </div>
  );
}
