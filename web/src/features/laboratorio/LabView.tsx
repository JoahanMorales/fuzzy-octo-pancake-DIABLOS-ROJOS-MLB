import { useMemo, useState } from 'react';
import { DataBadge, fmt } from '../staff/data';

export interface TweakRow {
  tweak: string;
  label: string;
  family?: string;
  admissible_share: number;
  arsenal_gain_hh: number;
  hh_lo: number;
  hh_hi: number;
  arsenal_gain_sea: number;
  arsenal_diff: number;
  diff_lo: number;
  diff_hi: number;
  share_above_noise?: number;
}

export interface NewPitchRow {
  new_pitch: string;
  candidates: number;
  admissible_share: number;
  arsenal_gain_hh: number | null;
  hh_lo: number | null;
  hh_hi: number | null;
  arsenal_gain_sea: number | null;
  arsenal_diff: number | null;
  share_positive: number | null;
}

export type PlanRow = [number, string, number, number, number];

export interface LabDoc {
  demo_data: boolean;
  sources: string[];
  meta: { eligible_pitcher_seasons: number; sampled_pitches: number };
  tweaks: TweakRow[];
  by_family: (TweakRow & { arsenal_hh_lo: number; arsenal_hh_hi: number })[];
  new_pitch: NewPitchRow[];
  plan: Record<string, PlanRow[]>;
}

const pct = (v: number | null | undefined) => (v === null || v === undefined ? '-' : `${Math.round(v * 100)} %`);
const ci = (lo: number | null, hi: number | null) => (lo === null || hi === null ? '' : ` [${fmt(lo, 2, true)}, ${fmt(hi, 2, true)}]`);
const NEW_PITCH: Record<string, string> = { splitter: 'Splitter', sinker: 'Sinker', sweeper: 'Sweeper' };

/** by_family rows name the CI columns arsenal_hh_lo/hi; the summary uses hh_lo/hi. */
export function familyRows(doc: LabDoc, family: string): TweakRow[] {
  return doc.by_family
    .filter((r) => r.family === family)
    .map((r) => ({ ...r, hh_lo: r.arsenal_hh_lo, hh_hi: r.arsenal_hh_hi }));
}

