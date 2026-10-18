import { useEffect, useState } from 'react';
import { geoMercator, geoPath, type GeoPermissibleObjects } from 'd3-geo';
import { scaleLinear } from 'd3-scale';
import { parksSchema, shapesSchema } from '../../contract/types';
import mexico from './mexico.json';
import './style.css';

type Parks = ReturnType<typeof parksSchema.parse>;
type Shapes = ReturnType<typeof shapesSchema.parse>;
type Data = { parks: Parks; shapes: Shapes };
const signed = (n: number) => `${n > 0 ? '+' : ''}${n.toFixed(2)}`;
const altitudeLabel = (label: string) => ({ 'Extreme Altitude': 'Altitud extrema', 'Medium Altitude': 'Altitud media', 'No Altitude': 'Sin altitud' })[label] ?? label;
const outline = mexico as GeoPermissibleObjects;
export const projection = geoMercator().fitExtent([[12, 12], [588, 348]], outline);
export const mexicoPath = geoPath(projection)(outline) ?? '';
export const parkRadius = (rho: number) => 13 * Math.sqrt(rho);

export async function loadAltitude(signal?: AbortSignal): Promise<Data> {
  const root = `${import.meta.env.BASE_URL}data/`;
  // HACK-050 contract message #355: real manifest present -> real, otherwise mock.
  const manifest = await fetch(`${root}real/manifest.json`, { signal });
  const isJson = manifest.headers.get('content-type')?.includes('application/json');
  const isHtml = manifest.headers.get('content-type')?.includes('text/html');
  if (!manifest.ok && manifest.status !== 404) throw new Error('No se pudo consultar el catálogo de datos.');
  if (manifest.ok && !isJson && !isHtml) throw new Error('El catálogo tiene un formato inesperado.');
  if (manifest.ok && isJson) await manifest.json();
  // Vite serves index.html for absent JSON paths. This is absence, not a real dataset.
  const source = manifest.ok && isJson ? 'real' : 'mock';
  const read = async (name: string) => {
    const response = await fetch(`${root}${source}/${name}.json`, { signal });
    if (!response.ok) throw new Error(`No se pudo cargar ${name}.`);
    return response.json();
  };
  const [p, s] = await Promise.all([read('parks'), read('shapes')]);
  const parks = parksSchema.parse(p), shapes = shapesSchema.parse(s);
  if (parks.demo_data !== shapes.demo_data || parks.model_version !== shapes.model_version ||
      parks.demo_data !== (source === 'mock')) throw new Error('Las fuentes de datos no son compatibles.');
  if (new Set(parks.parks.map(p => p.id)).size !== parks.parks.length ||
      parks.parks.some(p => !Number.isFinite(p.rho) || p.rho <= 0 || !Number.isFinite(p.air_effect)) ||
      shapes.shapes.some(s => ![s.delta_lo, s.delta_stuff, s.delta_hi, s.stuff_sea_level, s.stuff_harp_helu].every(Number.isFinite) ||
        s.delta_lo > s.delta_stuff || s.delta_stuff > s.delta_hi)) throw new Error('Los agregados contienen valores inválidos.');
  return { parks, shapes };
}

