import '../staff/pages.css';
import { useEffect, useState } from 'react';
import type { CompositeModel } from '../../model/predict';
import { DATA_BASE } from '../staff/data';
import { ProspectView } from './ProspectView';

/** The model (4.6 MB) is fetched at runtime from data/models/, so it stays out of the JS bundle. */
export default function ProspectoPage() {
  const [model, setModel] = useState<CompositeModel | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    fetch(`${DATA_BASE}models/stuff.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((m: CompositeModel) => live && setModel(m))
      .catch((e: unknown) => live && setError(e instanceof Error ? e.message : String(e)));
    return () => {
      live = false;
    };
  }, []);
  if (error) return <p className="h48-error" role="alert">No se pudo cargar el modelo: {error}</p>;
  return <ProspectView model={model} />;
}
