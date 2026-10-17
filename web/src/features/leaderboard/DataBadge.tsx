/** Says whether the page shows the deploy aggregates (real/) or the example mock (demo_data). */
export function DataBadge({ source, demo }: { source: 'real' | 'mock'; demo: boolean }) {
  const real = source === 'real' && !demo;
  return (
    <span className={`data-badge ${real ? 'is-real' : 'is-demo'}`} title={real ? 'data/real/' : 'data/mock/'}>
      {real ? 'Datos reales (agregados)' : 'Ejemplo'}
    </span>
  );
}
