import { Link } from 'react-router-dom';

export function NotFound() {
  return (
    <section className="placeholder">
      <p className="eyebrow">404</p>
      <h1>Esta página no existe</h1>
      <p>
        <Link to="/">Volver al inicio</Link>
      </p>
    </section>
  );
}
