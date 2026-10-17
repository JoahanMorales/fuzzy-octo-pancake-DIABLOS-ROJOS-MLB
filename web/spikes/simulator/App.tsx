/* Simulator spike shell: DOM HUD over the r3f canvas. HUD chips top-left, controls in the right rail, lower-third
   readout with 4 values (web/DESIGN.md). The scene lazy-loads so the HUD paints first. */
import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowsLeftRight, Play } from '@phosphor-icons/react';
import Fallback2D from './Fallback2D';
import { fmt, PITCHES, PRESET_NOTE, RHO_HH, RHO_SEA, throwPitch, type Hand } from './model';
import type { View } from './Scene';

const Scene = lazy(() => import('./Scene'));

const VIEW_LABEL: Record<View, string> = { catcher: 'Catcher', pitcher: 'Pitcher', lateral: 'Lateral', broadcast: 'Transmisión' };
const SLOW = 0.22;

function useReducedMotion() {
  const q = '(prefers-reduced-motion: reduce)';
  const [reduced, setReduced] = useState(() => typeof matchMedia !== 'undefined' && matchMedia(q).matches);
  useEffect(() => {
    const m = matchMedia(q);
    const on = () => setReduced(m.matches);
    m.addEventListener('change', on);
    return () => m.removeEventListener('change', on);
  }, []);
  return reduced;
}

function hasWebGL() {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') || c.getContext('webgl'));
  } catch {
    return false;
  }
}

