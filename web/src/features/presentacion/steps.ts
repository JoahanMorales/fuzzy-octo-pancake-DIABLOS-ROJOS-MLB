/* Presentation tour (HACK-071): six steps, each with the page to show, a one-line speaker note (adapted from
   demo/script.md, HACK-025) and the number to say, computed from the contract JSON, never typed. */
import type { z } from 'zod';
import type { leaderboardSchema, parksSchema, staffSchema, validationSchema } from '../../contract/types';
import { fmt } from '../staff/data';

export interface TourDocs {
  validation: z.infer<typeof validationSchema>;
  parks: z.infer<typeof parksSchema>;
  staff: z.infer<typeof staffSchema>;
  leaderboard: z.infer<typeof leaderboardSchema>;
}

export interface Step {
  path: string;
  feature: string;
  title: string;
  note: string;
  number: (d: TourDocs) => { value: string; label: string };
  air?: boolean; // the number is a Harp Helú air value (shown in red)
}

export const TOUR_SECONDS = 5 * 60;

const median = (xs: number[]) => {
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

const skill = (d: TourDocs, split: string) =>
  d.validation.rows.find((r) => r.model === 'Pitching+' && r.metric === 'skill_vs_baseline' && r.split === split)?.value;

export const STEPS: Step[] = [
  {
    path: '/', feature: 'landing', title: 'Inicio',
    note: 'El mismo lanzamiento vale distinto en el aire de la Ciudad de México; medimos cuánto y qué hacer en casa.',
    number: (d) => ({ value: fmt(d.validation.highlights.league_delta_cdmx, 1, true), label: 'cambio de Stuff+ de la liga en el aire del Harp Helú' }),
    air: true,
  },
  {
    path: '/simulador', feature: 'simulador', title: 'Simulador',
    note: 'Mismo lanzamiento, dos aires: la bola fantasma es el nivel del mar y la roja es el Harp Helú.',
    number: (d) => ({ value: fmt(d.validation.highlights.worst_delta, 1, true), label: `cambio de Stuff+ de la forma más castigada (${d.validation.highlights.worst_shape})` }),
    air: true,
  },
  {
    path: '/altitud', feature: 'altitud', title: 'Altitud',
    note: 'La pérdida depende de la forma del lanzamiento, no solo de la altura del parque.',
    number: (d) => {
      const ext = d.parks.parks.filter((p) => p.bucket === 'Extreme Altitude').map((p) => p.rho);
      return { value: fmt(Math.min(...ext), 3), label: 'densidad del aire relativa al nivel del mar en el parque de altitud extrema más ligero' };
    },
  },
  {
    path: '/staff', feature: 'staff', title: 'Staff Diablos',
    note: 'Las franquicias 5 y 11 son alternativas con identificación inferida; nunca se suman.',
    number: (d) => ({
      value: d.staff.franchises.map((f) => fmt(median(f.pitchers.map((p) => p.delta_cdmx).filter((v): v is number => v !== null)), 1, true)).join(' / '),
      label: `mediana del cambio en CDMX por franquicia (${d.staff.franchises.map((f) => f.id).join(' / ')})`,
    }),
  },
  {
    path: '/reclutamiento', feature: 'reclutamiento', title: 'Reclutamiento',
    note: 'Buscamos brazos de la liga cuyo arsenal pierde poco en el aire de casa.',
    number: (d) => {
      const diablos = new Set(d.staff.franchises.flatMap((f) => f.pitchers.map((p) => p.pitcher_anon_id)));
      const rows = d.leaderboard.rows;
      const cut = median(rows.map((r) => r.delta_cdmx));
      const n = rows.filter((r) => !diablos.has(r.pitcher_anon_id) && r.delta_cdmx >= cut).length;
      return { value: n.toLocaleString('es-MX'), label: 'pitcher-temporadas fuera del staff que pierden menos que la mediana de la liga' };
    },
  },
  {
    path: '/metodologia', feature: 'metodologia', title: 'Metodología',
    note: 'Pitching+ mejora al modelo nulo por conteo fuera de muestra; la preparación es transductiva.',
    number: (d) => {
      const s = skill(d, 'season_holdout');
      return { value: s === undefined ? '-' : `${fmt(s * 100, 2, true)} %`, label: 'mejora de Pitching+ en RMSE contra el promedio por conteo (temporada fuera de muestra)' };
    },
  },
];

export function formatClock(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}
