import { useState } from 'react';
import { number, sourceLink, type Validation } from './data';

export function Calibration({ data }: { data: Validation }) {
  const [selection, setSelection] = useState('');
  const [active, setActive] = useState<number | null>(null);
  const holdouts = data.calibration_bins_holdouts ?? [];
  const bins = [...holdouts, ...(data.calibration_bins ?? []).filter((bin) => !holdouts.some((full) => full.split === bin.split && full.model === bin.model))];
  const choices = [...new Set(bins.map((bin) => `${bin.split} / ${bin.model}`))];
  const picked = choices.includes(selection) ? selection : choices[0];
  const points = bins.filter((bin) => `${bin.split} / ${bin.model}` === picked).sort((a, b) => a.p_mean - b.p_mean);
  const low = Math.min(...points.flatMap((p) => [p.p_mean, p.y_mean]));
  const high = Math.max(...points.flatMap((p) => [p.p_mean, p.y_mean]));
  const span = high - low || 1;
  const x = (value: number) => 90 + (value - low) / span * 280;
  const y = (value: number) => 330 - (value - low) / span * 260;
  const focused = points.find((p) => p.bin === active);
  return <section className="method-section"><h2>Calibración del valor de carrera</h2><p>Predicción agrupada frente al valor observado. Estos bins son de xRV, no probabilidades.</p>
    {!points.length ? <p className="method-empty">Curva no disponible: el archivo no incluye pares predichos y observados por intervalo.</p> : <>
      <label htmlFor="method-calibration">Partición y modelo de la curva</label><select id="method-calibration" value={picked} onChange={(event) => { setSelection(event.target.value); setActive(null); }}>{choices.map((choice) => <option key={choice}>{choice}</option>)}</select>
      <figure className="method-calibration"><svg viewBox="0 0 420 420" role="img" aria-label={`Calibración xRV: ${picked}`}>
        <line x1="90" y1="330" x2="370" y2="70" className="method-reference" />
        <line x1="90" y1="330" x2="370" y2="330" className="method-zero" /><line x1="90" y1="330" x2="90" y2="70" className="method-zero" />
        <polyline points={points.map((p) => `${x(p.p_mean)},${y(p.y_mean)}`).join(' ')} className="method-calibration-line" />
        {points.map((p) => <circle key={p.bin} cx={x(p.p_mean)} cy={y(p.y_mean)} r="5" tabIndex={0} role="img" aria-label={`Predicho ${number(p.p_mean)}, observado ${number(p.y_mean)}, muestra ${number(p.n)}`} onFocus={() => setActive(p.bin)} onMouseEnter={() => setActive(p.bin)}><title>Predicho {number(p.p_mean)} · observado {number(p.y_mean)} · n {number(p.n)}</title></circle>)}
        <text x="90" y="352">{number(low)}</text><text x="370" y="352" textAnchor="end">{number(high)}</text>
        <text x="80" y="330" textAnchor="end">{number(low)}</text><text x="80" y="76" textAnchor="end">{number(high)}</text>
        <text x="215" y="392" textAnchor="middle">Predicho · carreras/pitch</text><text transform="translate(16 205) rotate(-90)" textAnchor="middle">Observado · carreras/pitch</text>
      </svg><figcaption>Línea continua y puntos: xRV agrupado. Gris discontinuo: predicho igual a observado. Alejarse de la diagonal indica descalibración; la curva no es un intervalo de confianza.</figcaption></figure>
      <p className="method-point" aria-live="polite">{focused ? `Predicho ${number(focused.p_mean)} · observado ${number(focused.y_mean)} · muestra ${number(focused.n)}` : 'Enfoca un punto con el teclado o pasa el cursor para consultar sus valores.'}</p>
      <p className="method-source">Fuente: validation_extra.json · {holdouts.some((bin) => `${bin.split} / ${bin.model}` === picked) ? 'calibration_bins_holdouts (corrida completa)' : 'calibration_bins (corrida rápida)'}.</p>
    </>}
    <h3>Métodos de calibración de probabilidades</h3>
    {!data.calibration_methods?.length ? <p className="method-empty">No hay métricas por método en este archivo.</p> : <div className="method-table" role="region" tabIndex={0} aria-label="Métodos de calibración"><table><caption>Menores log-loss y ECE son mejores. Una pendiente de xRV cercana a la identidad reduce la distorsión de escala.</caption><thead><tr><th>Modelo</th><th>Método</th><th>Log-loss</th><th>ECE</th><th>Pendiente xRV</th></tr></thead><tbody>{data.calibration_methods.map((row) => <tr key={`${row.model}-${row.method}`}><th scope="row">{row.label}</th><td>{row.method}</td><td>{number(row.logloss)}</td><td>{number(row.ece)}</td><td>{number(row.xrv_slope)}</td></tr>)}</tbody></table></div>}
    <p className="method-source">Fuente: validation_extra.json · calibration_methods. Cada fila conserva su modelo y método; no se infiere una adopción global.</p>
  </section>;
}

export function LeakAudit({ data }: { data: Validation }) {
  return <section className="method-section"><h2>Auditoría de fugas</h2><p>Compara conjuntos de variables. Una AUC mayor no autoriza a incluir ubicación en Stuff+.</p>
    {!data.leak_audit?.length ? <p className="method-empty">No se publicó una auditoría de fugas en este archivo. Las reglas de adopción no sustituyen esa auditoría.</p> : <div className="method-table" role="region" tabIndex={0} aria-label="Auditoría de variables"><table><caption>Permiso reportado por el exportador; no demuestra ausencia de toda fuga ni resuelve la preparación transductiva.</caption><thead><tr><th>Variables</th><th>AUC whiff</th><th>Intervalo AUC</th><th>Permitidas en Stuff+</th></tr></thead><tbody>{data.leak_audit.map((row) => <tr key={row.set}><th scope="row">{row.label}</th><td>{number(row.whiff_auc)}</td><td>{number(row.whiff_auc_lo)} a {number(row.whiff_auc_hi)}</td><td>{row.stuff_allowed ? 'Sí, según auditoría' : 'No'}</td></tr>)}</tbody></table></div>}
    <p className="method-source">Fuente: validation_extra.json · leak_audit. <a href={sourceLink('reports/leak_audit/README.md')}>Consultar el reporte de auditoría</a>.</p>
  </section>;
}
