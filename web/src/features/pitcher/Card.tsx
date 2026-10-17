/* Savant-style pitcher card, exportable as PNG (html-to-image). */
import { useRef, useState } from 'react';
import { DownloadSimple } from '@phosphor-icons/react';
import { fmt } from '../leaderboard/data';
import { handLabel } from '../leaderboard/logic';
import { MovementPlot } from './MovementPlot';
import { familyLabel, movement, type Season } from './logic';

export function PitcherCard({ id, season, demo }: { id: string; season: Season; demo: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const [busy, setBusy] = useState(false);
  const top = [...season.arsenal_pitches].sort((a, b) => b.usage - a.usage).slice(0, 4);

  const download = async () => {
    if (!ref.current) return;
    setBusy(true);
    try {
      const { toPng } = await import('html-to-image');
      const url = await toPng(ref.current, { pixelRatio: 2, backgroundColor: '#0c0c0e' });
      const a = document.createElement('a');
      a.href = url;
      a.download = `stuffplus2240-${id}-${season.year}.png`;
      a.click();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card-wrap">
      <div className="pcard" ref={ref}>
        <header>
          <div>
            <p className="pcard-kicker">Stuff+ 2240 · {season.year}</p>
            <h3>{id}</h3>
            <p className="pcard-meta">{handLabel(season.throws)} · {season.pitches.toLocaleString('es-MX')} lanzamientos</p>
          </div>
          <span className="pcard-pct" title="Percentil de Stuff+ neutral en la LMB">P{Math.round(season.stuff_plus_percentile)}</span>
        </header>
        <dl className="pcard-stats">
          <div><dt>Stuff+ neutral</dt><dd>{fmt(season.stuff_plus)}</dd></div>
          <div className="is-hh"><dt>Stuff+ en CDMX</dt><dd>{fmt(season.stuff_plus_harp_helu)}</dd></div>
          <div><dt>Δ CDMX</dt><dd>{fmt(season.delta_cdmx, 1, true)}</dd></div>
          <div><dt>Pitching+</dt><dd>{fmt(season.pitching_plus)}</dd></div>
        </dl>
        <div className="pcard-body">
          <MovementPlot moves={season.arsenal_pitches.map((p) => movement(p))} compact />
          <table>
            <tbody>
              {top.map((p) => (
                <tr key={p.pitch_id}>
                  <th scope="row">{familyLabel(p.pitch_family)}</th>
                  <td>{Math.round(p.usage * 100)} %</td>
                  <td>{fmt(p.velo)} mph</td>
                  <td>{fmt(p.stuff_plus)}</td>
                  <td className="is-hh">{fmt(p.stuff_plus_harp_helu)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <footer>{demo ? 'Datos de ejemplo' : 'Agregados LMB'} · gris = nivel del mar · rojo = aire del Harp Helú</footer>
      </div>
      <button type="button" className="pcard-dl" onClick={download} disabled={busy}>
        <DownloadSimple size={16} aria-hidden /> {busy ? 'Generando…' : 'Descargar tarjeta (PNG)'}
      </button>
    </div>
  );
}
