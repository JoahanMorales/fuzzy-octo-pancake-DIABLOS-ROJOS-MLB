/* /fisica (HACK-072): why the fastball loses ride in CDMX air. A density slider from sea level to the Harp Helú
   throws the same release three ways (sea level, measured elasticity, textbook physics) with the browser RK4 engine,
   and shows the measured Magnus elasticity per family next to textbook physics (1). */
import { useDeferredValue, useEffect, useMemo, useState } from 'react';
import '../staff/pages.css';
import './style.css';
import { DataBadge, Status, useLoaded } from '../staff/data';
import {
  compare, FAMILY_LABEL, fmt, loadPhysics, NOUN, ORDER, pct, RHO_HARP, SHAPES, SHAPES_SOURCE, type PhysicsDoc,
} from './data';
import { CatcherView, ElasticityChart, SideView } from './views';

/** prefers-reduced-motion: the flights skip the draw animation and show the final frame. */
function useReducedMotion() {
  const query = '(prefers-reduced-motion: reduce)';
  const [reduced, setReduced] = useState(() => typeof window !== 'undefined' && window.matchMedia?.(query).matches === true);
  useEffect(() => {
    const media = window.matchMedia?.(query);
    if (!media) return;
    const on = () => setReduced(media.matches);
    media.addEventListener?.('change', on);
    return () => media.removeEventListener?.('change', on);
  }, []);
  return reduced;
}

