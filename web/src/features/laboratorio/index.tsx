import '../staff/pages.css';
import { Status, useLoaded } from '../staff/data';
import { LabView, type LabDoc } from './LabView';

// design_lab.json is generated from reports/design_lab by make_data.py (no contract file for it yet).
const load = async () => ({ doc: (await import('./design_lab.json')).default as unknown as LabDoc, source: 'real' as const });

export default function LaboratorioPage() {
  const loaded = useLoaded<LabDoc>(load, 'laboratorio');
  if (loaded.state !== 'ready') return <Status loaded={loaded} />;
  return <LabView doc={loaded.doc} />;
}
