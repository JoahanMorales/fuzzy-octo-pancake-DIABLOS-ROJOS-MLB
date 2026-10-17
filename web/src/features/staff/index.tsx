import './pages.css';
import { loadDoc, Status, useLoaded } from './data';
import { StaffView, type StaffDoc } from './StaffView';

export default function StaffPage() {
  const loaded = useLoaded<StaffDoc>(() => loadDoc<StaffDoc>('staff.json'), 'staff');
  if (loaded.state !== 'ready') return <Status loaded={loaded} />;
  return <StaffView doc={loaded.doc} source={loaded.source} />;
}
