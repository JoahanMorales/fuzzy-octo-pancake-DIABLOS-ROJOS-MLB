import { useDeferredValue, useEffect, useMemo, useState } from 'react';
import { HARP_RHO, RIDE, type Release } from './flight/presets';
import { lostLabel, plateGap, scenePath, throwPair } from './flight/throw';
import { Controls, PARK_HARP, type Draft } from './panel/Controls';
import { Panel } from './panel/Panel';
import { loadModels, scoreRelease, type Models } from './panel/score';
import SimulatorScene from './scene/SimulatorScene';
import { LOCAL_BOOK, loadParkBook, type Park, type ParkSide } from './scene/sceneModel';
import './simulador.css';

interface ShapeNote { shape: string; physics: string }

function editRelease(release: Release, patch: Partial<Release>): Release {
  let next: Release = { ...release, ...patch };
  if (patch.spin !== undefined && patch.ivb === undefined && release.spin) {
    const scale = patch.spin / release.spin;
    next = { ...next, ivb: release.ivb * scale, hb: release.hb * scale };
  }
  if (patch.axis !== undefined && patch.hb === undefined) {
    const mag = Math.hypot(next.ivb, next.hb);
    const base = Math.atan2(release.hb, release.ivb);
    const ang = base + ((patch.axis - release.axis) * Math.PI) / 180;
    next = { ...next, ivb: mag * Math.cos(ang), hb: mag * Math.sin(ang) };
  }
  const touched = (['velo', 'spin', 'axis', 'height', 'side', 'extension', 'throws', 'family'] as const)
    .some((key) => patch[key] !== undefined);
  if (!touched) return next;
  return { ...next, id: 'custom', shape: null, label: 'Personal', source: 'controles' };
}

function parkLabel(draft: Draft, parks: Park[]): string {
  if (draft.parkId === PARK_HARP) return 'Harp Helú';
  if (draft.parkId === 'sea') return 'Nivel del mar';
  const park = parks.find((row) => row.id === draft.parkId);
  if (!park) return 'Aire elegido';
  return park.name || `Parque ${park.id}`;
}

export function Simulador({ models: given }: { models?: Models } = {}) {
  const [parks, setParks] = useState<Park[]>(LOCAL_BOOK.parks);
  const [models, setModels] = useState<Models | null>(given ?? null);
  const [modelError, setModelError] = useState<string | null>(null);
  const [notes, setNotes] = useState<Map<string, string>>(new Map());
  const [draft, setDraft] = useState<Draft>({
    release: RIDE,
    batter: 'R',
    balls: 0,
    strikes: 0,
    rho: HARP_RHO,
    parkId: PARK_HARP,
    playId: 1,
  });
  const [flightError, setFlightError] = useState<string | null>(null);

  useEffect(() => {
    if (given) return undefined;
    let live = true;
    loadModels()
      .then((next) => { if (live) setModels(next); })
      .catch(() => { if (live) setModelError('No se pudo leer el modelo.'); });
    return () => { live = false; };
  }, [given]);

  useEffect(() => {
    let live = true;
    fetch(`${import.meta.env.BASE_URL}data/mock/shapes.json`)
      .then((res) => (res.ok ? res.json() : null))
      .then((file: { shapes?: ShapeNote[] } | null) => {
        if (!live || !file?.shapes) return;
        setNotes(new Map(file.shapes.map((row) => [row.shape, row.physics])));
      })
      .catch(() => {});
    return () => { live = false; };
  }, []);

  useEffect(() => {
    let live = true;
    loadParkBook().then((loaded) => {
      if (live) setParks(loaded.book.parks);
    });
    return () => { live = false; };
  }, []);

  // Sliders fire many changes per second: the flight and the model score follow a deferred copy, so dragging stays smooth.
  const live = useDeferredValue(draft);
  const thrown = useMemo(() => {
    try {
      const pair = throwPair(live.release, live.rho);
      return { pair, gap: plateGap(pair.sea, pair.park), error: null as string | null };
    } catch (err) {
      return { pair: null, gap: null, error: err instanceof Error ? err.message : 'sin trayectoria' };
    }
  }, [live.release, live.rho]);

  useEffect(() => { setFlightError(thrown.error); }, [thrown.error]);

  const score = useMemo(() => {
    if (!thrown.pair || !models) return null;
    return scoreRelease(live.release, live.rho, models, {
      balls: live.balls,
      strikes: live.strikes,
      batter: live.batter,
      plateSea: { x: thrown.pair.sea.plateX, z: thrown.pair.sea.plateZ },
      platePark: { x: thrown.pair.park.plateX, z: thrown.pair.park.plateZ },
    });
  }, [live.balls, live.batter, live.release, live.rho, live.strikes, models, thrown.pair]);

  const sky: ParkSide = draft.rho < 0.95 ? 'harp' : 'sea';
  const lost = thrown.gap ? lostLabel(thrown.gap) : 'Ese lanzamiento no llega al plato.';
  const label = parkLabel(draft, parks);

  return (
    <div className="sim-app">
      <h1 className="sr-only">Simulador de lanzamientos</h1>
      <SimulatorScene
        flight={thrown.pair ? {
          harpPath: scenePath(thrown.pair.park, live.release.throws),
          seaPath: scenePath(thrown.pair.sea, live.release.throws),
          hand: draft.batter,
          throws: live.release.throws,
          spin: live.release.spin,
          axis: live.release.axis,
          park: sky,
          playId: draft.playId,
          parkName: label,
          rho: draft.rho,
          lost,
        } : undefined}
      />
      <div className="sim-dock">
        {score ? (
          <Panel
            score={score}
            parkLabel={label}
            rho={draft.rho}
            lost={lost}
            shapeNote={draft.release.shape ? notes.get(draft.release.shape) ?? null : null}
            releaseSource={draft.release.source}
            modelNote={score.demo
              ? 'Ejemplo. Fuente: models/stuff.json y models/location.json.'
              : 'Fuente: models/stuff.json y models/location.json, physics_translator.'}
          />
        ) : (
          <p className="sim-error" role="status">{modelError ?? flightError ?? 'Cargando el modelo.'}</p>
        )}
        <Controls
          draft={draft}
          parks={parks}
          onRelease={(release) => setDraft((prev) => ({ ...prev, release, playId: prev.playId + 1 }))}
          onPatch={(patch) => setDraft((prev) => ({
            ...prev,
            release: editRelease(prev.release, patch),
            playId: prev.playId + 1,
          }))}
          onDraft={(patch) => setDraft((prev) => ({ ...prev, ...patch, playId: prev.playId + 1 }))}
          onThrow={() => setDraft((prev) => ({ ...prev, playId: prev.playId + 1 }))}
        />
      </div>
    </div>
  );
}

export default Simulador;
