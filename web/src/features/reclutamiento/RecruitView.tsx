import { useMemo, useRef, useState } from 'react';
import { handLabel, years, type Board } from '../leaderboard/logic';
import { DataBadge, fmt, type Source } from '../staff/data';
import {
  candidates, median, rowKey, shapeOptions, shortlistCsv, SHORTLIST_MAX, toggleShortlist, type RecruitFilters, type Row,
} from './logic';

const SHOWN = 50;

function download(name: string, href: string) {
  const a = document.createElement('a');
  a.href = href;
  a.download = name;
  a.click();
}

export function RecruitView({ board, source, diablos }: { board: Board; source: Source; diablos: Set<string> }) {
  const leagueMedian = useMemo(() => median(board.rows.map((r) => r.delta_cdmx)), [board]);
  const shapes = useMemo(() => shapeOptions(board.rows).slice(0, 12), [board]);
  const [f, setF] = useState<RecruitFilters>({
    year: years(board.rows)[0] ?? 'all', hand: 'all', minPitches: 300, maxLoss: Math.round(-leagueMedian), shapes: [],
  });
  const [list, setList] = useState<string[]>([]);
  const card = useRef<HTMLDivElement>(null);
  const rows = useMemo(() => candidates(board.rows, diablos, f), [board, diablos, f]);
  const byKey = useMemo(() => new Map(board.rows.map((r) => [rowKey(r), r])), [board]);
  const picked = list.map((k) => byKey.get(k)).filter((r): r is Row => !!r);
  const set = (patch: Partial<RecruitFilters>) => setF((old) => ({ ...old, ...patch }));

  const exportCsv = () => {
    const url = URL.createObjectURL(new Blob([shortlistCsv(picked)], { type: 'text/csv' }));
    download('reclutamiento_shortlist.csv', url);
    URL.revokeObjectURL(url);
  };
  const exportPng = async () => {
    if (!card.current) return;
    const { toPng } = await import('html-to-image');
    download('reclutamiento_shortlist.png', await toPng(card.current, { backgroundColor: '#0c0c0e', pixelRatio: 2 }));
  };

  return (
    <article className="h48-page">
      <header className="h48-head">
        <h1 className="h48-h1">Reclutamiento</h1>
        <DataBadge source={source} demo={board.demo_data} />
      </header>
      <p className="h48-lede">
        Pitchers de la liga fuera del staff de los Diablos cuyo arsenal aguanta el aire del Harp Helú: los mejores en
        Stuff+ en CDMX entre los que pierden poco contra el nivel del mar.
      </p>

      <section className="h68-filters" aria-label="Filtros">
        <div className="h48-field">
          <label htmlFor="r-year">Temporada</label>
          <select id="r-year" value={String(f.year)} onChange={(e) => set({ year: e.target.value === 'all' ? 'all' : Number(e.target.value) })}>
            <option value="all">Todas</option>
            {years(board.rows).map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>
        <div className="h48-field">
          <label htmlFor="r-hand">Mano</label>
          <select id="r-hand" value={f.hand} onChange={(e) => set({ hand: e.target.value as RecruitFilters['hand'] })}>
            <option value="all">Ambas</option>
            <option value="Right">Derecho</option>
            <option value="Left">Zurdo</option>
          </select>
        </div>
        <div className="h48-field">
          <label htmlFor="r-min">Mínimo de lanzamientos</label>
          <input id="r-min" type="number" min={0} step={50} value={f.minPitches} onChange={(e) => set({ minPitches: Number(e.target.value) || 0 })} />
        </div>
        <div className="h48-field">
          <label htmlFor="r-loss">Pérdida máxima en CDMX: {f.maxLoss} puntos</label>
          <input id="r-loss" type="range" min={0} max={25} step={1} value={f.maxLoss} onChange={(e) => set({ maxLoss: Number(e.target.value) })} />
          <small>Mediana de la liga: {fmt(leagueMedian, 1, true)} puntos.</small>
        </div>
      </section>
      <div className="h48-chips" role="group" aria-label="Formas en el arsenal">
        {shapes.map((s) => (
          <button key={s} type="button" className="h48-chip" aria-pressed={f.shapes.includes(s)}
            onClick={() => set({ shapes: f.shapes.includes(s) ? f.shapes.filter((x) => x !== s) : [...f.shapes, s] })}>
            {s}
          </button>
        ))}
      </div>

      {rows.length ? (
        <p className="h48-conclusion">
          {rows.length.toLocaleString('es-MX')} pitcher-temporadas cumplen los filtros. El mejor en el aire del Harp Helú es{' '}
          <strong>{rows[0].pitcher_anon_id}</strong> ({rows[0].year}): {fmt(rows[0].stuff_plus_harp_helu)} de Stuff+ en CDMX con{' '}
          {fmt(rows[0].delta_cdmx, 1, true)} contra el nivel del mar.
        </p>
      ) : (
        <p className="h48-muted" role="status">Ningún pitcher cumple estos filtros. Sube la pérdida máxima o quita formas.</p>
      )}

      {rows.length > 0 && (
        <div className="h48-scroll" tabIndex={0} role="region" aria-label="Candidatos">
          <table className="h48-table">
            <thead>
              <tr>
                <th scope="col"><span className="h48-visually-hidden">Lista corta</span></th>
                <th scope="col">Pitcher</th>
                <th scope="col" className="opt">Temporada</th>
                <th scope="col" className="opt">Mano</th>
                <th scope="col" className="num opt">Lanzamientos</th>
                <th scope="col" className="num opt">Stuff+ neutral</th>
                <th scope="col" className="num is-hh">Stuff+ en CDMX</th>
                <th scope="col" className="num">Cambio</th>
                <th scope="col" className="opt">Arsenal</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, SHOWN).map((r) => {
                const key = rowKey(r);
                const on = list.includes(key);
                return (
                  <tr key={key}>
                    <td>
                      <input type="checkbox" checked={on} disabled={!on && list.length >= SHORTLIST_MAX}
                        aria-label={`Agregar ${r.pitcher_anon_id} ${r.year} a la lista corta`}
                        onChange={() => setList((l) => toggleShortlist(l, key))} />
                    </td>
                    <th scope="row"><a href={`#/pitcher/${r.pitcher_anon_id}`}>{r.pitcher_anon_id}</a></th>
                    <td className="opt">{r.year}</td>
                    <td className="opt">{handLabel(r.throws)}</td>
                    <td className="num opt">{r.pitches.toLocaleString('es-MX')}</td>
                    <td className="num opt">{fmt(r.stuff_plus)}</td>
                    <td className="num">{fmt(r.stuff_plus_harp_helu)}</td>
                    <td className="num">{fmt(r.delta_cdmx, 1, true)}</td>
                    <td className="opt">{r.arsenal}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {rows.length > SHOWN && <p className="h48-note">Se muestran los primeros {SHOWN} de {rows.length.toLocaleString('es-MX')}.</p>}
        </div>
      )}

      <section className="h48-block" aria-labelledby="lista-title">
        <h2 id="lista-title" className="h48-h2">Lista corta ({picked.length} de {SHORTLIST_MAX})</h2>
        {picked.length === 0 ? (
          <p className="h48-muted">Marca hasta {SHORTLIST_MAX} pitchers en la tabla para armar la lista y exportarla.</p>
        ) : (
          <>
            <div ref={card} className="h68-card" data-testid="tarjeta">
              <p className="h68-card-title">Lista corta de reclutamiento · Stuff+ 2240</p>
              <ol>
                {picked.map((r) => (
                  <li key={rowKey(r)}>
                    <span>{r.pitcher_anon_id} ({r.year}, {handLabel(r.throws)})</span>
                    <span className="h68-num is-sea">{fmt(r.stuff_plus)}</span>
                    <span className="h68-num is-hh">{fmt(r.stuff_plus_harp_helu)}</span>
                  </li>
                ))}
              </ol>
              <p className="h68-legend"><span className="is-sea">Stuff+ neutral</span> · <span className="is-hh">Stuff+ en CDMX</span> · identificadores anonimizados</p>
            </div>
            <div className="h48-chips">
              <button type="button" className="h48-button" onClick={exportCsv}>Exportar CSV</button>
              <button type="button" className="h48-button is-ghost" onClick={() => void exportPng()}>Exportar tarjeta PNG</button>
              <button type="button" className="h48-button is-ghost" onClick={() => setList([])}>Vaciar lista</button>
            </div>
          </>
        )}
      </section>
    </article>
  );
}
