import { useEffect, useState, type ReactNode } from 'react';
import { formatClock, STEPS, TOUR_SECONDS, type TourDocs } from './steps';

const NEXT = new Set(['ArrowRight', 'ArrowDown', 'PageDown', ' ']);
const PREV = new Set(['ArrowLeft', 'ArrowUp', 'PageUp']);

function typing(target: EventTarget | null) {
  const el = target as HTMLElement | null;
  return !!el && (el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName));
}

/** Keyboard tour over the real pages. `renderPage` draws a step's page (the app's own route element). */
export function Tour({ docs, renderPage, onExit, start = 0 }: {
  docs: TourDocs;
  renderPage: (path: string, feature: string, title: string) => ReactNode;
  onExit: () => void;
  start?: number;
}) {
  const [i, setI] = useState(start);
  const [running, setRunning] = useState(false);
  const [left, setLeft] = useState(TOUR_SECONDS);
  const step = STEPS[i];
  const num = step.number(docs);
  const go = (d: number) => setI((k) => Math.min(STEPS.length - 1, Math.max(0, k + d)));

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onExit();
      } else if (typing(e.target)) {
        return;
      } else if (NEXT.has(e.key)) {
        e.preventDefault();
        setRunning(true);
        go(1);
      } else if (PREV.has(e.key)) {
        e.preventDefault();
        go(-1);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onExit]);

  useEffect(() => {
    if (!running) return undefined;
    const t = window.setInterval(() => setLeft((s) => Math.max(0, s - 1)), 1000);
    return () => window.clearInterval(t);
  }, [running]);

  return (
    <div className="h71-tour">
      <div className="h71-stage h71-noprint" aria-hidden={false}>{renderPage(step.path, step.feature, step.title)}</div>
      <aside className="h71-hud h71-noprint" aria-label="Presentación" aria-live="polite">
        <div className="h71-step">
          <span className="h71-count">{i + 1} / {STEPS.length}</span>
          <strong>{step.title}</strong>
        </div>
        <p className="h71-note">{step.note}</p>
        <p className="h71-number"><b>{num.value}</b><span>{num.label}</span></p>
        <div className="h71-controls">
          <button type="button" className="h48-button is-ghost" onClick={() => go(-1)} disabled={i === 0}>Anterior</button>
          <button type="button" className="h48-button" onClick={() => { setRunning(true); go(1); }} disabled={i === STEPS.length - 1}>Siguiente</button>
          <span className={`h71-clock${left === 0 ? ' is-over' : ''}`} role="timer" aria-label="Tiempo restante">{formatClock(left)}</span>
          <button type="button" className="h48-button is-ghost" onClick={() => setRunning((r) => !r)}>{running ? 'Pausar' : 'Iniciar'}</button>
          <button type="button" className="h48-button is-ghost" onClick={() => window.print()}>Imprimir guion</button>
          <button type="button" className="h48-button is-ghost" onClick={onExit}>Salir (Esc)</button>
        </div>
      </aside>
      <section className="h71-script" aria-label="Guion del presentador">
        <h1>Guion · Stuff+ 2240 · 5 minutos</h1>
        <ol>
          {STEPS.map((s) => {
            const n = s.number(docs);
            return (
              <li key={s.path}>
                <strong>{s.title}</strong> ({s.path}). {s.note} Cifra: {n.value} {n.label}.
              </li>
            );
          })}
        </ol>
        <p>Flechas o espacio avanzan, Esc sale. Las cifras salen de los JSON publicados de la app.</p>
      </section>
    </div>
  );
}
