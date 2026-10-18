import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { parseContractFile } from '../../contract/types';
import staffMock from '../../../public/data/mock/staff.json';
import lab from '../laboratorio/design_lab.json';
import type { StaffDoc } from '../staff/StaffView';
import { BullpenView, PitcherReport, type PitcherDoc } from './BullpenView';
import { MIX_CAP, suggestHomeMix, type ArsenalPitch, type PlanRow } from './logic';

const staff = parseContractFile('staff.json', staffMock) as StaffDoc;
const mockPitchers = import.meta.glob('../../../public/data/mock/pitcher/*.json', { eager: true, import: 'default' });
const pitcherDocs = Object.entries(mockPitchers).map(
  ([path, json]) => parseContractFile(`pitcher/${path.split('/').pop()}`, json) as PitcherDoc,
);
const plan = (lab as unknown as { plan: Record<string, PlanRow[]> }).plan;

const p = (id: number, family: string, usage: number, sea: number, hh: number): ArsenalPitch => ({
  pitch_id: id, pitch_family: family, shape: 'x', usage, velo: 90, stuff_plus: sea, stuff_plus_harp_helu: hh, delta_cdmx: hh - sea,
});

describe('suggested home mix', () => {
  it('moves capped usage from the pitch that loses most to the one that resists, and raises the CDMX arsenal', () => {
    const arsenal = [p(1, 'Four-Seam', 0.5, 110, 96), p(2, 'Slider', 0.3, 104, 101), p(3, 'Changeup', 0.2, 100, 92)];
    const mix = suggestHomeMix(arsenal);
    expect(mix.from?.pitch_family).toBe('Four-Seam');
    expect(mix.to?.pitch_family).toBe('Slider');
    expect(mix.moved).toBe(MIX_CAP);
    expect(mix.rows.reduce((t, r) => t + r.suggested, 0)).toBeCloseTo(1, 12);
    expect(mix.arsenalSuggested).toBeGreaterThan(mix.arsenalNow);
    expect(Math.max(...mix.rows.map((r) => Math.abs(r.suggested - r.current)))).toBeLessThanOrEqual(MIX_CAP + 1e-12);
  });

  it('sends usage to the resisting pitch worth most in CDMX air, not just the one that loses least', () => {
    const arsenal = [p(1, 'Sinker', 0.3, 104, 98.6), p(2, 'Sinker', 0.2, 101.5, 92.5), p(3, 'Slider', 0.5, 96, 92.5)];
    const mix = suggestHomeMix(arsenal);
    expect(mix.from?.pitch_id).toBe(2);
    expect(mix.to?.pitch_id).toBe(1);
    expect(mix.arsenalSuggested).toBeGreaterThan(mix.arsenalNow);
  });

  it('keeps the mix when every pitch loses about the same', () => {
    const mix = suggestHomeMix([p(1, 'Sinker', 0.6, 100, 95), p(2, 'Slider', 0.4, 100, 95.5)]);
    expect(mix.moved).toBe(0);
    expect(mix.rows.every((r) => r.suggested === r.current)).toBe(true);
  });
});

describe('cuerpo técnico page', () => {
  it('keeps franchises apart and labels the identification as inferred', () => {
    render(<BullpenView staff={staff} source="mock" pitcher={null} plan={plan} onPick={() => {}} pickedId={null} loadingPitcher={false} />);
    const ids5 = new Set(staff.franchises[0].pitchers.map((x) => x.pitcher_anon_id));
    const options = () => within(screen.getByLabelText('Pitcher')).getAllByRole('option').slice(1).map((o) => o.getAttribute('value'));
    expect(options().every((id) => ids5.has(id as string))).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: `Franquicia ${staff.franchises[1].id}` }));
    expect(options().some((id) => ids5.has(id as string))).toBe(false);
    expect(screen.getByText(/identificación inferida/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Imprimir reporte' })).toBeDisabled();
  });

  it('renders a pitcher report from the contract JSON and prints it', () => {
    const doc = pitcherDocs[0];
    const print = vi.spyOn(window, 'print').mockImplementation(() => {});
    render(<BullpenView staff={staff} source="mock" pitcher={doc} plan={plan} onPick={() => {}} pickedId={doc.id} loadingPitcher={false} />);
    const report = screen.getByTestId('reporte');
    const season = [...doc.seasons].sort((a, b) => b.year - a.year)[0];
    expect(within(report).getAllByRole('row')).toHaveLength(season.arsenal_pitches.length + 1);
    expect(within(report).getByText(/más pierde en casa/)).toBeInTheDocument();
    expect(within(report).getByText(/Sugerencia del modelo, no un efecto medido|no sugiere cambios/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Imprimir reporte' }));
    expect(print).toHaveBeenCalledTimes(1);
  });

  it('names a pitch to develop when the lab has a plan for that pitcher-season', () => {
    const doc = pitcherDocs[0];
    const season = [...doc.seasons].sort((a, b) => b.year - a.year)[0];
    const key = `${doc.id}_${season.year}`;
    const withPlan = { ...plan, [key]: [[1, '+1 mph de velocidad · Sinker', 1.5, 1.2, 0.3] as PlanRow] };
    render(<PitcherReport doc={doc} plan={withPlan} />);
    expect(screen.getByText('+1 mph de velocidad · Sinker')).toBeInTheDocument();
  });
});
