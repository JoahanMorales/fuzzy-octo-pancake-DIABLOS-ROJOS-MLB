import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { parseContractFile } from '../../contract/types';
import boardMock from '../../../public/data/mock/leaderboard.json';
import staffMock from '../../../public/data/mock/staff.json';
import type { Board } from '../leaderboard/logic';
import type { StaffDoc } from '../staff/StaffView';
import {
  arsenalShapes, candidates, shortlistCsv, SHORTLIST_MAX, toggleShortlist, type RecruitFilters,
} from './logic';
import { RecruitView } from './RecruitView';

const board = parseContractFile('leaderboard.json', boardMock) as Board;
const staff = parseContractFile('staff.json', staffMock) as StaffDoc;
const diablos = new Set(staff.franchises.flatMap((f) => f.pitchers.map((p) => p.pitcher_anon_id)));
const all: RecruitFilters = { year: 'all', hand: 'all', minPitches: 0, maxLoss: 100, shapes: [] };

describe('recruiting logic', () => {
  it('parses arsenal shapes', () => {
    expect(arsenalShapes('riding 4S 53% · 4S 20% · gyro slider 17%')).toEqual(['riding 4S', '4S', 'gyro slider']);
  });

  it('excludes the Diablos staff, ranks by Stuff+ en CDMX and respects the loss and shape filters', () => {
    const rows = candidates(board.rows, diablos, all);
    expect(rows.some((r) => diablos.has(r.pitcher_anon_id))).toBe(false);
    rows.slice(1).forEach((r, i) => expect(rows[i].stuff_plus_harp_helu).toBeGreaterThanOrEqual(r.stuff_plus_harp_helu));
    const tight = candidates(board.rows, diablos, { ...all, maxLoss: 5 });
    expect(tight.every((r) => r.delta_cdmx >= -5)).toBe(true);
    const shape = arsenalShapes(rows[0].arsenal)[0];
    expect(candidates(board.rows, diablos, { ...all, shapes: [shape] }).every((r) => arsenalShapes(r.arsenal).includes(shape))).toBe(true);
  });

  it('caps the shortlist and exports aggregates only', () => {
    let list: string[] = [];
    for (let i = 0; i < SHORTLIST_MAX + 3; i++) list = toggleShortlist(list, `p${i}`);
    expect(list).toHaveLength(SHORTLIST_MAX);
    expect(toggleShortlist(list, 'p0')).toHaveLength(SHORTLIST_MAX - 1);
    const csv = shortlistCsv(board.rows.slice(0, 2));
    expect(csv.split('\n')[0]).toBe('pitcher_anon_id,year,throws,pitches,stuff_plus,stuff_plus_harp_helu,delta_cdmx,location_plus,pitching_plus,arsenal');
    expect(csv.trim().split('\n')).toHaveLength(3);
    expect(csv).not.toMatch(/PitchUID|PlateLoc|RelSpeed/);
  });
});

describe('recruiting page', () => {
  it('shows both flavours, a conclusion, links to /pitcher/:id and builds the shortlist card', () => {
    render(<RecruitView board={board} source="mock" diablos={diablos} />);
    fireEvent.change(screen.getByLabelText('Temporada'), { target: { value: 'all' } });
    fireEvent.change(screen.getByLabelText('Mínimo de lanzamientos'), { target: { value: '0' } });
    expect(screen.getByText('Stuff+ neutral')).toBeInTheDocument();
    expect(screen.getByText('Stuff+ en CDMX')).toBeInTheDocument();
    expect(screen.getByText(/cumplen los filtros/)).toBeInTheDocument();
    const table = screen.getByRole('region', { name: 'Candidatos' });
    const link = within(table).getAllByRole('link')[0];
    expect(link.getAttribute('href')).toMatch(/^#\/pitcher\/pitcher_\d+$/);
    fireEvent.click(within(table).getAllByRole('checkbox')[0]);
    expect(screen.getByTestId('tarjeta')).toHaveTextContent(link.textContent as string);
    expect(screen.getByRole('button', { name: 'Exportar CSV' })).toBeInTheDocument();
  });

  it('has an empty state when nothing passes the filters', () => {
    render(<RecruitView board={board} source="mock" diablos={diablos} />);
    fireEvent.change(screen.getByLabelText('Mínimo de lanzamientos'), { target: { value: '999999' } });
    expect(screen.getByText(/Ningún pitcher cumple estos filtros/)).toBeInTheDocument();
  });
});
