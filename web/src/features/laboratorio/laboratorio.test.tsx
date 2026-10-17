import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import data from './design_lab.json';
import { FAMILY_ES, familyRows, LabView, type LabDoc } from './LabView';

const doc = data as unknown as LabDoc;

describe('design lab page', () => {
  it('lists every tweak sorted by the CDMX gain, with both airs labelled', () => {
    render(<LabView doc={doc} />);
    const table = screen.getByRole('region', { name: /cada familia/ });
    const labels = [...table.querySelectorAll('tbody th')].map((th) => th.textContent);
    const expected = [...doc.tweaks].sort((a, b) => b.arsenal_gain_hh - a.arsenal_gain_hh).map((t) => t.label);
    expect(labels).toEqual(expected);
    expect(screen.getAllByText(/Ganancia en CDMX/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/nivel del mar/).length).toBeGreaterThan(0);
  });

  it('filters by family with the family CI columns', () => {
    render(<LabView doc={doc} />);
    const fam = doc.by_family[0].family as string;
    fireEvent.click(screen.getByRole('button', { name: FAMILY_ES[fam] }));
    expect(screen.getByRole('region', { name: `Ajustes aplicados a ${FAMILY_ES[fam]}` })).toBeInTheDocument();
    const rows = familyRows(doc, fam);
    expect(rows.every((r) => r.hh_lo <= r.arsenal_gain_hh && r.arsenal_gain_hh <= r.hh_hi)).toBe(true);
  });

  it('shows the top-3 plan of a pitcher-season and says when an id has none', () => {
    render(<LabView doc={doc} />);
    const id = Object.keys(doc.plan).sort()[0];
    expect(screen.getByRole('table', { name: `Plan de ${id}` })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Pitcher y temporada'), { target: { value: 'pitcher_99999_1900' } });
    expect(screen.getByText(/Sin plan para ese identificador/)).toBeInTheDocument();
  });

  it('every number comes from the CSV export and no text uses an em-dash', () => {
    expect(doc.sources.every((s) => s.startsWith('reports/design_lab/'))).toBe(true);
    const { container } = render(<LabView doc={doc} />);
    expect(container.textContent).not.toMatch(/—/);
  });
});
