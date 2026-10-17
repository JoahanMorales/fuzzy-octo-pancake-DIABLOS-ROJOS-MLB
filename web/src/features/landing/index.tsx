import { ArrowRight } from '@phosphor-icons/react';
import { Component, lazy, Suspense, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import type { Flight } from '../../physics/flight';
import { loadLanding, type LandingData } from './load';
import { StaticFlight } from './StaticFlight';
import {
  demoFlights,
  forestScale,
  heroNumbers,
  lowestExtremePark,
  mostContactDamage,
  percentFromFraction,
  shapeExtremes,
  signed,
  staffSnapshot,
} from './story';
import './landing.css';

const HeroFlight = lazy(() => import('./HeroFlight'));

interface LandingProps {
  loader?: () => Promise<LandingData>;
  motion?: 'auto' | 'reduce';
}

function wantsStillness(motion: 'auto' | 'reduce') {
  if (motion === 'reduce') return true;
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true;
}

function hasWebGL() {
  try {
    const canvas = document.createElement('canvas');
    return Boolean(canvas.getContext('webgl2') || canvas.getContext('webgl'));
  } catch {
    return false;
  }
}

class SceneBoundary extends Component<{ children: ReactNode; fallback: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

function FlightView({ sea, cdmx, rhoLabel, still }: { sea: Flight; cdmx: Flight; rhoLabel: string; still: boolean }) {
  const diagram = <StaticFlight sea={sea} cdmx={cdmx} rhoLabel={rhoLabel} />;
  if (still || !hasWebGL()) return diagram;
  return (
    <SceneBoundary fallback={diagram}>
      <Suspense fallback={<p className="landing-note" role="status">Cargando el vuelo…</p>}>
        <HeroFlight sea={sea} cdmx={cdmx} />
      </Suspense>
    </SceneBoundary>
  );
}

export default function Landing({ loader = loadLanding, motion = 'auto' }: LandingProps) {
  const [data, setData] = useState<LandingData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let alive = true;
    setData(null);
    setError(null);
    loader()
      .then((next) => { if (alive) setData(next); })
      .catch((reason: unknown) => {
        if (alive) setError(reason instanceof Error ? reason.message : 'No se pudo leer el informe');
      });
    return () => { alive = false; };
  }, [loader, attempt]);

  if (error) {
    return (
      <section className="landing-state" role="alert">
        <h1>No se pudo abrir el informe</h1>
        <p>{error}</p>
        <button type="button" onClick={() => setAttempt((value) => value + 1)}>Reintentar</button>
      </section>
    );
  }

  if (!data) {
    return <section className="landing-state" role="status">Cargando el informe…</section>;
  }

  return <LandingView data={data} still={wantsStillness(motion)} />;
}

