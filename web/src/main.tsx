import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
// Self-hosted fonts (web/DESIGN.md): Barlow Condensed for display, Geist for body, Geist Mono for numbers.
import '@fontsource/barlow-condensed/600.css';
import '@fontsource/barlow-condensed/700.css';
import '@fontsource-variable/geist';
import '@fontsource-variable/geist-mono';
import './styles/base.css';
// Design tokens (HACK-039) load when present; the shell has fallbacks until then.
import.meta.glob('./styles/tokens.css', { eager: true });

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
