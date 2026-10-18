/* Skinned mannequin (Quaternius, Universal Animation Library, CC0) posed every frame from the same joint keyframes
   as the low-poly figures: each limb bone is aimed at its target joint (orientation-agnostic, so no knowledge of the
   rig's local axes is needed). All the aiming happens in the rig's own space, so a mirrored parent (left-handers)
   never enters the quaternion math. */
import { useEffect, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import { clone } from 'three/examples/jsm/utils/SkeletonUtils.js';
import type { Look, Pose } from './figures';

export const MANNEQUIN_URL = `${import.meta.env.BASE_URL ?? './'}models/mannequin.glb`;
const FT = 3.28084;

type Chain = [bone: string, child: string, from: keyof Pose, to: keyof Pose];
const CHAINS: Chain[] = [
  ['DEF-spine.001', 'DEF-neck', 'pelvis', 'neck'],
  ['DEF-upper_arm.R', 'DEF-forearm.R', 'shoulderR', 'elbowR'],
  ['DEF-forearm.R', 'DEF-hand.R', 'elbowR', 'handR'],
  ['DEF-upper_arm.L', 'DEF-forearm.L', 'shoulderL', 'elbowL'],
  ['DEF-forearm.L', 'DEF-hand.L', 'elbowL', 'handL'],
  ['DEF-thigh.R', 'DEF-shin.R', 'hipR', 'kneeR'],
  ['DEF-shin.R', 'DEF-foot.R', 'kneeR', 'ankleR'],
  ['DEF-foot.R', 'DEF-toe.R', 'ankleR', 'toeR'],
  ['DEF-thigh.L', 'DEF-shin.L', 'hipL', 'kneeL'],
  ['DEF-shin.L', 'DEF-foot.L', 'kneeL', 'ankleL'],
  ['DEF-foot.L', 'DEF-toe.L', 'ankleL', 'toeL'],
];

/** Pose space → rig space (meters, +z forward, character's right at -x). `toRig` maps a pose point in feet. */
export type ToRig = (p: [number, number, number]) => THREE.Vector3;

export function Mannequin({ pose, look, toRig, helmet, onPosed, children }: {
  pose: React.MutableRefObject<Pose>;
  look: Look;
  toRig: ToRig;
  helmet?: boolean;
  children?: React.ReactNode;
  /** Called after posing with both hands' positions in rig space (meters). */
  onPosed?: (handL: THREE.Vector3, handR: THREE.Vector3) => void;
}) {
  const gltf = useGLTF(MANNEQUIN_URL);
  const rig = useMemo(() => {
    const r = clone(gltf.scene) as THREE.Object3D;
    const main = new THREE.MeshStandardMaterial({ color: look.jersey, roughness: 0.62, metalness: 0.0 });
    const joints = new THREE.MeshStandardMaterial({ color: look.dark, roughness: 0.4 });
    r.traverse((o) => {
      const m = o as THREE.SkinnedMesh;
      if (!m.isMesh) return;
      m.castShadow = true;
      m.receiveShadow = true;
      m.frustumCulled = false;
      const mats = Array.isArray(m.material) ? m.material : [m.material];
      m.material = mats.length > 1 ? mats.map((x) => (x.name === 'M_Joints' ? joints : main)) : (mats[0]?.name === 'M_Joints' ? joints : main);
    });
    return r;
  }, [gltf.scene, look]);

  const bones = useMemo(() => {
    // GLTFLoader sanitizes node names ("DEF-hand.L" -> "DEF-handL"): look them up the same way
    const raw = new Map<string, THREE.Object3D>();
    rig.traverse((o) => { if (o.name) raw.set(o.name, o); });
    const map = { get: (n: string) => raw.get(THREE.PropertyBinding.sanitizeNodeName(n)) ?? raw.get(n) };
    const rest = new Map<string, THREE.Quaternion>();
    for (const [b] of CHAINS) rest.set(b, map.get(b)!.quaternion.clone());
    const root = map.get('root')!;
    return { map, rest, hips: map.get('DEF-hips')!, root, rootRest: root.position.clone() };
  }, [rig]);

  const helmetRef = useRef<THREE.Mesh>(null);
  const tmp = useMemo(() => ({
    inv: new THREE.Matrix4(), m: new THREE.Matrix4(), p: new THREE.Vector3(), c: new THREE.Vector3(), d: new THREE.Vector3(),
    q: new THREE.Quaternion(), qb: new THREE.Quaternion(), qp: new THREE.Quaternion(), s: new THREE.Vector3(),
    hl: new THREE.Vector3(), hr: new THREE.Vector3(), head: new THREE.Vector3(),
  }), []);

  useEffect(() => () => { rig.traverse((o) => { const m = o as THREE.Mesh; if (m.isMesh) m.geometry?.dispose(); }); }, [rig]);

  const rel = (o: THREE.Object3D, outP?: THREE.Vector3, outQ?: THREE.Quaternion) => {
    tmp.m.multiplyMatrices(tmp.inv, o.matrixWorld);
    tmp.m.decompose(outP ?? tmp.p, outQ ?? tmp.q, tmp.s);
  };

  useFrame(() => {
    const p = pose.current;
    rig.updateMatrixWorld(true);
    tmp.inv.copy(rig.matrixWorld).invert();
    // pelvis: move the root (in its parent's space, which is the rig's) so the hips sit on the pose's pelvis
    const pelvis = toRig(p.pelvis);
    bones.root.position.copy(bones.rootRest);
    for (const [b] of CHAINS) bones.map.get(b)!.quaternion.copy(bones.rest.get(b)!);
    rig.updateMatrixWorld(true);
    tmp.inv.copy(rig.matrixWorld).invert();
    rel(bones.hips, tmp.p);
    bones.root.position.add(pelvis.clone().sub(tmp.p));
    rig.updateMatrixWorld(true);
    for (const [b, child, from, to] of CHAINS) {
      const bone = bones.map.get(b)!;
      const kid = bones.map.get(child)!;
      rel(bone, tmp.p);
      const bp = tmp.p.clone();
      rel(kid, tmp.c);
      const cur = tmp.c.clone().sub(bp).normalize();
      const want = toRig(p[to]).sub(toRig(p[from])).normalize();
      tmp.d.copy(want);
      const delta = new THREE.Quaternion().setFromUnitVectors(cur, tmp.d);
      rel(bone, undefined, tmp.qb);
      const qb = tmp.qb.clone();
      rel(bone.parent!, undefined, tmp.qp);
      bone.quaternion.copy(tmp.qp.clone().invert().multiply(delta.multiply(qb)));
      bone.updateMatrixWorld(true);
    }
    const hl = bones.map.get('DEF-hand.L')!, hr = bones.map.get('DEF-hand.R')!;
    rel(hl, tmp.hl);
    const left = tmp.hl.clone();
    rel(hr, tmp.hr);
    onPosed?.(left, tmp.hr.clone());
    if (helmetRef.current) {
      rel(bones.map.get('DEF-head')!, tmp.head);
      helmetRef.current.position.copy(tmp.head).add(new THREE.Vector3(0, 0.125, 0.005));
    }
  });

  return (
    <group scale={FT}>
      <primitive object={rig} />
      {helmet ? (
        <mesh ref={helmetRef} castShadow>
          <sphereGeometry args={[0.118, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2.15]} />
          <meshStandardMaterial color={look.helmet} roughness={0.22} metalness={0.15} />
        </mesh>
      ) : null}
      {children}
    </group>
  );
}

useGLTF.preload(MANNEQUIN_URL);
