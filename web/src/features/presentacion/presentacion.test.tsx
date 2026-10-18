import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { parseContractFile } from '../../contract/types';
import leaderboard from '../../../public/data/mock/leaderboard.json';
import parks from '../../../public/data/mock/parks.json';
import staff from '../../../public/data/mock/staff.json';
import validation from '../../../public/data/mock/validation.json';
import { formatClock, STEPS, type TourDocs } from './steps';
import { Tour } from './Tour';

const docs = {
  validation: parseContractFile('validation.json', validation),
  parks: parseContractFile('parks.json', parks),
  staff: parseContractFile('staff.json', staff),
  leaderboard: parseContractFile('leaderboard.json', leaderboard),
} as TourDocs;

const page = (path: string) => <div data-testid="stage">{path}</div>;

afterEach(() => vi.useRealTimers());

describe('presentation tour', () => {
  it('follows landing, simulador, altitud, staff, reclutamiento, metodologia', () => {
    expect(STEPS.map((s) => s.path)).toEqual(['/', '/simulador', '/altitud', '/staff', '/reclutamiento', '/metodologia']);
  });

  it('every step has a note and a number computed from the contract JSON', () => {
    for (const s of STEPS) {
      const n = s.number(docs);
      expect(s.note.length).toBeGreaterThan(20);
      expect(n.value).toMatch(/\d/);
      expect(`${s.note} ${n.label}`).not.toMatch(/—/);
    }
    expect(STEPS[0].number(docs).value).toContain(Math.abs(docs.validation.highlights.league_delta_cdmx).toFixed(1));
  });

  it('arrows and space move between steps and Esc exits', () => {
    const onExit = vi.fn();
    render(<Tour docs={docs} renderPage={page} onExit={onExit} />);
    expect(screen.getByTestId('stage')).toHaveTextContent('/');
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(screen.getByTestId('stage')).toHaveTextContent('/simulador');
    fireEvent.keyDown(window, { key: ' ' });
    expect(screen.getByTestId('stage')).toHaveTextContent('/altitud');
    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(screen.getByTestId('stage')).toHaveTextContent('/simulador');
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onExit).toHaveBeenCalledTimes(1);
  });

  it('ignores arrow keys while typing in a page control', () => {
    render(<Tour docs={docs} renderPage={() => <input aria-label="campo" />} onExit={() => {}} />);
    fireEvent.keyDown(screen.getByLabelText('campo'), { key: 'ArrowRight' });
    expect(screen.getByText('1 / 6')).toBeInTheDocument();
  });

  it('runs a 5-minute timer and prints the script', () => {
    vi.useFakeTimers();
    const print = vi.spyOn(window, 'print').mockImplementation(() => {});
    render(<Tour docs={docs} renderPage={page} onExit={() => {}} />);
    expect(screen.getByRole('timer')).toHaveTextContent('5:00');
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar el tiempo' }));
    act(() => vi.advanceTimersByTime(61_000));
    expect(screen.getByRole('timer')).toHaveTextContent('3:59');
    expect(formatClock(-3)).toBe('0:00');
    fireEvent.click(screen.getByRole('button', { name: 'Imprimir guion' }));
    expect(print).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('Guion del presentador').querySelectorAll('li')).toHaveLength(STEPS.length);
  });
});
