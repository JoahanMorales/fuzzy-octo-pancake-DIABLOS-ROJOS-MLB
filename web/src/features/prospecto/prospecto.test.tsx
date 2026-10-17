import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { CompositeModel } from '../../model/predict';
import stuff from '../../../public/data/models/stuff.json';
import golden from './golden.json';
import { EXAMPLE_CSV, ProspectView } from './ProspectView';

const model = stuff as CompositeModel;

afterEach(() => vi.restoreAllMocks());

describe('prospect page', () => {
  it('scores an uploaded CSV in the browser without any network request', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    const xhrSpy = vi.spyOn(XMLHttpRequest.prototype, 'open');
    const beaconSpy = vi.fn();
    Object.defineProperty(navigator, 'sendBeacon', { value: beaconSpy, configurable: true });
    render(<ProspectView model={model} />);
    const c = golden.cases[0];
    const file = new File([c.csv], 'prospecto.csv', { type: 'text/csv' });
    fireEvent.change(screen.getByLabelText('CSV del arsenal'), { target: { files: [file] } });
    expect(await screen.findByText('Resultado: prospecto.csv')).toBeInTheDocument();
    expect(screen.getByText(c.arsenal_neutral.toFixed(1))).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(xhrSpy).not.toHaveBeenCalled();
    expect(beaconSpy).not.toHaveBeenCalled();
  });

  it('labels the example and both Stuff+ flavours', () => {
    render(<ProspectView model={model} />);
    fireEvent.click(screen.getByRole('button', { name: 'Usar un arsenal de ejemplo' }));
    expect(screen.getByText('Resultado: ejemplo')).toBeInTheDocument();
    expect(screen.getByText('Stuff+ neutral del arsenal')).toBeInTheDocument();
    expect(screen.getByText('Stuff+ en CDMX del arsenal')).toBeInTheDocument();
    expect(EXAMPLE_CSV.split('\n')[0]).toContain('pitch_type');
  });

  it('shows parsing errors inline and waits for the model before enabling upload', async () => {
    const { rerender } = render(<ProspectView model={null} />);
    expect(screen.getByLabelText('CSV del arsenal')).toBeDisabled();
    rerender(<ProspectView model={model} />);
    const bad = new File(['pitch_type,throws\nFour-Seam,Right\n'], 'malo.csv', { type: 'text/csv' });
    fireEvent.change(screen.getByLabelText('CSV del arsenal'), { target: { files: [bad] } });
    expect(await screen.findByRole('alert')).toHaveTextContent(/faltan columnas/);
  });
});
