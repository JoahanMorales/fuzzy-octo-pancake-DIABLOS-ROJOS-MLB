import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles/base.css';
// Design tokens (HACK-039) load when present; the shell has fallbacks until then.
import.meta.glob('./styles/tokens.css', { eager: true });

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
