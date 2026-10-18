/* Leaderboard (HACK-047): pitcher-seasons with both Stuff+ flavours labelled, sortable and filterable. */
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { CaretDown, CaretUp, MagnifyingGlass } from '@phosphor-icons/react';
import { DataBadge } from './DataBadge';
import { fmt, useDoc } from './data';
import {
  FLAVOUR_KEY,
  filterRows,
  handLabel,
  sortRows,
  summarize,
  years,
  type Board,
  type Filters,
  type Flavour,
  type Hand,
  type SortKey,
} from './logic';
import './leaderboard.css';

const PAGE = 50;
const DELTA_SCALE = 15; // ΔStuff+ points that fill the inline bar

const COLUMNS: { key: SortKey; label: string; title: string }[] = [
  { key: 'pitches', label: 'Lanz.', title: 'Lanzamientos en la temporada' },
  { key: 'stuff_plus', label: 'Stuff+ neutral', title: 'Nivel del mar, 100 = promedio LMB' },
  { key: 'stuff_plus_harp_helu', label: 'Stuff+ en CDMX', title: 'El mismo pitcher con el aire del Harp Helú' },
  { key: 'delta_cdmx', label: 'Δ CDMX', title: 'Stuff+ en CDMX menos Stuff+ neutral' },
  { key: 'location_plus', label: 'Location+', title: 'Ubicación, 100 = promedio' },
  { key: 'pitching_plus', label: 'Pitching+', title: 'Todo junto, 100 = promedio' },
];

function Seg<T extends string>({ label, value, options, onChange }: {
  label: string; value: T; options: [T, string][]; onChange: (v: T) => void;
}) {
  return (
    <div className="lb-seg" role="group" aria-label={label}>
      {options.map(([v, text]) => (
        <button key={v} type="button" aria-pressed={value === v} onClick={() => onChange(v)}>
          {text}
        </button>
      ))}
    </div>
  );
}

