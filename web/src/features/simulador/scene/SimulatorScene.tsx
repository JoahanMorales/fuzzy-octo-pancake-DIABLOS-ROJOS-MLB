import { Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react';
import Fallback2D from './Fallback2D';
import {
  LOCAL_BOOK,
  VIEW_LABEL,
  hasWebGL2,
  loadParkBook,
  endLabel,
  pathNote,
  pickEnds,
  placeholderPath,
  readReduced,
  sceneSummary,
  showDevStats,
  sourceLine,
  type Hand,
  type LoadedParks,
  type ParkSide,
  type Vec3,
  type ViewId,
} from './sceneModel';
import './scene.css';

const World = lazy(() => import('./World'));

const VIEWS = Object.keys(VIEW_LABEL) as ViewId[];

export interface SceneFlight {
  harpPath: Vec3[];
  seaPath: Vec3[];
  hand: Hand;
  /** Pitcher's hand: mirrors the pitcher figure and the release side. */
  throws?: Hand;
  /** rpm and degrees (Trackman spin axis): the ball spins with them in the 3D view. */
  spin?: number;
  axis?: number;
  park: ParkSide;
  playId: number;
  parkName: string;
  rho: number;
  lost: string;
}

export function SimulatorScene({ flight }: { flight?: SceneFlight } = {}) {
  const [webgl2, setWebgl2] = useState(hasWebGL2);
  const [reduced, setReduced] = useState(readReduced);
  const [loaded, setLoaded] = useState<LoadedParks>({ book: LOCAL_BOOK, origin: 'local' });
  const [view, setView] = useState<ViewId>('catcher');
  const [hand, setHand] = useState<Hand>('R');
  const [park, setPark] = useState<ParkSide>('harp');
  const [playId, setPlayId] = useState(0);
  const [free, setFree] = useState(false);
  const fpsRef = useRef<HTMLParagraphElement>(null);
  const devStats = showDevStats(import.meta.env.DEV) && webgl2;

  useEffect(() => {
    if (typeof matchMedia !== 'function') return undefined;
    const media = matchMedia('(prefers-reduced-motion: reduce)');
    const onChange = () => setReduced(media.matches);
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, []);

  useEffect(() => {
    let live = true;
    loadParkBook().then((next) => {
      if (!live || (next.origin === 'local' && next.book === LOCAL_BOOK)) return;
      setLoaded(next);
    });
    return () => {
      live = false;
    };
  }, []);

  const ends = useMemo(() => pickEnds(loaded.book), [loaded.book]);
  const placeholderHarp = useMemo(() => placeholderPath(ends.harp.rho, ends.sea.rho), [ends]);
  const placeholderSea = useMemo(() => placeholderPath(ends.sea.rho, ends.sea.rho), [ends]);
  const harpPath = flight?.harpPath ?? placeholderHarp;
  const seaPath = flight?.seaPath ?? placeholderSea;
  const shownHand = flight?.hand ?? hand;
  const shownPark = flight?.park ?? park;
  const shownPlay = flight?.playId ?? playId;
  const active = shownPark === 'harp' ? ends.harp : ends.sea;
  const parkName = flight?.parkName ?? endLabel(active, shownPark);
  const rho = flight?.rho ?? active.rho;
  const placeholderSummary = sceneSummary({
    hand: shownHand,
    park: shownPark,
    parkName,
    rho,
    view,
    demo: flight ? false : loaded.book.demoData,
  });
  const summary = flight
    ? `${placeholderSummary.replace(pathNote(), 'Trayectoria física.')} ${flight.lost}`
    : placeholderSummary;

  const choosePark = (next: ParkSide) => {
    setPark(next);
    setPlayId((n) => n + 1);
  };

  return (
    <section
      className="sim"
      aria-label="Simulador del estadio"
      data-motion={reduced ? 'cut' : 'smooth'}
      data-view={view}
      data-side={shownHand}
      data-park={shownPark}
      data-free={free && !reduced ? 'on' : 'off'}
      data-controlled={flight ? 'on' : 'off'}
    >
      <div className="sim-stage">
        {webgl2 ? (
          <Suspense fallback={<p className="sim-wait">Preparando el estadio.</p>}>
            <World
              view={view}
              hand={shownHand}
              throws={flight?.throws ?? 'R'}
              spin={flight?.spin ?? 2300}
              axis={flight?.axis ?? 210}
              park={shownPark}
              harpPath={harpPath}
              seaPath={seaPath}
              reduced={reduced}
              free={free}
              playId={shownPlay}
              devStats={devStats}
              fpsNode={fpsRef}
              onNoWebGL2={() => setWebgl2(false)}
            />
          </Suspense>
        ) : (
          <div className="sim-fallback">
            <p className="sim-note">Este navegador no tiene WebGL2. La vista del receptor queda en 2D.</p>
            <Fallback2D hand={shownHand} park={shownPark} harpPath={harpPath} seaPath={seaPath} label={summary} />
          </div>
        )}

        <div className="sim-cams" role="group" aria-label="Cámara">
          {VIEWS.map((id) => (
            <button key={id} type="button" aria-pressed={view === id} onClick={() => setView(id)}>
              {VIEW_LABEL[id]}
            </button>
          ))}
          <button type="button" aria-pressed={free} disabled={reduced} onClick={() => setFree((on) => !on)}>
            Libre
          </button>
        </div>

        {devStats ? <p className="sim-fps" data-testid="sim-fps" ref={fpsRef} aria-hidden="true" /> : null}

        <div className="sim-lower">
          <div>
            <p className="sim-k">Parque</p>
            <p className="sim-v">{parkName}</p>
          </div>
          <div>
            <p className="sim-k">Densidad</p>
            <p className="sim-v">
              <span>{rho.toFixed(3)}</span>
              {flight ? <span className="sim-ejemplo">vuelo físico</span> : <span className="sim-ejemplo">trayectoria de ejemplo</span>}
              {!flight && loaded.book.demoData ? <span className="sim-ejemplo">datos de ejemplo</span> : null}
            </p>
          </div>
          <div>
            <p className="sim-k">Bateador</p>
            <p className="sim-v">{shownHand === 'R' ? 'Diestro' : 'Zurdo'}</p>
          </div>
          <div>
            <p className="sim-k">Cámara</p>
            <p className="sim-v">{VIEW_LABEL[view]}</p>
          </div>
          <p className="sim-source">{flight ? `Fuente: flyPitch · physics.json. ${flight.lost}` : sourceLine(loaded.origin, loaded.book.demoData)}</p>
        </div>
      </div>

      {flight ? null : (
      <aside className="sim-rail" aria-label="Controles del estadio">
        <fieldset>
          <legend>Bateador</legend>
          <button type="button" aria-pressed={hand === 'R'} onClick={() => setHand('R')}>Diestro</button>
          <button type="button" aria-pressed={hand === 'L'} onClick={() => setHand('L')}>Zurdo</button>
        </fieldset>
        <fieldset>
          <legend>Parque</legend>
          <button type="button" aria-pressed={park === 'harp'} onClick={() => choosePark('harp')}>{endLabel(ends.harp, 'harp')}</button>
          <button type="button" aria-pressed={park === 'sea'} onClick={() => choosePark('sea')}>Nivel del mar</button>
        </fieldset>
      </aside>
      )}

      <p className="sim-sr" role="status">{summary}</p>
    </section>
  );
}

export default SimulatorScene;
