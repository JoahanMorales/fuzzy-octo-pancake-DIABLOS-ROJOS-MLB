import type { z } from 'zod';
import type { staffSchema } from '../../contract/types';
import { DataBadge, fmt, type Source } from './data';

export type StaffDoc = z.infer<typeof staffSchema>;
type Pitcher = StaffDoc['franchises'][number]['pitchers'][number];

const THROWS: Record<string, string> = { Right: 'Derecho', Left: 'Zurdo' };

/** Pitchers of one franchise ordered by Stuff+ in CDMX air (nulls last). */
export function rankForHome(pitchers: Pitcher[]): Pitcher[] {
  const key = (p: Pitcher) => p.stuff_plus_harp_helu ?? Number.NEGATIVE_INFINITY;
  return [...pitchers].sort((a, b) => key(b) - key(a));
}

function Conclusion({ pitchers }: { pitchers: Pitcher[] }) {
  const ranked = rankForHome(pitchers).filter((p) => p.stuff_plus_harp_helu !== null);
  const deltas = pitchers.map((p) => p.delta_cdmx).filter((v): v is number => v !== null);
  if (!ranked.length || !deltas.length) return null;
  const median = [...deltas].sort((a, b) => a - b)[Math.floor(deltas.length / 2)];
  const top = ranked[0];
  return (
    <p className="h48-conclusion">
      En el aire del Harp Helú el mejor Stuff+ es <strong>{top.pitcher_anon_id}</strong> ({fmt(top.stuff_plus_harp_helu)}).
      La mediana del cambio por la altura en este staff es {fmt(median, 1, true)} puntos.
    </p>
  );
}

function FranchiseTable({ id, pitchers }: { id: string; pitchers: Pitcher[] }) {
  const rows = rankForHome(pitchers);
  return (
    <section className="h48-block" aria-labelledby={`franquicia-${id}`} data-testid={`franquicia-${id}`}>
      <h2 id={`franquicia-${id}`} className="h48-h2">Franquicia {id}</h2>
      <p className="h48-muted">{pitchers.length} pitchers · identificación inferida</p>
      <Conclusion pitchers={pitchers} />
      <div className="h48-scroll" tabIndex={0} role="region" aria-label={`Staff de la franquicia ${id}`}>
        <table className="h48-table">
          <thead>
            <tr>
              <th scope="col">Pitcher</th>
              <th scope="col">Mano</th>
              <th scope="col">Rol</th>
              <th scope="col" className="num">Lanzamientos en casa</th>
              <th scope="col" className="num">Stuff+ neutral</th>
              <th scope="col" className="num is-hh">Stuff+ en CDMX</th>
              <th scope="col" className="num">Cambio CDMX</th>
              <th scope="col" className="num">Location+</th>
              <th scope="col" className="num">Pitching+</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.pitcher_anon_id}>
                <th scope="row">
                  <a href={`#/pitcher/${p.pitcher_anon_id}`}>{p.pitcher_anon_id}</a>
                </th>
                <td>{THROWS[p.throws] ?? p.throws}</td>
                <td>{p.role}</td>
                <td className="num">{p.home_pitches.toLocaleString('es-MX')}</td>
                <td className="num">{fmt(p.stuff_plus)}</td>
                <td className="num is-hh">{fmt(p.stuff_plus_harp_helu)}</td>
                <td className="num">{fmt(p.delta_cdmx, 1, true)}</td>
                <td className="num">{fmt(p.location_plus)}</td>
                <td className="num">{fmt(p.pitching_plus)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/** One table per franchise; 5 and 11 are never pooled (no combined row, no cross-franchise average). */
export function StaffView({ doc, source }: { doc: StaffDoc; source: Source }) {
  return (
    <article className="h48-page">
      <header className="h48-head">
        <h1 className="h48-h1">Staff Diablos</h1>
        <DataBadge source={source} demo={doc.demo_data} />
      </header>
      <p className="h48-lede">
        Stuff+ neutral es el valor a nivel del mar. Stuff+ en CDMX es el mismo lanzamiento en el aire del Harp Helú.
        Las identidades de franquicia son inferidas. {doc.note}
      </p>
      {doc.franchises.map((f) => (
        <FranchiseTable key={f.id} id={f.id} pitchers={f.pitchers} />
      ))}
    </article>
  );
}
