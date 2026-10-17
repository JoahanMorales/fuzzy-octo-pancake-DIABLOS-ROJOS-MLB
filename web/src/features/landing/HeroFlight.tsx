import { Line } from '@react-three/drei';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { useLayoutEffect, useMemo, useRef } from 'react';
import type { Mesh } from 'three';
import type { Flight } from '../../physics/flight';
import { toScene } from './story';

interface HeroFlightProps {
  sea: Flight;
  cdmx: Flight;
}

function sample(flight: Flight) {
  return flight.pos
    .filter((_, index) => index % 8 === 0 || index === flight.pos.length - 1)
    .map((point) => toScene(point));
}

function pointAt(points: [number, number, number][], t: number): [number, number, number] {
  const index = Math.min(points.length - 1, Math.floor(t * (points.length - 1)));
  return points[index];
}

function Scene({ sea, cdmx }: HeroFlightProps) {
  const seaPts = useMemo(() => sample(sea), [sea]);
  const cdmxPts = useMemo(() => sample(cdmx), [cdmx]);
  const seaBall = useRef<Mesh>(null);
  const cdmxBall = useRef<Mesh>(null);
  const progress = useRef(0);
  const { camera } = useThree();

  useLayoutEffect(() => {
    camera.lookAt(0, 1.5, -12);
  }, [camera]);

  useFrame((_, delta) => {
    progress.current = Math.min(1, progress.current + delta / 2.4);
    const seaAt = pointAt(seaPts, progress.current);
    const cdmxAt = pointAt(cdmxPts, progress.current);
    seaBall.current?.position.set(...seaAt);
    cdmxBall.current?.position.set(...cdmxAt);
  });

  return (
    <>
      <color attach="background" args={['#0c0c0e']} />
      <ambientLight intensity={0.4} />
      <pointLight position={[-3.2, 6, -1]} intensity={22} distance={24} color="#f1f1f3" />
      <pointLight position={[3.4, 5.5, -2]} intensity={14} distance={22} color="#f1f1f3" />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, -12]}>
        <planeGeometry args={[18, 40]} />
        <meshStandardMaterial color="#2f4a35" />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, -26]}>
        <circleGeometry args={[1.5, 18]} />
        <meshStandardMaterial color="#6b4f3a" />
      </mesh>
      <mesh position={[0, 1.25, 0.04]}>
        <planeGeometry args={[0.7, 1.0]} />
        <meshBasicMaterial color="#e8e6e1" transparent opacity={0.22} />
      </mesh>
      <Line points={seaPts} color="#c9ccd3" dashed dashSize={0.22} gapSize={0.12} lineWidth={1} />
      <Line points={cdmxPts} color="#c8102e" lineWidth={1} />
      <mesh ref={seaBall}>
        <sphereGeometry args={[0.07, 12, 12]} />
        <meshStandardMaterial color="#c9ccd3" transparent opacity={0.55} />
      </mesh>
      <mesh ref={cdmxBall}>
        <sphereGeometry args={[0.075, 14, 14]} />
        <meshStandardMaterial color="#efece6" />
      </mesh>
    </>
  );
}

export default function HeroFlight(props: HeroFlightProps) {
  return (
    <div className="landing-canvas">
      <Canvas
        data-testid="flight-canvas"
        style={{ width: '100%', height: '100%' }}
        camera={{ position: [0.2, 2.6, 5.2], fov: 36 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, powerPreference: 'high-performance' }}
      >
        <Scene {...props} />
      </Canvas>
    </div>
  );
}