export function LeaderboardView({ board, source }: { board: Board; source: 'real' | 'mock' }) {
  const allYears = useMemo(() => years(board.rows), [board]);
  const [flavour, setFlavour] = useState<Flavour>('neutral');
  const [filters, setFilters] = useState<Filters>({ year: allYears[0] ?? 'all', hand: 'all', minPitches: 200, query: '' });
  const [sort, setSort] = useState<{ key: SortKey; dir: 'desc' | 'asc' }>({ key: 'stuff_plus', dir: 'desc' });
  const [shown, setShown] = useState(PAGE);

  const filtered = useMemo(() => filterRows(board.rows, filters), [board, filters]);
  const rows = useMemo(() => sortRows(filtered, sort.key, sort.dir), [filtered, sort]);
  const sum = useMemo(() => summarize(filtered), [filtered]);
  const set = (patch: Partial<Filters>) => {
    setFilters((f) => ({ ...f, ...patch }));
    setShown(PAGE);
  };
  const chooseFlavour = (f: Flavour) => {
    setFlavour(f);
    setSort({ key: FLAVOUR_KEY[f], dir: 'desc' });
  };
  const clickSort = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === 'desc' ? 'asc' : 'desc' } : { key, dir: 'desc' }));

  return (
    <section className="lb" aria-labelledby="lb-title">
      <header className="lb-head">
        <div>
          <h1 id="lb-title">Leaderboard</h1>
          <p className="lb-sub">Stuff+ por pitcher y temporada: a nivel del mar y con el aire del Harp Helú.</p>
        </div>
        <DataBadge source={source} demo={board.demo_data} />
      </header>

      <div className="lb-controls">
        <Seg label="Sabor de Stuff+" value={flavour} onChange={chooseFlavour}
          options={[['neutral', 'Stuff+ neutral'], ['cdmx', 'Stuff+ en CDMX']]} />
        <label className="lb-field">
          <span>Temporada</span>
          <select value={String(filters.year)} onChange={(e) => set({ year: e.target.value === 'all' ? 'all' : Number(e.target.value) })}>
            {allYears.map((y) => <option key={y} value={y}>{y}</option>)}
            <option value="all">Todas</option>
          </select>
        </label>
        <Seg label="Mano" value={filters.hand} onChange={(hand: Hand) => set({ hand })}
          options={[['all', 'Todos'], ['Right', 'Derechos'], ['Left', 'Zurdos']]} />
        <label className="lb-field">
          <span>Mínimo</span>
          <select value={filters.minPitches} onChange={(e) => set({ minPitches: Number(e.target.value) })}>
            {[0, 100, 200, 500, 1000].map((n) => <option key={n} value={n}>{n} lanz.</option>)}
          </select>
        </label>
        <label className="lb-search">
          <MagnifyingGlass size={16} aria-hidden />
          <input type="search" placeholder="Buscar pitcher o arsenal" aria-label="Buscar pitcher o arsenal"
            value={filters.query} onChange={(e) => set({ query: e.target.value })} />
        </label>
      </div>

      <div className="lb-body">
        <div className="lb-table-wrap">
          <table className="lb-table">
            <caption className="sr-only">
              Pitcher-temporadas ordenadas por {COLUMNS.find((c) => c.key === sort.key)?.label}
            </caption>
            <thead>
              <tr>
                <th scope="col" className="num">#</th>
                <th scope="col">Pitcher</th>
                <th scope="col" className="num hide-sm">Año</th>
                <th scope="col" className="hide-sm">Mano</th>
                {COLUMNS.map((c) => (
                  <th key={c.key} scope="col" className={`num ${c.key === FLAVOUR_KEY[flavour] ? 'is-flavour' : ''} ${c.key === 'location_plus' || c.key === 'pitching_plus' ? 'hide-sm' : ''}`}
                    aria-sort={sort.key === c.key ? (sort.dir === 'desc' ? 'descending' : 'ascending') : 'none'}>
                    <button type="button" title={c.title} onClick={() => clickSort(c.key)}>
                      {c.label}
                      {sort.key === c.key && (sort.dir === 'desc' ? <CaretDown size={12} aria-hidden /> : <CaretUp size={12} aria-hidden />)}
                    </button>
                  </th>
                ))}
                <th scope="col" className="hide-sm">Arsenal</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, shown).map((r, i) => {
                const w = Math.min(1, Math.abs(r.delta_cdmx) / DELTA_SCALE) * 50;
                return (
                  <tr key={`${r.pitcher_anon_id}-${r.year}`}>
                    <td className="num rank">{i + 1}</td>
                    <td><Link to={`/pitcher/${r.pitcher_anon_id}`}>{r.pitcher_anon_id}</Link></td>
                    <td className="num hide-sm">{r.year}</td>
                    <td className="hide-sm">{handLabel(r.throws)}</td>
                    <td className="num">{r.pitches.toLocaleString('es-MX')}</td>
                    <td className={`num ${flavour === 'neutral' ? 'is-flavour' : ''}`}>{fmt(r.stuff_plus)}</td>
                    <td className={`num ${flavour === 'cdmx' ? 'is-flavour' : ''}`}>{fmt(r.stuff_plus_harp_helu)}</td>
                    <td className="num delta">
                      <span className="delta-bar" aria-hidden>
                        <span style={r.delta_cdmx < 0 ? { right: '50%', width: `${w}%` } : { left: '50%', width: `${w}%` }} />
                      </span>
                      {fmt(r.delta_cdmx, 1, true)}
                    </td>
                    <td className="num hide-sm">{fmt(r.location_plus)}</td>
                    <td className="num hide-sm">{fmt(r.pitching_plus)}</td>
                    <td className="arsenal hide-sm">{r.arsenal}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {rows.length === 0 && <p className="lb-empty">Ningún pitcher cumple estos filtros. Baja el mínimo de lanzamientos o cambia la temporada.</p>}
          {shown < rows.length && (
            <button type="button" className="lb-more" onClick={() => setShown((n) => n + PAGE)}>
              Mostrar {Math.min(PAGE, rows.length - shown)} más de {rows.length.toLocaleString('es-MX')}
            </button>
          )}
        </div>

        <aside className="lb-aside" aria-label="Conclusión">
          <p className="lb-stat-label">ΔStuff+ medio en el aire del Harp Helú</p>
          <p className="lb-stat">{sum.n ? fmt(sum.meanDelta, 1, true) : '-'}</p>
          {sum.n > 0 && (
            <p>
              En estas {sum.n.toLocaleString('es-MX')} pitcher-temporadas, {Math.round(sum.losingShare * 100)} % pierde Stuff+
              con el aire del Harp Helú (promedio ponderado por lanzamientos).
              {sum.best && <> El que menos sufre: <Link to={`/pitcher/${sum.best.pitcher_anon_id}`}>{sum.best.pitcher_anon_id}</Link>{' '}
                ({sum.best.year}, {fmt(sum.best.delta_cdmx, 1, true)}).</>}
            </p>
          )}
          <dl className="lb-defs">
            <dt>Stuff+ neutral</dt>
            <dd>Calidad física del lanzamiento a nivel del mar; 100 = promedio de la LMB.</dd>
            <dt>Stuff+ en CDMX</dt>
            <dd>El mismo arsenal evaluado con la densidad del aire del Harp Helú.</dd>
          </dl>
        </aside>
      </div>
    </section>
  );
}

export default function LeaderboardPage() {
  const data = useDoc<Board>('leaderboard.json');
  if (data.state === 'loading') return <div className="page-loading" role="status">Cargando leaderboard…</div>;
  if (data.state === 'error') return <p className="lb-empty" role="alert">No se pudo cargar el leaderboard: {data.message}</p>;
  return <LeaderboardView board={data.doc} source={data.source} />;
}
