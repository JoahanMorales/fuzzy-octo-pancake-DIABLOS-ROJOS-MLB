import { FAMILIES, type Family } from '../../../physics/flight';
import { HARP_RHO, SHAPE_PRESETS, SHORTCUTS, type Release } from '../flight/presets';
import type { Park } from '../scene/sceneModel';

export interface Draft {
  release: Release;
  batter: 'R' | 'L';
  balls: number;
  strikes: number;
  rho: number;
  parkId: string;
  playId: number;
}

export const PARK_HARP = 'harp';
export const PARK_SEA = 'sea';

interface ControlsProps {
  draft: Draft;
  parks: Park[];
  onRelease: (release: Release) => void;
  onPatch: (patch: Partial<Release>) => void;
  onDraft: (patch: Partial<Draft>) => void;
  onThrow: () => void;
}

function Slider({
  label, min, max, step, value, unit, onChange,
}: {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  unit: string;
  onChange: (value: number) => void;
}) {
  const id = `sim-${label.replace(/\s+/g, '-').toLowerCase()}`;
  return (
    <label className="ctl-slider" htmlFor={id}>
      <span>{label}</span>
      <span>{value.toFixed(step < 1 ? 2 : 0)} {unit}</span>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

export function Controls({ draft, parks, onRelease, onPatch, onDraft, onThrow }: ControlsProps) {
  const { release } = draft;
  return (
    <form className="ctl" aria-label="Controles del lanzamiento" onSubmit={(event) => { event.preventDefault(); onThrow(); }}>
      <fieldset>
        <legend>Preset</legend>
        <div className="ctl-pills">
          {SHORTCUTS.map((shortcut) => (
            <button
              key={shortcut.id}
              type="button"
              aria-pressed={release.id === shortcut.release.id}
              onClick={() => onRelease(shortcut.release)}
            >
              {shortcut.label}
            </button>
          ))}
        </div>
      </fieldset>

      <label className="ctl-field">
        Forma
        <select
          value={release.id}
          onChange={(event) => {
            const next = SHAPE_PRESETS.find((row) => row.id === event.target.value);
            if (next) onRelease(next);
          }}
        >
          {release.shape ? null : <option value={release.id}>{release.label}</option>}
          {SHAPE_PRESETS.map((row) => (
            <option key={row.id} value={row.id}>{row.label}</option>
          ))}
        </select>
      </label>

      <label className="ctl-field">
        Familia
        <select
          value={release.family}
          onChange={(event) => {
            const family = event.target.value as Family;
            const next = SHAPE_PRESETS.find((row) => row.family === family);
            if (next) onRelease(next);
            else onPatch({ family });
          }}
        >
          {FAMILIES.map((family) => <option key={family} value={family}>{family}</option>)}
        </select>
      </label>

      <Slider label="Velocidad" min={70} max={102} step={0.5} value={release.velo} unit="mph" onChange={(velo) => onPatch({ velo })} />
      <Slider label="Giro" min={600} max={3200} step={10} value={release.spin} unit="rpm" onChange={(spin) => onPatch({ spin })} />
      <Slider label="Eje" min={0} max={360} step={1} value={release.axis} unit="°" onChange={(axis) => onPatch({ axis })} />
      <Slider label="Altura de salida" min={4} max={7.5} step={0.05} value={release.height} unit="ft" onChange={(height) => onPatch({ height })} />
      <Slider label="Lado de salida" min={0.2} max={4} step={0.05} value={release.side} unit="ft" onChange={(side) => onPatch({ side })} />
      <Slider label="Extensión" min={4} max={8} step={0.05} value={release.extension} unit="ft" onChange={(extension) => onPatch({ extension })} />

      <fieldset>
        <legend>Cuenta</legend>
        <div className="ctl-count">
          <label>Bolas
            <input type="number" min={0} max={3} value={draft.balls} onChange={(event) => onDraft({ balls: Number(event.target.value) })} />
          </label>
          <label>Strikes
            <input type="number" min={0} max={2} value={draft.strikes} onChange={(event) => onDraft({ strikes: Number(event.target.value) })} />
          </label>
        </div>
      </fieldset>

      <fieldset>
        <legend>Lados</legend>
        <div className="ctl-pills">
          <button type="button" aria-pressed={release.throws === 'R'} onClick={() => onPatch({ throws: 'R' })}>Lanzador diestro</button>
          <button type="button" aria-pressed={release.throws === 'L'} onClick={() => onPatch({ throws: 'L' })}>Lanzador zurdo</button>
          <button type="button" aria-pressed={draft.batter === 'R'} onClick={() => onDraft({ batter: 'R' })}>Bateador diestro</button>
          <button type="button" aria-pressed={draft.batter === 'L'} onClick={() => onDraft({ batter: 'L' })}>Bateador zurdo</button>
        </div>
      </fieldset>

      <label className="ctl-field">
        Parque
        <select
          value={draft.parkId}
          onChange={(event) => {
            const id = event.target.value;
            if (id === PARK_HARP) onDraft({ parkId: id, rho: HARP_RHO });
            else if (id === PARK_SEA) onDraft({ parkId: id, rho: 1 });
            else {
              const park = parks.find((row) => row.id === id);
              if (park) onDraft({ parkId: id, rho: park.rho });
            }
          }}
        >
          <option value={PARK_HARP}>Harp Helú</option>
          <option value={PARK_SEA}>Nivel del mar</option>
          {parks.map((park) => (
            <option key={park.id} value={park.id}>
              Parque {park.id} · {park.bucket || park.altitude} · ρ {park.rho.toFixed(3)}
            </option>
          ))}
        </select>
      </label>
      <Slider label="Densidad" min={0.75} max={1.1} step={0.001} value={draft.rho} unit="ρ" onChange={(rho) => onDraft({ rho, parkId: 'custom' })} />

      <button className="ctl-throw" type="submit">Lanzar</button>
    </form>
  );
}
