import type { Flight } from '../../physics/flight';
import { sideView } from './story';

interface StaticFlightProps {
  sea: Flight;
  cdmx: Flight;
  rhoLabel: string;
}

/** Diagrama del vuelo cuando no hay WebGL o el usuario pide menos movimiento. */
export function StaticFlight({ sea, cdmx, rhoLabel }: StaticFlightProps) {
  const seaPts = sideView(sea);
  const cdmxPts = sideView(cdmx);
  const all = [...seaPts, ...cdmxPts];
  const minDist = Math.min(...all.map((point) => point.dist));
  const maxDist = Math.max(...all.map((point) => point.dist));
  const minHeight = Math.min(...all.map((point) => point.height)) - 0.5;
  const maxHeight = Math.max(...all.map((point) => point.height)) + 0.5;
  const width = 640;
  const height = 360;
  const pad = 28;
  const xOf = (dist: number) => pad + ((maxDist - dist) / (maxDist - minDist || 1)) * (width - pad * 2);
  const yOf = (h: number) => pad + ((maxHeight - h) / (maxHeight - minHeight || 1)) * (height - pad * 2);
  const draw = (points: typeof seaPts) => points
    .map((point, index) => `${index === 0 ? 'M' : 'L'}${xOf(point.dist).toFixed(1)} ${yOf(point.height).toFixed(1)}`)
    .join(' ');
  const seaEnd = seaPts[seaPts.length - 1];
  const cdmxEnd = cdmxPts[cdmxPts.length - 1];
  const lost = sea.ivb - cdmx.ivb;
  const label = `Recta de ejemplo. A nivel del mar el IVB es ${sea.ivb.toFixed(1)} pulgadas. En el parque de menor densidad (${rhoLabel}) es ${cdmx.ivb.toFixed(1)}.`;

  return (
    <figure className="landing-static" data-testid="flight-static">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label}>
        <path d={draw(seaPts)} fill="none" stroke="var(--sea)" strokeWidth="2" strokeDasharray="7 6" />
        <path d={draw(cdmxPts)} fill="none" stroke="var(--red)" strokeWidth="2.5" />
        <circle cx={xOf(seaEnd.dist)} cy={yOf(seaEnd.height)} r="5" fill="var(--sea)" />
        <circle cx={xOf(cdmxEnd.dist)} cy={yOf(cdmxEnd.height)} r="6" fill="var(--red)" />
      </svg>
      <figcaption>
        <span><i className="landing-swatch landing-swatch-sea" /> nivel del mar</span>
        <span><i className="landing-swatch landing-swatch-air" /> aire del Harp Helú</span>
        <span>Esta recta de ejemplo pierde {lost.toFixed(1)} pulgadas de IVB. No es un lanzamiento del archivo.</span>
      </figcaption>
    </figure>
  );
}
