import { NavLink, Outlet } from 'react-router-dom';
import { PAGES } from '../routes';

export function Layout() {
  return (
    <div className="app">
      <a className="skip-link" href="#main">Saltar al contenido</a>
      <header className="topbar">
        <NavLink to="/" className="brand" aria-label="Stuff+ 2240, inicio">
          <span className="brand-mark" aria-hidden="true" />
          Stuff+ <strong>2240</strong>
        </NavLink>
        <nav aria-label="Secciones">
          <ul>
            {PAGES.filter((p) => p.nav && p.path !== '/').map((p) => (
              <li key={p.path}>
                <NavLink to={p.path}>{p.title}</NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      <main id="main" tabIndex={-1}>
        <Outlet />
      </main>
      <footer className="footer">
        <p>
          ISAC Sports Analytics Hackathon 2026 · Diablos Rojos del México. Solo agregados: los datos por lanzamiento
          no salen de nuestras computadoras.
        </p>
      </footer>
    </div>
  );
}