function LandingView({ data, still }: { data: LandingData; still: boolean }) {
  const park = lowestExtremePark(data.parks.parks);
  const flights = useMemo(() => demoFlights(park.rho), [park.rho]);
  let hero: ReturnType<typeof heroNumbers>;
  try {
    hero = heroNumbers(data.validation);
  } catch (reason) {
    const message = reason instanceof Error ? reason.message : 'El informe no trae las cifras del inicio';
    return (
      <section className="landing-state" role="alert">
        <h1>El informe está incompleto</h1>
        <p>{message}</p>
      </section>
    );
  }
  const scale = forestScale(data.shapes.shapes);
  const extremes = shapeExtremes(data.shapes.shapes);
  const contact = mostContactDamage(data.shapes.shapes);
  const staff = staffSnapshot(data.staff);
  const ordered = [...data.shapes.shapes].sort((a, b) => a.delta_stuff - b.delta_stuff);

  return (
    <article className="landing">
      <section className="landing-hero">
        <div className="landing-copy">
          <p className="landing-kicker">Liga Mexicana de Béisbol</p>
          <h1>El aire le quita Stuff+</h1>
          <p>La misma recta llega con menos movimiento en el Harp Helú que a nivel del mar.</p>
          <Link className="landing-cta" to="/simulador">
            Probar el simulador
            <ArrowRight size={18} weight="bold" aria-hidden="true" />
          </Link>
        </div>
        <div className="landing-stage">
          <p className="landing-badge">{hero.demo ? 'ejemplo' : 'informe'}</p>
          <p className="landing-legend landing-scene-legend">
            <span><i className="landing-swatch landing-swatch-sea" /> nivel del mar</span>
            <span><i className="landing-swatch landing-swatch-air" /> aire del Harp Helú</span>
          </p>
          <FlightView sea={flights.sea} cdmx={flights.cdmx} rhoLabel={`ρ ${park.rho.toFixed(3)}`} still={still} />
          <div className="landing-readout">
            <div>
              <strong className="is-air" data-testid="league-delta">{signed(hero.leagueDelta)}</strong>
              <span>Stuff+ de la liga en aire de CDMX. {hero.leagueModel}.</span>
            </div>
            <div>
              <strong className="is-model" data-testid="pitching-skill">{percentFromFraction(hero.pitchingSkill)}</strong>
              <span>Pitching+ contra el nulo, {hero.pitchingSplit.replace('_', ' ')}.</span>
            </div>
            <div>
              <strong className="is-air" data-testid="bias-drop">{percentFromFraction(-hero.biasReduction)}</strong>
              <span>Sesgo en altura no vista, {hero.biasSplit.replace('_', ' ')}.</span>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-section" id="problema">
        <h2>El problema</h2>
        <p className="landing-stat">{signed(hero.leagueDelta)}</p>
        <p className="landing-lead">
          En el aire del Harp Helú la liga pierde Stuff+ frente al nivel del mar. El número es el delta de liga del modelo vigente, no un promedio escrito a mano.
        </p>
        <p className="landing-source">{hero.sources.join(' · ')}</p>
      </section>

      <section className="landing-section" id="evidencia">
        <h2>La evidencia</h2>
        <p className="landing-lead">
          Cada forma pierde movimiento distinto. La línea punteada es el nivel del mar. El punto rojo es el delta en el aire del Harp Helú, con su intervalo.
        </p>
        <ul className="landing-forest">
          {ordered.map((shape) => (
            <li key={shape.shape}>
              <span>{shape.shape}</span>
              <span className="landing-plot" aria-hidden="true">
                <i className="landing-zero" style={{ left: `${scale.zero}%` }} />
                <i
                  className="landing-whisker"
                  style={{
                    left: `${scale.pct(Math.min(shape.delta_lo, shape.delta_hi))}%`,
                    width: `${Math.abs(scale.pct(shape.delta_hi) - scale.pct(shape.delta_lo))}%`,
                  }}
                />
                <i className="landing-dot" style={{ left: `${scale.pct(shape.delta_stuff)}%` }} />
              </span>
              <span>{signed(shape.delta_stuff)}</span>
            </li>
          ))}
        </ul>
        <p className="landing-legend">
          <span><i className="landing-swatch landing-swatch-sea" /> nivel del mar</span>
          <span><i className="landing-swatch landing-swatch-air" /> aire del Harp Helú</span>
        </p>
        <p className="landing-source">{data.shapes.sources.join(' · ')}</p>
      </section>

      <section className="landing-section" id="modelo">
        <h2>El modelo</h2>
        <p className="landing-lead">
          {data.validation.highlights.source_model}. Estas son las reglas de adopción, con el resultado que trae el informe.
        </p>
        <ul className="landing-checks">
          {data.validation.adoption.map((rule) => (
            <li key={`${rule.rule}-${rule.check}`}>
              <strong>{rule.rule}</strong>
              <span className={rule.passed ? 'did-pass' : 'did-fail'}>{rule.passed ? 'pasó' : 'no pasó'}</span>
              <span>{rule.check}. Valor: {rule.value}.</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="landing-section" id="formas">
        <h2>Qué gana y qué pierde</h2>
        <div className="landing-pair">
          <div>
            <h3>{extremes.resists.shape} resiste</h3>
            <p>{extremes.resists.physics}</p>
            <p className="landing-source">Delta {signed(extremes.resists.delta_stuff)}. Veredicto: {extremes.resists.verdict}.</p>
          </div>
          <div>
            <h3>{extremes.loses.shape} pierde</h3>
            <p>{extremes.loses.physics}</p>
            <p className="landing-source">Delta {signed(extremes.loses.delta_stuff)}. Veredicto: {extremes.loses.verdict}.</p>
          </div>
        </div>
      </section>

      <section className="landing-section" id="staff">
        <h2>El staff</h2>
        <p className="landing-lead">
          {data.staff.note} Identificación inferida. En cada franquicia, quien más pierde Stuff+ en CDMX y quien mejor lo sostiene.
        </p>
        {staff.map((franchise) => (
          <div className="landing-franchise" key={franchise.id}>
            <h3>Franquicia {franchise.id}</h3>
            <table className="landing-table">
              <thead>
                <tr>
                  <th>Pitcher</th>
                  <th>Rol</th>
                  <th>Stuff+ neutral</th>
                  <th>Delta CDMX</th>
                </tr>
              </thead>
              <tbody>
                {[franchise.hurt, franchise.holds].filter(Boolean).map((pitcher) => pitcher && (
                  <tr key={pitcher.pitcher_anon_id}>
                    <td>{pitcher.pitcher_anon_id.replace('pitcher_', '')}</td>
                    <td>{pitcher.role}</td>
                    <td>{pitcher.stuff_plus == null ? 'n/d' : signed(pitcher.stuff_plus)}</td>
                    <td>{pitcher.delta_cdmx == null ? 'n/d' : signed(pitcher.delta_cdmx)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
        <p className="landing-source">
          <Link className="landing-textlink" to="/staff">Ver el staff completo</Link>
          {' · '}
          {data.staff.sources.join(' · ')}
        </p>
      </section>

      <section className="landing-section" id="prospectos">
        <h2>Prospectos</h2>
        <p className="landing-lead">
          El perfil de un arsenal se calcula en este navegador. El archivo no sale del dispositivo.
        </p>
        <Link className="landing-textlink" to="/prospecto">Abrir el perfilador</Link>
      </section>

      <section className="landing-section" id="victorias">
        <h2>Valor en victorias</h2>
        <div className="landing-close">
          <div>
            <p className="landing-stat">{signed(contact.delta_contact_runs, 3)}</p>
            <p className="landing-lead">
              Carreras de contacto por batazo en {contact.shape}, la forma donde el aire más encarece el contacto. El informe no convierte ese daño en victorias de temporada: el puente es este delta, y de ahí sale la decisión de roster.
            </p>
            <p className="landing-source">{data.shapes.sources.join(' · ')}</p>
          </div>
          <Link className="landing-cta" to="/simulador">
            Probar el simulador
            <ArrowRight size={18} weight="bold" aria-hidden="true" />
          </Link>
        </div>
        <p className="landing-source">
          <Link className="landing-textlink" to="/metodologia">Ver la metodología</Link>
        </p>
      </section>
    </article>
  );
}
