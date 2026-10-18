import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import parksMock from '../../../public/data/mock/parks.json';
import pitcherMock from '../../../public/data/mock/pitcher/pitcher_00019.json';
import { parseContractFile } from '../../contract/types';
import { movement, parkCurve, RHO_HH, RHO_REF, stuffAt, translate, type Park, type PitcherDoc } from './logic';
import { PitcherView } from './index';

const doc = parseContractFile('pitcher/pitcher_00019.json', pitcherMock) as PitcherDoc;
const parks = (parseContractFile('parks.json', parksMock) as { parks: Park[] }).parks;

describe('pitcher logic', () => {
  it('translator is the identity at the same density and loses ride in thin air', () => {
    expect(translate(17, 1.7, 0.9, 0.9)).toBeCloseTo(17);
    expect(translate(17, 1.7, RHO_REF, RHO_HH)).toBeLessThan(17);
    const fb = doc.seasons[0].arsenal_pitches[0];
    const m = movement(fb);
    expect(Math.abs(m.cdmx.ivb)).toBeLessThanOrEqual(Math.abs(m.sea.ivb) + 1e-9);
  });

  it('Stuff+ by park hits both scored flavours and is ordered by density', () => {
    expect(stuffAt(100, 94, 1)).toBeCloseTo(100);
    expect(stuffAt(100, 94, RHO_HH)).toBeCloseTo(94);
    const curve = parkCurve(doc.seasons[0], parks);
    expect(curve).toHaveLength(20);
    for (let i = 1; i < curve.length; i++) expect(curve[i - 1].park.rho).toBeGreaterThanOrEqual(curve[i].park.rho);
  });
});

describe('pitcher page', () => {
  it('shows both flavours, the arsenal, the movement chart, the parks chart and the card', () => {
    render(<MemoryRouter><PitcherView doc={doc} parks={parks} source="mock" /></MemoryRouter>);
    expect(screen.getByRole('heading', { level: 1, name: doc.id })).toBeInTheDocument();
    expect(screen.getAllByText('Stuff+ en CDMX').length).toBeGreaterThan(0);
    expect(screen.getByRole('img', { name: /Movimiento de/ })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Stuff\+ en los 20 parques/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Descargar tarjeta/ })).toBeInTheDocument();
    const pitchGroup = screen.getAllByLabelText(/pulgadas verticales/)[0];
    fireEvent.focus(pitchGroup);
    expect(screen.getByRole('status')).toHaveTextContent(/Vertical/);
  });
});
