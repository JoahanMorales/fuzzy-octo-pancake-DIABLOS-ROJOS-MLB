import { useMemo, useState } from 'react';
import type { z } from 'zod';
import type { pitcherSchema } from '../../contract/types';
import { DataBadge, fmt, type Source } from '../staff/data';
import type { StaffDoc } from '../staff/StaffView';
import { losesMost, pitchName, pitchToDevelop, suggestHomeMix, MIX_CAP, type ArsenalPitch, type PlanRow } from './logic';

export type PitcherDoc = z.infer<typeof pitcherSchema>;

const pct = (v: number) => `${Math.round(v * 100)} %`;

export function PitcherReport({ doc, plan }: { doc: PitcherDoc; plan: Record<string, PlanRow[]> | null }) {
  const season = [...doc.seasons].sort((a, b) => b.year - a.year)[0];
  const pitches = season.arsenal_pitches as ArsenalPitch[];
  const worst = losesMost(pitches);
  const mix = suggestHomeMix(pitches);
  const develop = pitchToDevelop(plan, doc.id, season.year);
  return (
    <section className="h67-report" aria-labelledby="reporte-title" data-testid="reporte">
      <header className="h67-report-head">
        <h2 id="reporte-title" className="h48-h2">{doc.id} · temporada {season.year}</h2>
        <p className="h48-muted">{season.pitches.toLocaleString('es-MX')} lanzamientos · identificación inferida</p>
      </header>
      <div className="h48-stats">
        <div className="h48-stat is-sea"><b>{fmt(season.stuff_plus)}</b><span>Stuff+ neutral</span></div>
        <div className="h48-stat is-hh"><b>{fmt(season.stuff_plus_harp_helu)}</b><span>Stuff+ en CDMX</span></div>
        <div className="h48-stat"><b>{fmt(season.delta_cdmx, 1, true)}</b><span>Cambio por el aire del Harp Helú</span></div>
      </div>
      {worst && (
        <p className="h48-conclusion">
          El lanzamiento que más pierde en casa es <strong>{pitchName(worst)}</strong> ({fmt(worst.delta_cdmx, 1, true)} puntos).
        </p>
      )}
      <div className="h48-scroll" tabIndex={0} role="region" aria-label="Arsenal y mezcla sugerida en casa">
        <table className="h48-table">
          <thead>
            <tr>
              <th scope="col">Lanzamiento</th>
              <th scope="col" className="num opt">Velocidad (mph)</th>
              <th scope="col" className="num opt">Stuff+ neutral</th>
              <th scope="col" className="num is-hh">Stuff+ en CDMX</th>
              <th scope="col" className="num">Cambio</th>
              <th scope="col" className="num">Uso actual</th>
              <th scope="col" className="num">Uso sugerido</th>
            </tr>
          </thead>
          <tbody>
            {mix.rows.map(({ pitch: p, current, suggested }) => (
              <tr key={p.pitch_id}>
                <th scope="row">{pitchName(p)}</th>
                <td className="num opt">{fmt(p.velo)}</td>
                <td className="num opt">{fmt(p.stuff_plus)}</td>
                <td className="num">{fmt(p.stuff_plus_harp_helu)}</td>
                <td className="num">{fmt(p.delta_cdmx, 1, true)}</td>
                <td className="num">{pct(current)}</td>
                <td className="num">{suggested === current ? pct(current) : <strong>{pct(suggested)}</strong>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="h48-note">
        {mix.from && mix.to
          ? `Sugerencia del modelo, no un efecto medido: pasar ${pct(mix.moved)} del uso de ${pitchName(mix.from)} a ${pitchName(mix.to)} sube el Stuff+ en CDMX del arsenal ${fmt(mix.arsenalSuggested - mix.arsenalNow, 2, true)} puntos (de ${fmt(mix.arsenalNow, 2)} a ${fmt(mix.arsenalSuggested, 2)}, promedio ponderado por uso).`
          : 'Ningún cambio de mezcla dentro del tope mejora el Stuff+ en CDMX de este arsenal; el modelo no sugiere cambios.'}{' '}
        Tope: {pct(MIX_CAP)} del uso y nunca más de la mitad de un lanzamiento.
      </p>
      <p className="h48-conclusion">
        {develop
          ? <>Lanzamiento a desarrollar (laboratorio): <strong>{develop.label}</strong>, {fmt(develop.gainHH, 2, true)} puntos de Stuff+ en CDMX ({fmt(develop.gainSea, 2, true)} a nivel del mar).</>
          : 'El laboratorio no tiene un ajuste admisible para esta temporada.'}
      </p>
    </section>
  );
}

export function BullpenView({ staff, source, pitcher, plan, onPick, pickedId, loadingPitcher }: {
  staff: StaffDoc;
  source: Source;
  pitcher: PitcherDoc | null;
  plan: Record<string, PlanRow[]> | null;
  onPick: (id: string) => void;
  pickedId: string | null;
  loadingPitcher: boolean;
}) {
  const [franchise, setFranchise] = useState(staff.franchises[0]?.id ?? '');
  const roster = useMemo(
    () => [...(staff.franchises.find((f) => f.id === franchise)?.pitchers ?? [])]
      .sort((a, b) => b.home_pitches - a.home_pitches),
    [staff, franchise],
  );
  return (
    <article className="h48-page h67-page">
      <header className="h48-head h67-noprint">
        <h1 className="h48-h1">Cuerpo técnico</h1>
        <DataBadge source={source} demo={staff.demo_data} />
      </header>
      <p className="h48-lede h67-noprint">
        Reporte de bullpen por pitcher: su arsenal a nivel del mar y en el aire del Harp Helú, qué lanzamiento pierde más
        en casa y una mezcla sugerida. Franquicias por separado, identificación inferida.
      </p>
      <div className="h67-controls h67-noprint">
        <div className="h48-chips" role="group" aria-label="Franquicia">
          {staff.franchises.map((f) => (
            <button key={f.id} type="button" className="h48-chip" aria-pressed={franchise === f.id} onClick={() => setFranchise(f.id)}>
              Franquicia {f.id}
            </button>
          ))}
        </div>
        <div className="h48-field">
          <label htmlFor="pitcher-pick">Pitcher</label>
          <select id="pitcher-pick" value={pickedId ?? ''} onChange={(e) => onPick(e.target.value)}>
            <option value="" disabled>Elige un pitcher</option>
            {roster.map((p) => (
              <option key={p.pitcher_anon_id} value={p.pitcher_anon_id}>
                {p.pitcher_anon_id} · {p.role} · {p.home_pitches.toLocaleString('es-MX')} lanzamientos en el Harp Helú
              </option>
            ))}
          </select>
        </div>
        <button type="button" className="h48-button" disabled={!pitcher} onClick={() => window.print()}>
          Imprimir reporte
        </button>
      </div>
      {!pickedId && <p className="h48-muted h67-noprint">Elige una franquicia y un pitcher para ver su reporte de bullpen.</p>}
      {loadingPitcher && <p className="h48-muted" role="status">Cargando el arsenal…</p>}
      {!loadingPitcher && pickedId && !pitcher && (
        <p className="h48-muted" role="status">Este pitcher no tiene suficientes lanzamientos para una tarjeta de arsenal.</p>
      )}
      {pitcher && <PitcherReport doc={pitcher} plan={plan} />}
    </article>
  );
}
