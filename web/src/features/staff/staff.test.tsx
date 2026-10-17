import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { parseContractFile } from '../../contract/types';
import mock from '../../../public/data/mock/staff.json';
import { dataSource, fmt, resetSourceCache } from './data';
import { rankForHome, StaffView, type StaffDoc } from './StaffView';

const doc = parseContractFile('staff.json', mock) as StaffDoc;

describe('staff page', () => {
  it('renders one table per franchise and never pools 5 and 11', () => {
    render(<StaffView doc={doc} source="mock" />);
    const five = screen.getByTestId('franquicia-5');
    const eleven = screen.getByTestId('franquicia-11');
    expect(within(five).getAllByRole('row')).toHaveLength(doc.franchises[0].pitchers.length + 1);
    expect(within(eleven).getAllByRole('row')).toHaveLength(doc.franchises[1].pitchers.length + 1);
    const ids5 = new Set(doc.franchises[0].pitchers.map((p) => p.pitcher_anon_id));
    within(eleven).getAllByRole('link').forEach((a) => expect(ids5.has(a.textContent ?? '')).toBe(false));
    expect(screen.queryByText(/total|ambas franquicias|combinad/i)).toBeNull();
    expect(screen.getAllByText(/identificación inferida/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('Ejemplo')).toBeInTheDocument();
  });

  it('orders by Stuff+ in CDMX air and labels both flavours', () => {
    const ranked = rankForHome(doc.franchises[0].pitchers);
    expect(ranked[0].stuff_plus_harp_helu).toBe(
      Math.max(...doc.franchises[0].pitchers.map((p) => p.stuff_plus_harp_helu ?? -Infinity)),
    );
    render(<StaffView doc={doc} source="real" />);
    expect(screen.getAllByText('Stuff+ neutral').length).toBe(2);
    expect(screen.getAllByText('Stuff+ en CDMX').length).toBe(2);
  });

  it('formats with a real minus sign and falls back to mock without real/manifest.json', async () => {
    expect(fmt(-5.57, 1)).toBe('−5.6');
    expect(fmt(2, 1, true)).toBe('+2.0');
    expect(fmt(null)).toBe('-');
    resetSourceCache();
    expect(await dataSource(async () => ({ ok: false, json: async () => ({}) }))).toBe('mock');
    resetSourceCache();
    expect(await dataSource(async () => ({ ok: true, json: async () => ({}) }))).toBe('real');
    resetSourceCache();
    // SPA fallback: 200 with index.html is not a manifest
    const html = async () => ({ ok: true, json: async () => JSON.parse('<!doctype html>') });
    expect(await dataSource(html)).toBe('mock');
    resetSourceCache();
  });
});
