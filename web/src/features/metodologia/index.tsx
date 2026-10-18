import { useEffect, useState } from 'react';
import { loadValidation, metric, number, percent, REPO, sourceLink, SPLITS, type Validation } from './data';
import './style.css';
import { Calibration, LeakAudit } from './evidence';

function MetricTable({ data, split }: { data: Validation; split: string }) {
  const parks = [...new Set([...data.rows, ...(data.rows_fast ?? [])].map((row) => row.split).filter((value) => value.startsWith('leave_one_park_out_')))].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  const [park, setPark] = useState('');
  const selected = split === 'leave_one_park_out' ? (parks.includes(park) ? park : parks[0]) : split;
  const full = data.rows.filter((row) => row.split === selected);
  const rows = full.length ? full : (data.rows_fast ?? []).filter((row) => row.split === selected);
  const models = [...new Set(rows.map((row) => row.model))];
  if (!models.length) return <p className="method-empty">Esta partición aún no está incluida en los resultados publicados.</p>;
  return <div className="method-result">{split === 'leave_one_park_out' && <div><label htmlFor="method-park">Parque inferido · {parks.length} disponibles</label><select id="method-park" value={selected} onChange={(event) => setPark(event.target.value)}>{parks.map((value) => <option key={value} value={value}>{value.replace('leave_one_park_out_', 'Parque ')}</option>)}</select></div>}
    <p className="method-source">{full.length ? 'Evaluación completa' : 'Corrida rápida (validation_extra.json)'} · {selected}</p><div className="method-table" tabIndex={0} role="region" aria-label="Métricas de la partición"><table>
    <caption>Comparación con el nulo por conteo. Menor RMSE es mejor; habilidad positiva significa mejora.</caption>
    <thead><tr><th scope="col">Modelo</th><th scope="col">RMSE · carreras/pitch</th><th scope="col">Mejora del RMSE</th><th scope="col">Intervalo de confianza</th></tr></thead>
    <tbody>{models.map((model) => {
      const rmse = metric(rows, model, 'rmse'), skill = metric(rows, model, 'skill_vs_baseline');
      const lo = metric(rows, model, 'skill_lo'), hi = metric(rows, model, 'skill_hi');
      return <tr key={model}><th scope="row">{model}</th><td>{rmse === undefined ? 'No disponible' : number(rmse)}</td>
        <td>{skill === undefined ? (model === 'baseline' ? 'Referencia' : 'No disponible') : percent(skill)}</td>
        <td>{lo === undefined || hi === undefined ? 'No disponible' : `${percent(lo)} a ${percent(hi)}`}</td></tr>;
    })}</tbody></table></div></div>;
}

function AltitudeBias({ data }: { data: Validation }) {
  const rows = data.rows.filter((row) => row.split === 'park_holdout' && row.metric === 'bias');
  if (!rows.length) return <p className="method-empty">No hay mediciones de sesgo en altitud extrema en este archivo.</p>;
  const max = Math.max(...rows.map((row) => Math.abs(row.value)), Number.EPSILON);
  return <figure className="method-bias"><svg viewBox={`0 0 400 ${rows.length * 58 + 40}`} role="img" aria-label="Sesgo por modelo en altitud extrema, carreras por lanzamiento">
    <line x1="200" x2="200" y1="24" y2={rows.length * 58} className="method-zero" />
    {rows.map((row, i) => <g key={row.model} tabIndex={0} role="img" aria-label={`${row.model}: ${number(row.value)} carreras por lanzamiento`}>
      <title>{row.model}: {number(row.value)} carreras por lanzamiento</title>
      <text x="4" y={i * 58 + 19}>{row.model}</text>
      <line x1="200" x2={200 + row.value / max * 180} y1={i * 58 + 38} y2={i * 58 + 38} className={row.model === 'baseline' ? 'method-reference' : 'method-air'} />
      <circle cx={200 + row.value / max * 180} cy={i * 58 + 38} r="5" className={row.model === 'baseline' ? 'method-dot-reference' : 'method-dot-air'} />
      <text x="396" textAnchor="end" y={i * 58 + 19}>{number(row.value)}</text>
    </g>)}
    <text x="200" y={rows.length * 58 + 28} textAnchor="middle">Cero</text>
  </svg><figcaption>Rojo continuo: modelos en altitud extrema. Gris discontinuo: nulo por conteo. Sesgo = observado menos predicho; valores positivos subestiman el daño. La cercanía a cero reduce ese sesgo, sin probar causalidad.</figcaption></figure>;
}