export function Explainer({ doc }: { doc: PhysicsDoc }) {
  const motion = !useReducedMotion();
  const families = ORDER.filter((f) => doc.families.some((x) => x.pitch_family === f) && SHAPES.some((s) => s.pitch_family === f));
  const [family, setFamily] = useState(families[0] ?? 'Four-Seam');
  const [rho, setRho] = useState(RHO_HARP);
  const live = useDeferredValue(rho);
  const fam = doc.families.find((x) => x.pitch_family === family);
  const shape = SHAPES.find((s) => s.pitch_family === family);
  const cmp = useMemo(() => (fam && shape ? compare(shape, fam, live) : null), [fam, shape, live]);
  const anim = useMemo(() => Math.round(live * 1000) * 10 + families.indexOf(family), [live, family, families]);
  if (!fam || !shape || !cmp) return <p className="h48-error" role="alert">Falta la física de {family} en physics.json.</p>;

  const [noun, fem] = NOUN[family] ?? [family, false];
  const typical = `${noun} típic${fem ? 'a' : 'o'}`;
  const faster = cmp.measured.plateMph - cmp.sea.plateMph;
  const atSea = live >= 0.9995;
  const includesOne = fam.elasticity_lo <= 1 && fam.elasticity_hi >= 1;
  return (
    <>
      <div className="fis-controls">
        <div className="fis-families" role="radiogroup" aria-label="Tipo de lanzamiento">
          {families.map((f) => (
            <button key={f} type="button" role="radio" aria-checked={f === family} onClick={() => setFamily(f)}>
              {FAMILY_LABEL[f] ?? f}
            </button>
          ))}
        </div>
        <div className="fis-rho">
          <label htmlFor="fis-rho">Densidad del aire relativa al nivel del mar</label>
          <div className="fis-rho-row">
            <button type="button" onClick={() => setRho(RHO_HARP)} aria-pressed={rho === RHO_HARP}>Harp Helú</button>
            <input id="fis-rho" type="range" min={RHO_HARP} max={1} step={0.001} value={rho}
              onChange={(e) => setRho(Number(e.target.value))} aria-valuetext={`${fmt(rho, 3)} del nivel del mar`} />
            <button type="button" onClick={() => setRho(1)} aria-pressed={rho === 1}>Nivel del mar</button>
            <output htmlFor="fis-rho" className="fis-rho-value">ρ {fmt(rho, 3)}</output>
          </div>
        </div>
      </div>

      <dl className="fis-readout">
        <div><dt>Arrastre</dt><dd>{pct(cmp.drag)}</dd><span>del nivel del mar</span></div>
        <div className="is-hh"><dt>Magnus medido</dt><dd>{pct(cmp.magnusMeasured)}</dd><span>ρ elevada a {fmt(fam.elasticity, 2)}</span></div>
        <div><dt>Magnus de libro</dt><dd>{pct(cmp.magnusTextbook)}</dd><span>ρ elevada a 1</span></div>
        <div className="is-hh"><dt>Movimiento perdido</dt><dd>{fmt(cmp.moveLost)} in</dd><span>de libro: {fmt(cmp.moveLostTextbook)} in</span></div>
      </dl>

      <div className="fis-views">
        <SideView cmp={cmp} anim={anim} motion={motion} />
        <CatcherView cmp={cmp} anim={anim} motion={motion} />
      </div>

      <p className="fis-summary" aria-live="polite">
        {atSea
          ? `A nivel del mar las tres versiones coinciden: ${typical} (${fmt(shape.velo)} mph, ${fmt(shape.ivb)} in de subida inducida) no pierde nada.`
          : `Con ρ ${fmt(live, 3)}, ${typical} (${fmt(shape.velo)} mph) pierde ${fmt(cmp.moveLost)} in de movimiento y cruza el plato ${fmt(Math.abs(cmp.drop))} in más ${cmp.drop >= 0 ? 'abajo' : 'arriba'} que a nivel del mar. Con física de libro perdería ${fmt(cmp.moveLostTextbook)} in. Con menos arrastre llega ${fmt(Math.abs(faster), 2)} mph más ${faster >= 0 ? 'rápida' : 'lenta'}.`}
      </p>

      <section className="fis-why" aria-labelledby="fis-why-title">
        <h2 id="fis-why-title">Menos aire, menos empuje</h2>
        <div className="fis-why-grid">
          <div className="fis-why-text">
            <p>
              La recta sube porque su giro desvía el aire hacia abajo y el aire empuja la bola hacia arriba: el efecto
              Magnus. Esa fuerza depende de cuánto aire hay. En el Harp Helú la densidad es {pct(RHO_HARP)} de la del
              nivel del mar, así que el empuje baja y la bola cae más de lo que el bateador espera. El arrastre baja
              en la misma proporción y la bola conserva más velocidad.
            </p>
            <p>
              Con la física de libro el empuje baja igual que la densidad (elasticidad 1). En la LMB lo medimos dentro
              del mismo lanzamiento entre juegos con distinta densidad, y baja más rápido: la elasticidad de {noun} es
              {' '}<strong>{fmt(fam.elasticity, 2)}</strong> [{fmt(fam.elasticity_lo, 2)}, {fmt(fam.elasticity_hi, 2)}].
              {includesOne ? ' Su intervalo incluye 1, así que para este lanzamiento no se distingue de la física de libro.' : ' El intervalo completo queda arriba de 1.'}
              {' '}Toca una fila para lanzar ese tipo de lanzamiento.
            </p>
            <p className="fis-source">
              Elasticidad y arrastre: contrato physics.json ({doc.sources.join(', ')}). Lanzamiento típico: mediana a
              nivel del mar de {SHAPES_SOURCE}. Vuelo: motor RK4 del navegador, salida y extensión estándar del motor.
            </p>
          </div>
          <ElasticityChart families={doc.families} selected={family} onSelect={setFamily} />
        </div>
      </section>
    </>
  );
}

export default function FisicaPage() {
  const loaded = useLoaded<PhysicsDoc>(loadPhysics, 'fisica');
  return (
    <article className="fis-page">
      <header className="fis-head">
        <h1>Por qué la recta pierde subida en la CDMX</h1>
        <p>Mueve la densidad del aire y mira el mismo lanzamiento a nivel del mar y en el Harp Helú.</p>
        {loaded.state === 'ready' ? <DataBadge source={loaded.source} demo={loaded.doc.demo_data} /> : null}
      </header>
      {loaded.state === 'ready' ? <Explainer doc={loaded.doc} /> : <Status loaded={loaded} />}
    </article>
  );
}
