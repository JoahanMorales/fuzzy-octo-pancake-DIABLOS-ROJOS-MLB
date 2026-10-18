/* Pitcher page (HACK-047): seasons, arsenal, movement in two airs, Stuff+ at the 20 parks and the card. */
import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from '@phosphor-icons/react';
import { DataBadge } from '../leaderboard/DataBadge';
import { fmt, useDoc, type Source } from '../leaderboard/data';
import { handLabel } from '../leaderboard/logic';
import { PitcherCard } from './Card';
import { MovementPlot } from './MovementPlot';
import { ParksChart } from './ParksChart';
import { familyLabel, movement, type Park, type PitcherDoc } from './logic';
import '../leaderboard/leaderboard.css';
import './pitcher.css';

type ParksDoc = { parks: Park[]; demo_data: boolean };

export function PitcherView({ doc, parks, source }: { doc: PitcherDoc; parks: Park[]; source: Source }) {
  const seasons = useMemo(() => [...doc.seasons].sort((a, b) => b.year - a.year), [doc]);
  const [year, setYear] = useState(seasons[0].year);
  useEffect(() => setYear(seasons[0].year), [seasons]);
  const season = seasons.find((s) => s.year === year) ?? seasons[0];
  const arsenal = [...season.arsenal_pitches].sort((a, b) => b.usage - a.usage);
  const moves = arsenal.map((p) => movement(p));
  const worst = arsenal.reduce((w, p) => (p.delta_cdmx < w.delta_cdmx ? p : w), arsenal[0]);

  return (
    <article className="pp" aria-labelledby="pp-title">
      <Link to="/leaderboard" className="pp-back"><ArrowLeft size={14} aria-hidden /> Leaderboard</Link>
      <header className="lb-head">
        <div>
          <h1 id="pp-title">{doc.id}</h1>
          <p className="lb-sub">
            {handLabel(season.throws)} · {season.pitches.toLocaleString('es-MX')} lanzamientos en {season.year} · percentil{' '}
            {Math.round(season.stuff_plus_percentile)} de Stuff+ en la LMB
          </p>
        </div>
        <DataBadge source={source} demo={doc.demo_data} />
      </header>

      {seasons.length > 1 && (
        <div className="lb-seg pp-years" role="group" aria-label="Temporada">
          {seasons.map((s) => (
            <button key={s.year} type="button" aria-pressed={s.year === year} onClick={() => setYear(s.year)}>{s.year}</button>
          ))}
        </div>
      )}

      <dl className="pp-strip">
        <div><dt>Stuff+ neutral</dt><dd>{fmt(season.stuff_plus)}</dd></div>
        <div className="is-hh"><dt>Stuff+ en CDMX</dt><dd>{fmt(season.stuff_plus_harp_helu)}</dd></div>
        <div><dt>Δ CDMX</dt><dd>{fmt(season.delta_cdmx, 1, true)}</dd></div>
        <div><dt>Location+</dt><dd>{fmt(season.location_plus)}</dd></div>
        <div><dt>Pitching+</dt><dd>{fmt(season.pitching_plus)}</dd></div>
      </dl>

      <section className="pp-grid" aria-label="Arsenal">
        <div>
          <h2>Movimiento en dos aires</h2>
          <MovementPlot moves={moves} />
        </div>
        <div>
          <h2>Arsenal</h2>
          <div className="lb-table-wrap">
            <table className="lb-table">
              <thead>
                <tr>
                  <th scope="col">Lanzamiento</th>
                  <th scope="col" className="num">Uso</th>
                  <th scope="col" className="num">Velo</th>
                  <th scope="col" className="num">IVB</th>
                  <th scope="col" className="num">HB</th>
                  <th scope="col" className="num">Giro</th>
                  <th scope="col" className="num">Stuff+</th>
                  <th scope="col" className="num">En CDMX</th>
                  <th scope="col" className="num">Δ</th>
                </tr>
              </thead>
              <tbody>
                {arsenal.map((p) => (
                  <tr key={p.pitch_id}>
                    <td><b>{familyLabel(p.pitch_family)}</b> <span className="pp-shape">{p.shape}</span></td>
                    <td className="num">{Math.round(p.usage * 100)} %</td>
                    <td className="num">{fmt(p.velo)}</td>
                    <td className="num">{fmt(p.ivb)}</td>
                    <td className="num">{fmt(p.hb)}</td>
                    <td className="num">{Math.round(p.spin).toLocaleString('es-MX')}</td>
                    <td className="num">{fmt(p.stuff_plus)}</td>
                    <td className="num">{fmt(p.stuff_plus_harp_helu)}</td>
                    <td className="num">{fmt(p.delta_cdmx, 1, true)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {worst && (
            <p className="pp-note">
              El que más pierde en el aire del Harp Helú es su {familyLabel(worst.pitch_family).toLowerCase()} ({worst.shape}):{' '}
              {fmt(worst.delta_cdmx, 1, true)} puntos de Stuff+.
            </p>
          )}
        </div>
      </section>

      <section className="pp-grid pp-grid-2" aria-label="Parques y tarjeta">
        <div>
          <h2>Stuff+ en los {parks.length} parques</h2>
          <ParksChart season={season} parks={parks} />
        </div>
        <div>
          <h2>Tarjeta</h2>
          <PitcherCard id={doc.id} season={season} demo={doc.demo_data} />
        </div>
      </section>
    </article>
  );
}

export default function PitcherPage() {
  const { id = '' } = useParams();
  const doc = useDoc<PitcherDoc>(id ? `pitcher/${id}.json` : null);
  const parks = useDoc<ParksDoc>('parks.json');
  if (doc.state === 'loading' || parks.state === 'loading') return <div className="page-loading" role="status">Cargando pitcher…</div>;
  if (doc.state === 'error') {
    return (
      <article className="pp">
        <h1 className="pp-missing">{id}</h1>
        <p className="lb-empty" role="alert">
          No hay página para este pitcher en estos datos. Los datos de ejemplo solo traen al staff de los Diablos; con
          los agregados reales cada pitcher del leaderboard tiene la suya.
        </p>
        <Link to="/leaderboard">Volver al leaderboard</Link>
      </article>
    );
  }
  return <PitcherView doc={doc.doc} parks={parks.state === 'ready' ? parks.doc.parks : []} source={doc.source} />;
}