export function Results({ data }: { data: Validation }) {
  const [split, setSplit] = useState<string>('season_holdout');
  const rowDemo = [...data.rows, ...(data.rows_fast ?? []), ...(data.calibration_bins ?? []), ...(data.calibration_bins_holdouts ?? [])].some((row) => row.demo_data);
  const evidence = [...new Set(data.rows.map((row) => row.evidence))];
  return <>
    <div className="method-status" role="note">{data.demo_data || rowDemo ? 'Datos de ejemplo · no presentar como resultados finales' : 'Resultados publicados · ver alcance y fuentes'}</div>
    <section className="method-lead" aria-labelledby="method-validation"><div><h2 id="method-validation">¿Mejora frente al nulo?</h2>
      <p>Comparamos el error con el promedio de valor de carrera por conteo, ajustado en entrenamiento.</p>
      <label htmlFor="method-split">Partición de evaluación</label><select id="method-split" value={split} onChange={(event) => setSplit(event.target.value)}>
        {SPLITS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select><p className="method-source">Fuente: validation.json · rows; validation_extra.json · rows_fast para las particiones rápidas. Los nombres de modelo se conservan tal como fueron exportados.</p>
    </div><MetricTable data={data} split={split} /></section>
    <aside className="method-limits"><h2>Qué permiten concluir estos datos</h2>
      <p>La preparación de targets, densidad, identidad y arsenal es transductiva. Estas cifras no prueban generalización inductiva completa ni efectos causales.</p>
      <p>Las identidades de parques son inferidas. Las métricas de modelos anteriores no demuestran la adopción del modelo actual.</p>
      <details><summary>Ver alcance declarado por el archivo</summary><ul>{evidence.map((item) => <li key={item}>{item || 'Sin alcance declarado'}</li>)}</ul></details>
    </aside>
    <section className="method-section" aria-labelledby="method-bias"><div className="method-section-title"><h2 id="method-bias">Sesgo en el aire extremo</h2><p>¿Cuánto daño deja de anticipar cada modelo?</p></div><AltitudeBias data={data} /><p className="method-source">Fuente: validation.json · rows, park_holdout / bias. Son métricas de evaluación, no el delta contrafactual de Stuff+.</p></section>
    <Calibration data={data} />
    <LeakAudit data={data} />
    <section className="method-section"><h2>Reglas de adopción del modelo</h2><p>Una regla cumplida no implica que el conjunto esté aprobado.</p>
      <ul className="method-checks">{data.adoption.map((item, i) => <li key={`${item.rule}-${i}`}><span className={item.passed ? 'method-pass' : 'method-pending'}>{item.passed ? 'Cumple' : 'No cumple'}</span><div><strong>{item.check}</strong><p>{item.value || 'Sin valor publicado'}</p></div></li>)}</ul>
      <p className="method-source">Fuente: validation.json · adoption. Estado limitado a las reglas exportadas.</p></section>
    <section className="method-section method-sources"><h2>Seguir la evidencia</h2><p>Fuentes declaradas por los archivos de validación:</p><ul>{data.sources.map((source) => <li key={source}><a href={sourceLink(source)}>{source}</a></li>)}</ul>
      <div className="method-links"><a href={sourceLink('docs/technical/stuffplus2240.pdf')}>Abrir documento técnico PDF</a><a href={REPO}>Explorar repositorio</a><a href={`${import.meta.env.BASE_URL}data/${data.demo_data ? 'mock' : 'real'}/validation.json`}>Consultar JSON de validación</a></div>
    </section>
  </>;
}

export default function Methodology() {
  const [state, setState] = useState<{ data?: Validation; error?: string }>({});
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setState({});
    loadValidation(controller.signal).then((data) => { if (!controller.signal.aborted) setState({ data }); })
      .catch(() => { if (!controller.signal.aborted) setState({ error: 'No pudimos cargar resultados válidos. Revisa la conexión y vuelve a intentar.' }); });
    return () => controller.abort();
  }, [attempt]);
  return <article className="methodology"><header className="method-heading"><p>Metodología</p><h1>Evidencia antes de decidir.</h1><p>Revisa el error, el efecto del aire y los límites de cada comparación.</p></header>
    {state.error ? <div className="method-limits" role="alert"><h2>Resultados no disponibles</h2><p>{state.error}</p><button onClick={() => setAttempt((n) => n + 1)}>Reintentar</button></div>
      : state.data ? <Results data={state.data} /> : <div role="status" className="method-loading" aria-live="polite"><p>Cargando evidencia de validación…</p><div /><div /></div>}
  </article>;
}
