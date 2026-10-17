import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource/barlow-condensed/600.css';
import '@fontsource/barlow-condensed/700.css';
import '@fontsource-variable/geist';
import '@fontsource-variable/geist-mono';
import './sim.css';
import App from './App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