function TweakTable({ rows, caption }: { rows: TweakRow[]; caption: string }) {
  const sorted = [...rows].sort((a, b) => b.arsenal_gain_hh - a.arsenal_gain_hh);
  return (
    <div className="h48-scroll" tabIndex={0} role="region" aria-label={caption}>
      <table className="h48-table">
        <caption className="h48-muted" style={{ textAlign: 'left', paddingBottom: 8 }}>{caption}</caption>
        <thead>
          <tr>
            <th scope="col">Ajuste</th>
            <th scope="col" className="num is-hh">Ganancia en CDMX [IC 95 %]</th>
            <th scope="col" className="num is-sea">Ganancia a nivel del mar</th>
            <th scope="col" className="num">CDMX menos mar [IC 95 %]</th>
            <th scope="col" className="num">Aplica a</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={`${r.tweak}-${r.family ?? 'all'}`}>
              <th scope="row">{r.label}</th>
              <td className="num is-hh">{fmt(r.arsenal_gain_hh, 2, true)}{ci(r.hh_lo, r.hh_hi)}</td>
              <td className="num is-sea">{fmt(r.arsenal_gain_sea, 2, true)}</td>
              <td className="num">{fmt(r.arsenal_diff, 2, true)}{ci(r.diff_lo, r.diff_hi)}</td>
              <td className="num">{pct(r.admissible_share)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Plan({ plan }: { plan: LabDoc['plan'] }) {
  const ids = useMemo(() => Object.keys(plan).sort(), [plan]);
  const [query, setQuery] = useState(ids[0] ?? '');
  const rows = plan[query.trim()];
  return (
    <section className="h48-block" aria-labelledby="plan-title">
      <h2 id="plan-title" className="h48-h2">Plan de desarrollo por pitcher</h2>
      <p className="h48-note">Los 3 ajustes que más suben su Stuff+ en CDMX. Solo ajustes que caen dentro de perfiles observados y suben al menos 0.1 puntos.</p>
      <div className="h48-field" style={{ maxWidth: 360 }}>
        <label htmlFor="plan-id">Pitcher y temporada</label>
        <input id="plan-id" list="plan-ids" value={query} onChange={(e) => setQuery(e.target.value)} autoComplete="off" />
        <datalist id="plan-ids">{ids.map((id) => <option key={id} value={id} />)}</datalist>
        <small>{ids.length.toLocaleString('es-MX')} pitcher-temporadas con plan. Identificadores anonimizados.</small>
      </div>
      {rows ? (
        <table className="h48-table" aria-label={`Plan de ${query}`}>
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">Ajuste</th>
              <th scope="col" className="num is-hh">Ganancia en CDMX</th>
              <th scope="col" className="num is-sea">A nivel del mar</th>
              <th scope="col" className="num">CDMX menos mar</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([rank, label, hh, sea, diff]) => (
              <tr key={rank}>
                <td>{rank}</td>
                <th scope="row">{label}</th>
                <td className="num is-hh">{fmt(hh, 2, true)}</td>
                <td className="num is-sea">{fmt(sea, 2, true)}</td>
                <td className="num">{fmt(diff, 2, true)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="h48-muted" role="status">Sin plan para ese identificador. Escribe uno de la lista, por ejemplo {ids[0]}.</p>
      )}
    </section>
  );
}

export function LabView({ doc }: { doc: LabDoc }) {
  const families = useMemo(() => [...new Set(doc.by_family.map((r) => r.family as string))], [doc]);
  const [family, setFamily] = useState<string | null>(null);
  const best = [...doc.tweaks].sort((a, b) => b.arsenal_gain_hh - a.arsenal_gain_hh)[0];
  const cdmx = [...doc.tweaks].sort((a, b) => b.arsenal_diff - a.arsenal_diff)[0];
  return (
    <article className="h48-page">
      <header className="h48-head">
        <h1 className="h48-h1">Laboratorio de diseño</h1>
        <DataBadge source="real" demo={doc.demo_data} />
      </header>
      <p className="h48-lede">
        Cada ajuste se aplica al arsenal de {doc.meta.eligible_pitcher_seasons.toLocaleString('es-MX')} pitcher-temporadas
        y se califica en el aire del Harp Helú y a nivel del mar. La ganancia es el cambio medio de Stuff+ del arsenal.
      </p>
      <section aria-labelledby="ajustes-title">
        <h2 id="ajustes-title" className="h48-h2">Qué ajuste gana más en CDMX</h2>
        <p className="h48-conclusion">
          La mayor ganancia en el Harp Helú es <strong>{best.label}</strong> ({fmt(best.arsenal_gain_hh, 2, true)} puntos).
          El que más vale en CDMX frente al nivel del mar es <strong>{cdmx.label}</strong> ({fmt(cdmx.arsenal_diff, 2, true)}).
        </p>
        <div className="h48-chips" role="group" aria-label="Filtrar por familia">
          <button type="button" className="h48-chip" aria-pressed={family === null} onClick={() => setFamily(null)}>
            Todo el arsenal
          </button>
          {families.map((f) => (
            <button key={f} type="button" className="h48-chip" aria-pressed={family === f} onClick={() => setFamily(f)}>
              {f}
            </button>
          ))}
        </div>
        <TweakTable
          rows={family ? familyRows(doc, family) : doc.tweaks}
          caption={family ? `Ajustes aplicados a ${family}` : 'Ajustes aplicados a cada familia del arsenal'}
        />
      </section>
      <section className="h48-block" aria-labelledby="nuevo-title">
        <h2 id="nuevo-title" className="h48-h2">Agregar un lanzamiento</h2>
        <p className="h48-note">Perfil mediano de pitchers comparables con un uso supuesto del 10 %. Puede restar si el nuevo lanzamiento vale menos que el arsenal.</p>
        <table className="h48-table">
          <thead>
            <tr>
              <th scope="col">Lanzamiento nuevo</th>
              <th scope="col" className="num is-hh">Ganancia en CDMX [IC 95 %]</th>
              <th scope="col" className="num is-sea">A nivel del mar</th>
              <th scope="col" className="num">Aplica a</th>
            </tr>
          </thead>
          <tbody>
            {doc.new_pitch.map((r) => (
              <tr key={r.new_pitch}>
                <th scope="row">{NEW_PITCH[r.new_pitch] ?? r.new_pitch}</th>
                {r.arsenal_gain_hh === null ? (
                  <td className="num" colSpan={2}>Sin perfiles comparables dentro de lo observado</td>
                ) : (
                  <>
                    <td className="num is-hh">{fmt(r.arsenal_gain_hh, 2, true)}{ci(r.hh_lo, r.hh_hi)}</td>
                    <td className="num is-sea">{fmt(r.arsenal_gain_sea, 2, true)}</td>
                  </>
                )}
                <td className="num">{pct(r.admissible_share)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <Plan plan={doc.plan} />
      <p className="h48-note h48-block">
        La ganancia es una diferencia del modelo (Stuff+ sin ubicación ni conteo), no un efecto causal medido. Fuente: reports/design_lab.
      </p>
    </article>
  );
}
