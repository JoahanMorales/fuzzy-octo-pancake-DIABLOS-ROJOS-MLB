import type { PairScore } from './score';
import { whyLines } from './score';
import './panel.css';

export interface PanelProps {
  score: PairScore;
  parkLabel: string;
  rho: number;
  lost: string;
  shapeNote: string | null;
  releaseSource: string;
  modelNote: string;
}

function num(n: number): string {
  return n.toFixed(1);
}

function signed(n: number): string {
  const body = Math.abs(n).toFixed(1);
  return n >= 0 ? `+${body}` : `−${body}`;
}

/** `pitching` is null while Pitching+ has no exported model: the cell says so instead of repeating Stuff+. */
function Column({ label, stuff, location, pitching }: { label: string; stuff: number; location: number; pitching: number | null }) {
  return (
    <div className="sp-col">
      <p className="sp-where">{label}</p>
      <p className="sp-stat">{num(stuff)}</p>
      <p className="sp-sub">Stuff+</p>
      <dl>
        <div><dt>Location+</dt><dd>{num(location)}</dd></div>
        <div><dt>Pitching+</dt><dd data-testid="pitching-cell" className={pitching === null ? 'sp-na' : undefined}>{pitching === null ? 'sin modelo' : num(pitching)}</dd></div>
      </dl>
    </div>
  );
}

const pitchingOf = (side: PairScore['sea']) => (side.pitchingSource === 'stuff-fallback' ? null : side.pitching);

export function Panel({ score, parkLabel, rho, lost, shapeNote, releaseSource, modelNote }: PanelProps) {
  const lines = whyLines(score);
  return (
    <article className="sp" aria-label="Lectura del lanzamiento">
      <header className="sp-head">
        <p className="sp-k">Stuff+</p>
        <p className="sp-badge" data-testid="model-badge">{score.demo ? 'demo' : 'modelo real'}</p>
      </header>
      <div className="sp-grid">
        <Column label="Nivel del mar" stuff={score.sea.stuff} location={score.sea.location} pitching={pitchingOf(score.sea)} />
        <Column label={parkLabel} stuff={score.park.stuff} location={score.park.location} pitching={pitchingOf(score.park)} />
        <div className="sp-col sp-delta">
          <p className="sp-where">ΔStuff+</p>
          <p className="sp-stat" data-testid="stuff-delta">{signed(score.deltaStuff)}</p>
          <p className="sp-sub">parque − mar</p>
        </div>
      </div>
      <p className="sp-lost">{lost}</p>
      <section className="sp-why" aria-label="Por qué cambia">
        <h2>¿Por qué?</h2>
        {shapeNote ? <p className="sp-note">Publicado para la forma: {shapeNote}</p> : null}
        <ul>
          {lines.map((line) => (
            <li key={line.label}><span>{line.label}</span><span>{line.delta}</span></li>
          ))}
        </ul>
      </section>
      <p className="sp-src">
        {modelNote} ρ {rho.toFixed(3)}. {releaseSource}. Pitching+ sin modelo publicado: falta models/pitching.json.
      </p>
    </article>
  );
}