function Seg<T extends string>({ label, value, options, onChange, grid }: {
  label: string; value: T; options: [T, string][]; onChange: (v: T) => void; grid?: boolean;
}) {
  return (
    <fieldset className={`seg ${grid ? 'seg-grid' : ''}`}>
      <legend>{label}</legend>
      <div className="seg-row">
        {options.map(([v, text]) => (
          <button key={v} type="button" aria-pressed={value === v} onClick={() => onChange(v)}>
            {text}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

export default function App() {
  const reduced = useReducedMotion();
  const webgl = useMemo(hasWebGL, []);
  const [pitchId, setPitchId] = useState(PITCHES[0].id);
  const [view, setView] = useState<View>('catcher');
  const [batter, setBatter] = useState<Hand>('R');
  const [hand, setHand] = useState<Hand>('R');
  const [slow, setSlow] = useState(true);
  const [playId, setPlayId] = useState(0);
  const [landed, setLanded] = useState(false);

  const pitch = PITCHES.find((p) => p.id === pitchId) ?? PITCHES[0];
  const thrown = useMemo(() => throwPitch(pitch), [pitch]);
  const replay = useCallback(() => {
    setLanded(false);
    setPlayId((n) => n + 1);
  }, []);
  useEffect(replay, [pitchId, hand, replay]);

  const { sea, hh } = thrown;
  const dz = (hh.plate_z - sea.plate_z) * 12;
  const summary =
    `${pitch.label} de ejemplo a ${pitch.release.velo_mph} mph. En el aire del Harp Helú el quiebre vertical pasa de ` +
    `${fmt(sea.ivb_in)} a ${fmt(hh.ivb_in)} pulgadas y cruza el plato ${fmt(Math.abs(dz))} pulgadas más ` +
    `${dz < 0 ? 'abajo' : 'arriba'} que a nivel del mar.`;

  const readout = [
    { label: 'Quiebre vertical', unit: 'in', hh: hh.ivb_in, sea: sea.ivb_in },
    { label: 'Quiebre horizontal', unit: 'in', hh: hh.hb_in, sea: sea.hb_in },
    { label: 'Llega al plato', unit: 'mph', hh: hh.plate_mph, sea: sea.plate_mph },
  ];

  return (
    <div className={`sim ${landed || !webgl ? "is-landed" : ""}`}>
      <div className="stage">
        <div className="scene-wrap">
        {webgl ? (
          <Suspense fallback={<div className="scene-loading" aria-hidden />}>
            <Scene
              thrown={thrown}
              hand={hand}
              batter={batter}
              view={view}
              playId={playId}
              slow={slow ? SLOW : 1}
              reduced={reduced}
              onLanded={() => setLanded(true)}
            />
          </Suspense>
        ) : (
          <div className="no-webgl">
            <p>Tu navegador no tiene WebGL. Te mostramos la vista del catcher en 2D con los mismos datos.</p>
            <Fallback2D thrown={thrown} hand={hand} />
          </div>
        )}
        </div>

        <header className="hud-top">
          <h1>Mismo lanzamiento, dos aires</h1>
          <div className="chips" role="group" aria-label="Tipo de lanzamiento">
            {PITCHES.map((p) => (
              <button key={p.id} type="button" className="chip" aria-pressed={p.id === pitchId} onClick={() => setPitchId(p.id)}>
                {p.label}
              </button>
            ))}
          </div>
        </header>

        <aside className="rail" aria-label="Controles del simulador">
          <button type="button" className="btn-primary" onClick={replay}>
            <Play weight="fill" size={16} aria-hidden /> Lanzar
          </button>
          <Seg grid label="Cámara" value={view} onChange={setView} options={(Object.keys(VIEW_LABEL) as View[]).map((v) => [v, VIEW_LABEL[v]])} />
          <fieldset className="seg">
            <legend>Bateador</legend>
            <button type="button" className="btn-switch" onClick={() => setBatter((b) => (b === 'R' ? 'L' : 'R'))}>
              <ArrowsLeftRight size={16} aria-hidden />
              {batter === 'R' ? 'Derecho' : 'Zurdo'}
              <span className="hint">cambiar</span>
            </button>
          </fieldset>
          <Seg label="Lanzador" value={hand} onChange={setHand} options={[['R', 'Derecho'], ['L', 'Zurdo']]} />
          <Seg label="Velocidad" value={slow ? 'slow' : 'real'} onChange={(v) => setSlow(v === 'slow')} options={[['slow', 'Cámara lenta'], ['real', 'Real']]} />
          <ul className="legend">
            <li>
              <svg width="28" height="8" aria-hidden><line x1="0" y1="4" x2="28" y2="4" className="lg-hh" /></svg>
              Aire del Harp Helú <span className="mono">ρ {RHO_HH.toFixed(3)}</span>
            </li>
            <li>
              <svg width="28" height="8" aria-hidden><line x1="0" y1="4" x2="28" y2="4" className="lg-sea" /></svg>
              Nivel del mar <span className="mono">ρ {RHO_SEA.toFixed(3)}</span>
            </li>
          </ul>
          <p className="note">
            Lanzamiento de ejemplo, no de un pitcher real. Física: RK4 con arrastre y Magnus; el Magnus escala con
            ρ<sup>{pitch.elasticity.toFixed(2)}</sup>, la elasticidad medida en la LMB para la {pitch.label.toLowerCase()}.
          </p>
        </aside>

        <section className="readout" aria-label="Lectura del lanzamiento">
          {readout.map((r) => (
            <div key={r.label} className="cell">
              <span className="cell-label">{r.label}</span>
              <span className="cell-value">
                {fmt(r.hh)}
                <small>{r.unit}</small>
              </span>
              <span className="cell-sub">
                nivel del mar {fmt(r.sea)} · <b>{fmt(r.hh - r.sea, 1, true)}</b>
              </span>
            </div>
          ))}
          <div className="cell cell-key">
            <span className="cell-label">Diferencia en el plato</span>
            <span className="cell-value">
              {fmt(thrown.plateGapIn)}
              <small>in</small>
            </span>
            <span className="cell-sub">
              {fmt(Math.abs(dz))} in más {dz < 0 ? 'abajo' : 'arriba'} con el mismo release
            </span>
          </div>
        </section>
      </div>
      <p className="sr-only" aria-live="polite">{landed ? summary : ''}</p>
      <p className="sr-only">{PRESET_NOTE}</p>
    </div>
  );
}
