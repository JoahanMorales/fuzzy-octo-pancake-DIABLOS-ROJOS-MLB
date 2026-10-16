export function Placeholder({ title, task }: { title: string; task: string }) {
  return (
    <section className="placeholder" aria-labelledby="placeholder-title">
      <p className="eyebrow">En construcción · {task}</p>
      <h1 id="placeholder-title">{title}</h1>
      <p>Esta sección llega en la ola 2. Mientras tanto, el tablero Streamlit sigue disponible como respaldo.</p>
    </section>
  );
}
