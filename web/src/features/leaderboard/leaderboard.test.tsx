import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import mock from '../../../public/data/mock/leaderboard.json';
import { parseContractFile } from '../../contract/types';
import { dataSource, fmt, loadDoc, resetSourceCache } from './data';
import { filterRows, sortRows, summarize, type Board } from './logic';
import { LeaderboardView } from './index';

const board = parseContractFile('leaderboard.json', mock) as Board;

describe('leaderboard logic', () => {
  it('filters by year, hand, volume and text, and sorts stably', () => {
    const y = board.rows[0].year;
    const f = filterRows(board.rows, { year: y, hand: 'Right', minPitches: 200, query: '' });
    expect(f.every((r) => r.year === y && r.throws === 'Right' && r.pitches >= 200)).toBe(true);
    const s = sortRows(f, 'stuff_plus_harp_helu');
    for (let i = 1; i < s.length; i++) expect(s[i - 1].stuff_plus_harp_helu).toBeGreaterThanOrEqual(s[i].stuff_plus_harp_helu);
    expect(filterRows(board.rows, { year: 'all', hand: 'all', minPitches: 0, query: board.rows[0].pitcher_anon_id }).length).toBeGreaterThan(0);
  });

  it('summarizes the CDMX delta weighted by pitches', () => {
    const rows = [
      { ...board.rows[0], pitches: 100, delta_cdmx: -10 },
      { ...board.rows[0], pitches: 300, delta_cdmx: 2 },
    ];
    const s = summarize(rows);
    expect(s.meanDelta).toBeCloseTo((-1000 + 600) / 400);
    expect(s.losingShare).toBe(0.5);
    expect(s.best?.delta_cdmx).toBe(2);
    expect(summarize([]).n).toBe(0);
  });

  it('formats with a real minus sign', () => {
    expect(fmt(-6.39)).toBe('\u22126.4');
    expect(fmt(2, 1, true)).toBe('+2.0');
  });
});

describe('data source', () => {
  afterEach(() => resetSourceCache());

  it('falls back to mock/ when the host answers the missing manifest with index.html', async () => {
    const html = async () => ({ ok: true, json: async () => { throw new SyntaxError('Unexpected token <'); } });
    expect(await dataSource(html)).toBe('mock');
  });

  it('reads real/ when its manifest exists, else mock/', async () => {
    const urls: string[] = [];
    const fake = (ok: boolean) => async (url: string) => {
      urls.push(url);
      return { ok: url.endsWith('manifest.json') ? ok : true, json: async () => mock };
    };
    expect(await dataSource(fake(false))).toBe('mock');
    resetSourceCache();
    const got = await loadDoc<Board>('leaderboard.json', fake(true));
    expect(got.source).toBe('real');
    expect(urls[urls.length - 1]).toMatch(/data\/real\/leaderboard\.json$/);
  });
});

describe('leaderboard page', () => {
  it('labels both flavours, sorts by the chosen one and links to the pitcher page', () => {
    render(<MemoryRouter><LeaderboardView board={board} source="mock" /></MemoryRouter>);
    expect(screen.getByRole('heading', { name: 'Leaderboard' })).toBeInTheDocument();
    expect(screen.getByText('Ejemplo')).toBeInTheDocument();
    const table = screen.getByRole('table');
    expect(within(table).getByRole('columnheader', { name: /Stuff\+ neutral/ })).toHaveAttribute('aria-sort', 'descending');
    fireEvent.click(within(screen.getByRole('group', { name: 'Sabor de Stuff+' })).getByRole('button', { name: 'Stuff+ en CDMX' }));
    expect(within(table).getByRole('columnheader', { name: /Stuff\+ en CDMX/ })).toHaveAttribute('aria-sort', 'descending');
    expect(within(table).getAllByRole('link')[0].getAttribute('href')).toMatch(/^\/pitcher\//);
    expect(screen.getByText(/ΔStuff\+ medio en el aire del Harp Helú/)).toBeInTheDocument();
  });

  it('shows an empty state when nothing matches', () => {
    render(<MemoryRouter><LeaderboardView board={board} source="mock" /></MemoryRouter>);
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'no-existe-xyz' } });
    expect(screen.getByText(/Ningún pitcher cumple estos filtros/)).toBeInTheDocument();
  });
});
