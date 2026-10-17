import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { vi } from 'vitest';
import sample from '../../../public/data/mock/validation.json';
import Methodology, { Results } from './index';
import { loadValidation, methodologySchema, type Validation } from './data';

const data = sample as Validation;
const response = (body: unknown, status = 200, type = 'application/json') => ({ ok: status === 200, status, headers: new Headers({ 'content-type': type }), json: async () => body });
afterEach(() => vi.unstubAllGlobals());

describe('metodología: evidencia y límites', () => {
  it('labels examples, preserves model names, and exposes actual scalar metrics', () => {
    render(<Results data={data} />);
    expect(screen.getByRole('note')).toHaveTextContent('Datos de ejemplo');
    expect(screen.getByText(/preparación de targets/)).toHaveTextContent('transductiva');
    const table = screen.getByRole('table');
    expect(within(table).getByText('Pitching+')).toBeInTheDocument();
    expect(within(table).getByText('3.74 %')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Abrir documento técnico PDF' })).toHaveAttribute('href', expect.stringContaining('/blob/main/docs/technical/stuffplus2240.pdf'));
  });
  it('shows unavailable partitions instead of borrowing metrics from another split', () => {
    render(<Results data={data} />);
    fireEvent.change(screen.getByLabelText('Partición de evaluación'), { target: { value: 'pitcher_kfold' } });
    expect(screen.getByText(/Esta partición aún no/)).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Partición de evaluación'), { target: { value: 'park_holdout' } });
    expect(within(screen.getByRole('table')).getByText('3.28 %')).toBeInTheDocument();
  });
  it('does not turn missing calibration/audit or failed adoption rules into success', () => {
    render(<Results data={data} />);
    expect(screen.getByText(/Curva no disponible/)).toBeInTheDocument();
    expect(screen.getByText(/No se publicó una auditoría/)).toBeInTheDocument();
    expect(screen.getAllByText('No cumple')).toHaveLength(data.adoption.filter((row) => !row.passed).length);
    expect(screen.getByRole('img', { name: /baseline: 0.01088 carreras/ })).toBeInTheDocument();
  });
  it('renders optional fast partitions, calibration bins and audit without conflating metrics', () => {
    const rich = methodologySchema.parse({ ...data,
      rows_fast: [{ split: 'pitcher_kfold', model: 'Synthetic model', metric: 'rmse', value: .123, demo_data: true, evidence: 'synthetic' }, ...Array.from({ length: 20 }, (_, i) => ({ split: `leave_one_park_out_${i + 1}`, model: 'Synthetic model', metric: 'rmse', value: .123, demo_data: true, evidence: 'synthetic' }))],
      calibration_bins: [{ bin: 0, p_mean: -.02, y_mean: -.01, n: 10, model: 'Synthetic model', split: 'pitcher_kfold', demo_data: true }],
      calibration_methods: [{ model: 'synthetic', label: 'Synthetic model', method: 'none', logloss: .7, ece: .1, xrv_slope: .9 }],
      leak_audit: [{ set: 'location', label: 'Ubicación sintética', whiff_auc: .8, whiff_auc_lo: .7, whiff_auc_hi: .9, stuff_allowed: false }],
    });
    render(<Results data={rich} />);
    fireEvent.change(screen.getByLabelText('Partición de evaluación'), { target: { value: 'pitcher_kfold' } });
    expect(screen.getByRole('region', { name: 'Métricas de la partición' })).toHaveTextContent('0.123');
    fireEvent.change(screen.getByLabelText('Partición de evaluación'), { target: { value: 'leave_one_park_out' } });
    expect(screen.getByLabelText('Parque inferido · 20 disponibles').children).toHaveLength(20);
    fireEvent.change(screen.getByLabelText('Parque inferido · 20 disponibles'), { target: { value: 'leave_one_park_out_20' } });
    expect(screen.getByText(/Corrida rápida · leave_one_park_out_20/)).toBeInTheDocument();
    const point = screen.getByRole('img', { name: /Predicho -0.02, observado -0.01, muestra 10/ });
    fireEvent.focus(point);
    expect(screen.getByText('Predicho -0.02 · observado -0.01 · muestra 10')).toBeInTheDocument();
    expect(screen.getByText(/Estos bins son de xRV, no probabilidades/)).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Métodos de calibración' })).toHaveTextContent('0.7');
    expect(screen.getByRole('region', { name: 'Auditoría de variables' })).toHaveTextContent('No');
  });
  it('finds individual parks published only in full rows', () => {
    const fullOnly = { ...data, rows: [...data.rows, { split: 'leave_one_park_out_7', model: 'Synthetic full model', metric: 'rmse', value: .456, demo_data: true, evidence: 'synthetic' }] };
    render(<Results data={fullOnly} />);
    fireEvent.change(screen.getByLabelText('Partición de evaluación'), { target: { value: 'leave_one_park_out' } });
    expect(screen.getByLabelText('Parque inferido · 1 disponibles')).toHaveValue('leave_one_park_out_7');
    expect(screen.getByRole('region', { name: 'Métricas de la partición' })).toHaveTextContent('0.456');
    expect(screen.getByText(/Evaluación completa · leave_one_park_out_7/)).toBeInTheDocument();
  });
  it('keeps example row provenance visible even inside a real envelope', () => {
    const mixed = structuredClone(data); mixed.demo_data = false; mixed.rows[0].demo_data = true;
    render(<Results data={mixed} />);
    expect(screen.getByRole('note')).toHaveTextContent('Datos de ejemplo');
  });
  it('shows loading, a recoverable error, and successful retry', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('offline'));
    vi.stubGlobal('fetch', fetcher); render(<Methodology />);
    expect(screen.getByRole('status')).toHaveTextContent('Cargando');
    expect(await screen.findByRole('alert')).toHaveTextContent('Resultados no disponibles');
    fetcher.mockResolvedValueOnce(response(null, 404)).mockResolvedValueOnce(response(data));
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByRole('note')).toHaveTextContent('Datos de ejemplo');
  });
});

describe('carga del contrato de validación', () => {
  it('prefers published real data and never substitutes mock for a broken real file', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response({})).mockResolvedValueOnce(response({}, 500));
    vi.stubGlobal('fetch', fetcher);
    await expect(loadValidation(new AbortController().signal)).rejects.toThrow('cargar');
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(fetcher.mock.calls[1][0]).toContain('data/real/validation.json');
  });
  it('supports static hosts whose missing manifest falls back to HTML', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response(null, 200, 'text/html')).mockResolvedValueOnce(response(data));
    vi.stubGlobal('fetch', fetcher);
    expect((await loadValidation(new AbortController().signal)).demo_data).toBe(true);
    expect(fetcher.mock.calls[1][0]).toContain('data/mock/validation.json');
  });
  it('rejects invalid data and mock files that claim to be real', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response(null, 404)).mockResolvedValueOnce(response({ ...data, demo_data: false }));
    vi.stubGlobal('fetch', fetcher);
    await expect(loadValidation(new AbortController().signal)).rejects.toThrow('identificado');
    fetcher.mockResolvedValueOnce(response(null, 404)).mockResolvedValueOnce(response({ ...data, rows: [{ value: 'bad' }] }));
    await expect(loadValidation(new AbortController().signal)).rejects.toThrow();
  });
  it('reports manifest errors instead of silently switching to example data', async () => {
    const fetcher = vi.fn().mockResolvedValue(response(null, 503)); vi.stubGlobal('fetch', fetcher);
    await expect(loadValidation(new AbortController().signal)).rejects.toThrow('comprobar');
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
  });
});
