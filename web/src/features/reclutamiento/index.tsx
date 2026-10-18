import '../staff/pages.css';
import './reclutamiento.css';
import type { Board } from '../leaderboard/logic';
import { loadDoc, Status, useLoaded, type Source } from '../staff/data';
import type { StaffDoc } from '../staff/StaffView';
import { RecruitView } from './RecruitView';

interface Docs {
  board: Board;
  diablos: Set<string>;
}

async function load(): Promise<{ doc: Docs; source: Source }> {
  const [{ doc: board, source }, { doc: staff }] = await Promise.all([
    loadDoc<Board>('leaderboard.json'),
    loadDoc<StaffDoc>('staff.json'),
  ]);
  const diablos = new Set(staff.franchises.flatMap((f) => f.pitchers.map((p) => p.pitcher_anon_id)));
  return { doc: { board, diablos }, source };
}

export default function ReclutamientoPage() {
  const loaded = useLoaded<Docs>(load, 'reclutamiento');
  if (loaded.state !== 'ready') return <Status loaded={loaded} />;
  return <RecruitView board={loaded.doc.board} diablos={loaded.doc.diablos} source={loaded.source} />;
}
