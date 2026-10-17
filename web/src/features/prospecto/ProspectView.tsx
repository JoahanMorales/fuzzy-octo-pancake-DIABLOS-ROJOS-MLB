import { useState } from 'react';
import type { CompositeModel } from '../../model/predict';
import { fmt } from '../staff/data';
import { profileArsenal, ProfileError, type Profile } from './profile';

// Example arsenal (made-up numbers, labelled "ejemplo" in the UI): one row per pitch, Trackman units.
export const EXAMPLE_CSV = `pitch_type,throws,velo,spin_rate,spin_axis,ivb,hb,rel_height,rel_side,extension,usage
Four-Seam,Right,94.1,2380,212,17.2,8.9,5.9,2.1,6.4,0.50
Slider,Right,85.3,2520,95,1.2,-5.8,5.9,2.1,6.3,0.30
Changeup,Right,86.0,1720,240,7.4,13.1,5.9,2.1,6.4,0.20
`;

const FAMILY: Record<string, string> = {
  'Four-Seam': 'Recta de 4 costuras', Sinker: 'Sinker', Cutter: 'Cutter', Slider: 'Slider', Curveball: 'Curva',
  Changeup: 'Cambio', Splitter: 'Splitter',
};

type State = { kind: 'idle' } | { kind: 'error'; message: string } | { kind: 'ready'; profile: Profile; label: string };

/** Local read only (File.text, or FileReader where it is missing). */
function readText(file: File): Promise<string> {
  if (typeof file.text === 'function') return file.text();
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result));
    r.onerror = () => reject(r.error);
    r.readAsText(file);
  });
}

function analyze(text: string, model: CompositeModel, label: string): State {
  try {
    return { kind: 'ready', profile: profileArsenal(text, model), label };
  } catch (e) {
    return { kind: 'error', message: e instanceof ProfileError ? e.message : `no se pudo leer el archivo (${String(e)})` };
  }
}

function Result({ profile, label }: { profile: Profile; label: string }) {
  const delta = profile.arsenalCdmx - profile.arsenalNeutral;
  return (
    <section aria-labelledby="resultado-title" aria-live="polite">
      <h2 id="resultado-title" className="h48-h2">Resultado: {label}</h2>
      <div className="h48-stats">
        <div className="h48-stat is-sea"><b>{fmt(profile.arsenalNeutral)}</b><span>Stuff+ neutral del arsenal</span></div>
        <div className="h48-stat is-hh"><b>{fmt(profile.arsenalCdmx)}</b><span>Stuff+ en CDMX del arsenal</span></div>
        <div className="h48-stat"><b>{fmt(delta, 1, true)}</b><span>Cambio por el aire del Harp Helú</span></div>
      </div>
      <p className="h48-conclusion">
        En el aire del Harp Helú este arsenal {delta < 0 ? 'pierde' : 'gana'} {fmt(Math.abs(delta))} puntos de Stuff+
        contra el nivel del mar. El promedio pondera cada lanzamiento por su uso.
      </p>
      <div className="h48-scroll" tabIndex={0} role="region" aria-label="Stuff+ por lanzamiento">
        <table className="h48-table">
          <thead>
            <tr>
              <th scope="col">Lanzamiento</th>
              <th scope="col" className="num">Uso</th>
              <th scope="col" className="num">Velocidad (mph)</th>
              <th scope="col" className="num">IVB (in)</th>
              <th scope="col" className="num is-sea">Stuff+ neutral</th>
              <th scope="col" className="num is-hh">Stuff+ en CDMX</th>
              <th scope="col" className="num">Cambio</th>
            </tr>
          </thead>
          <tbody>
            {profile.pitches.map((p) => (
              <tr key={p.pitch.pitch_type}>
                <th scope="row">{FAMILY[p.pitch.pitch_type] ?? p.pitch.pitch_type}</th>
                <td className="num">{Math.round(p.usage * 100)} %</td>
                <td className="num">{fmt(p.pitch.velo)}</td>
                <td className="num">{fmt(p.pitch.ivb)}</td>
                <td className="num is-sea">{fmt(p.stuffNeutral)}</td>
                <td className="num is-hh">{fmt(p.stuffCdmx)}</td>
                <td className="num">{fmt(p.stuffCdmx - p.stuffNeutral, 1, true)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/** Upload → parse and score in the browser. `model` comes from data/models/stuff.json; the file never leaves. */
export function ProspectView({ model }: { model: CompositeModel | null }) {
  const [state, setState] = useState<State>({ kind: 'idle' });
  const onFile = async (file: File | undefined) => {
    if (!file || !model) return;
    setState(analyze(await readText(file), model, file.name));
  };
  return (
    <article className="h48-page">
      <header className="h48-head">
        <h1 className="h48-h1">Perfil de prospecto</h1>
      </header>
      <p className="h48-lede">
        Sube el arsenal de un prospecto o agente libre y mira su Stuff+ neutral y su Stuff+ en CDMX. El archivo se lee
        y se califica en tu navegador: no sale de tu dispositivo.
      </p>
      <div className="h48-grid">
        <section className="h48-panel" aria-labelledby="archivo-title">
          <h2 id="archivo-title" className="h48-h2">Archivo</h2>
          <div className="h48-field">
            <label htmlFor="prospect-csv">CSV del arsenal</label>
            <input id="prospect-csv" type="file" accept=".csv,text/csv" disabled={!model}
              onChange={(e) => void onFile(e.target.files?.[0])} />
            <small>
              Una fila por lanzamiento (2 a 5) con pitch_type, throws, velo, spin_rate, spin_axis, ivb, hb y, si quieres,
              rel_height, rel_side, extension, usage y rho_measured. También acepta lanzamientos de Trackman.
            </small>
          </div>
          <button type="button" className="h48-button is-ghost" disabled={!model}
            onClick={() => model && setState(analyze(EXAMPLE_CSV, model, 'ejemplo'))}>
            Usar un arsenal de ejemplo
          </button>
          {!model && <p className="h48-muted" role="status">Cargando el modelo…</p>}
          {state.kind === 'error' && <p className="h48-error" role="alert">{state.message}</p>}
          <p className="h48-note">
            Modelo: Stuff+ por familia de lanzamiento con traslado físico al aire del Harp Helú, el mismo del documento técnico.
          </p>
        </section>
        <div>
          {state.kind === 'ready' ? <Result profile={state.profile} label={state.label} /> : (
            <p className="h48-muted">Aún no hay arsenal. Sube un CSV o usa el ejemplo.</p>
          )}
        </div>
      </div>
    </article>
  );
}