function Charts({ parks, shapes }: Data) {
  const [selected, setSelected] = useState(parks.parks[0].id);
  const [cdmx, setCdmx] = useState(true);
  const [focusedShape, setFocusedShape] = useState(shapes.shapes[0]);
  const park = parks.parks.find(p => p.id === selected)!;
  const rows = [...shapes.shapes].sort((a, b) => b.delta_stuff - a.delta_stuff);
  const min = Math.min(0, ...rows.map(s => s.delta_lo)), max = Math.max(0, ...rows.map(s => s.delta_hi));
  const x = scaleLinear().domain([min - 1, max + 1]).range([145, 550]);
  const height = rows.length * 44 + 70;
  return <>
    <section className="alt-shapes" aria-labelledby="shapes-heading">
      <h2 id="shapes-heading">Qué formas pierden más</h2>
      <p>ΔStuff+ CDMX − nivel del mar. Un valor negativo indica menor Stuff+ en el aire del Harp Helú.</p>
      <div className="alt-toggle" role="group" aria-label="Escenario de Stuff+">
        <button aria-pressed={cdmx} onClick={() => setCdmx(true)}>CDMX</button>
        <button aria-pressed={!cdmx} onClick={() => setCdmx(false)}>Nivel del mar</button>
      </div>
      <div className="alt-forest-wrap">
        <svg className="alt-desktop-forest" viewBox={`0 0 760 ${height}`} role="img" aria-label="ΔStuff+ CDMX menos nivel del mar, con intervalos del contrato">
          <text x="145" y="20">ΔStuff+ · puntos e intervalos</text>
          <text x="565" y="10">Stuff+<tspan x="565" dy="16">{cdmx ? 'en CDMX' : 'nivel del mar'}</tspan></text>
          <text x="670" y="20">Δ</text>
          {x.ticks(5).map(t => <g key={t}><line className="alt-gridline" x1={x(t)} x2={x(t)} y1="30" y2={height - 30} /><text x={x(t)} y={height - 8} textAnchor="middle">{t.toFixed(0)}</text></g>)}
          <line className="alt-zero" x1={x(0)} x2={x(0)} y1="30" y2={height - 30} />
          {rows.map((s, i) => <g key={s.shape} transform={`translate(0 ${48 + i * 44})`} tabIndex={0} onMouseEnter={() => setFocusedShape(s)} onFocus={() => setFocusedShape(s)} aria-describedby="alt-shape-detail" aria-label={`${s.shape}: delta ${signed(s.delta_stuff)}, intervalo ${signed(s.delta_lo)} a ${signed(s.delta_hi)}, Stuff+ ${cdmx ? 'en CDMX' : 'nivel del mar'} ${(cdmx ? s.stuff_harp_helu : s.stuff_sea_level).toFixed(2)}`}>
            <title>{`${s.shape}: ${s.physics} Intervalo: ${signed(s.delta_lo)} a ${signed(s.delta_hi)}.`}</title>
            <text x="0" y="5">{s.shape}</text>
            <line className="alt-ci" x1={x(s.delta_lo)} x2={x(s.delta_hi)} />
            <line className="alt-ci" x1={x(s.delta_lo)} x2={x(s.delta_lo)} y1="-5" y2="5" />
            <line className="alt-ci" x1={x(s.delta_hi)} x2={x(s.delta_hi)} y1="-5" y2="5" />
            <circle className="alt-point" cx={x(s.delta_stuff)} r="5" />
            <text x="580" y="5">{(cdmx ? s.stuff_harp_helu : s.stuff_sea_level).toFixed(2)}</text>
            <text x="670" y="5">{signed(s.delta_stuff)}</text>
          </g>)}
        </svg>
        <div className="alt-mobile-forest">
          {rows.map(s => <button key={s.shape} onClick={() => setFocusedShape(s)} onFocus={() => setFocusedShape(s)} aria-describedby="alt-shape-detail">
            <span><strong>{s.shape}</strong><span>Δ {signed(s.delta_stuff)}</span></span>
            <svg viewBox="0 0 600 24" aria-hidden="true">
              <line className="alt-zero" x1={x(0)} x2={x(0)} y1="0" y2="24" />
              <line className="alt-ci" x1={x(s.delta_lo)} x2={x(s.delta_hi)} y1="12" y2="12" />
              <circle className="alt-point" cx={x(s.delta_stuff)} cy="12" r="6" />
            </svg>
            <span className="alt-note">Stuff+ {cdmx ? 'en CDMX' : 'nivel del mar'}: {(cdmx ? s.stuff_harp_helu : s.stuff_sea_level).toFixed(2)} · intervalo [{signed(s.delta_lo)}, {signed(s.delta_hi)}]</span>
          </button>)}
        </div>
      </div>
      <p id="alt-shape-detail" className="alt-shape-detail" aria-live="polite"><strong>{focusedShape.shape}</strong>: Δ {signed(focusedShape.delta_stuff)}, intervalo [{signed(focusedShape.delta_lo)}, {signed(focusedShape.delta_hi)}]. {focusedShape.physics}</p>
      <p className="alt-note">Rojo: diferencia estimada en aire del Harp Helú. Línea gris discontinua: diferencia cero. Barras: intervalos publicados. El selector cambia la columna Stuff+; la diferencia y sus intervalos se mantienen.</p>
      <p>Mayor descenso estimado: <strong>{rows[rows.length - 1].shape}</strong> ({signed(rows[rows.length - 1].delta_stuff)} puntos). Son estimaciones del modelo; no prueban un efecto causal ni rendimiento futuro.</p>
      <details><summary>Consultar cifras y explicación física</summary><div className="alt-table-wrap"><table>
        <caption>Comparación por forma · puntos Stuff+</caption>
        <thead><tr><th>Forma</th><th>Nivel del mar</th><th>CDMX</th><th>Δ [intervalo]</th><th>Explicación física</th></tr></thead>
        <tbody>{rows.map(s => <tr key={s.shape}><th scope="row">{s.shape}</th><td>{s.stuff_sea_level.toFixed(2)}</td><td>{s.stuff_harp_helu.toFixed(2)}</td><td>{signed(s.delta_stuff)} [{signed(s.delta_lo)}, {signed(s.delta_hi)}]</td><td>{s.physics}</td></tr>)}</tbody>
      </table></div></details>
    </section>
    <section className="alt-parks" aria-labelledby="parks-heading">
      <div>
        <h2 id="parks-heading">El aire de cada parque</h2>
        <p>El área de cada círculo representa la densidad relativa ρ̂. Selecciona un parque para consultar su estimación.</p>
        <svg viewBox="0 0 600 360" role="img" aria-label="Contorno de México, sin ubicaciones de parques verificadas">
          <path d={mexicoPath} className="alt-outline" />
        </svg>
        <p className="alt-note">Cartografía: <a href="https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/">Natural Earth, escala 1:110m</a> (<a href={mexico.properties.terms}>dominio público</a>).</p>
      </div>
      <div className="alt-park-panel">
        <h3>Identidad inferida · ubicación pendiente</h3>
        <p>Los IDs son anónimos. No hay una correspondencia verificada con ciudades; estos círculos no representan posiciones geográficas.</p>
        <div className="alt-park-grid" aria-label="Parques sin ubicación verificada">
          {parks.parks.map(p => <button key={p.id} aria-pressed={selected === p.id} onClick={() => setSelected(p.id)} aria-label={`Parque ${p.id}, densidad ${p.rho.toFixed(3)}`}>
            <svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r={parkRadius(p.rho)} /></svg>
            <span>{p.id}</span>
          </button>)}
        </div>
        <dl className="alt-readout" aria-live="polite">
          <div><dt>Parque {park.id} · inferido</dt><dd>ρ̂ {park.rho.toFixed(3)}</dd></div>
          <div><dt>Categoría de altitud</dt><dd>{altitudeLabel(park.altitude)}</dd></div>
          <div><dt>Efecto del aire · pts Stuff+</dt><dd>{signed(park.air_effect)}</dd></div>
        </dl>
        <p className="alt-note">ρ̂ es relativa al aire de referencia; no es una medición en kg/m³. El efecto por parque describe un agregado, no una comparación causal.</p>
      </div>
    </section>
  </>;
}

export default function AltitudePage() {
  const [data, setData] = useState<Data>();
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setData(undefined); setError(false);
    loadAltitude(controller.signal).then(d => { if (!controller.signal.aborted) setData(d); })
      .catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [attempt]);
  return <article className="alt-page">
    <header><h1>El pitcheo cambia con el aire</h1><p>Compara la densidad de los parques y el cambio estimado de Stuff+ por forma de lanzamiento.</p></header>
    {error ? <div role="alert"><p>No se pudieron cargar los agregados de altitud.</p><button onClick={() => setAttempt(n => n + 1)}>Reintentar</button></div> : !data ? <div className="alt-loading" role="status">Cargando parques y formas…</div> : <>
      <p className="alt-source">{data.parks.demo_data ? 'Datos de ejemplo · demo_data: true' : 'Agregados del modelo · demo_data: false'} · {data.parks.model_version}</p>
      <Charts {...data} />
      <footer className="alt-note">Fuentes de las cifras: {[...new Set([...data.parks.sources, ...data.shapes.sources])].join(' · ')}. Modelo: {data.parks.model}. Traducción: {data.parks.translation}.</footer>
    </>}
  </article>;
}
