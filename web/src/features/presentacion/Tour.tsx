import { useEffect, useRef, useState, type ReactNode } from 'react';
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
  const hud = useRef<HTMLElement>(null);
  const [hudH, setHudH] = useState(0);
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

  useEffect(() => {
    // the stage reserves exactly the strip's height so nothing hides behind it
    const el = hud.current;
    if (!el || typeof ResizeObserver === 'undefined') return undefined;
    const ro = new ResizeObserver(() => setHudH(el.getBoundingClientRect().height));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <div className="h71-tour">
      <div className="h71-stage h71-noprint" style={{ paddingBottom: hudH + 16 }}>{renderPage(step.path, step.feature, step.title)}</div>
      <aside ref={hud} className="h71-hud h71-noprint" aria-label="Presentación">
        <div className="h71-step">
          <span className="h71-count">{i + 1} / {STEPS.length}</span>
          <strong>{step.title}</strong>
        </div>
        <div className="h71-say" aria-live="polite">
          <p className="h71-note">{step.note}</p>
          <p className={`h71-number${step.air ? ' is-air' : ''}`}><b>{num.value}</b><span>{num.label}</span></p>
        </div>
        <div className="h71-controls">
          <button type="button" className={`h71-clock${left === 0 ? ' is-over' : ''}`} onClick={() => setRunning((r) => !r)}
            aria-label={running ? 'Pausar el tiempo' : 'Iniciar el tiempo'} aria-pressed={running}>
            <span role="timer" aria-live="off" aria-label="Tiempo restante">{formatClock(left)}</span>
          </button>
          <button type="button" className="h48-button is-ghost" onClick={() => go(-1)} disabled={i === 0} aria-label="Anterior">
            <span className="h71-long" aria-hidden="true">Anterior</span><span className="h71-short" aria-hidden="true">←</span>
          </button>
          <button type="button" className="h48-button" onClick={() => { setRunning(true); go(1); }} disabled={i === STEPS.length - 1}>Siguiente</button>
          <button type="button" className="h48-button is-ghost" onClick={onExit}>Salir</button>
        </div>
        <p className="h71-hint h71-wide">
          Flechas o espacio avanzan, Esc sale, el reloj inicia o pausa.{' '}
          <button type="button" className="h71-link" onClick={() => window.print()}>Imprimir guion</button>
        </p>
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
