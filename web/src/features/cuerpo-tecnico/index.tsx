import '../staff/pages.css';
import './cuerpo-tecnico.css';
import { useEffect, useState } from 'react';
import { DATA_BASE, dataSource, loadDoc, Status, useLoaded } from '../staff/data';
import type { StaffDoc } from '../staff/StaffView';
import { BullpenView, type PitcherDoc } from './BullpenView';
import type { PlanRow } from './logic';

/** Design-lab plan: real/design_lab.json (HACK-065) when published, else the /laboratorio copy of the same CSVs. */
async function loadPlan(): Promise<Record<string, PlanRow[]>> {
  if ((await dataSource()) === 'real') {
    try {
      const r = await fetch(`${DATA_BASE}real/design_lab.json`);
      if (r.ok) return ((await r.json()) as { plan: Record<string, PlanRow[]> }).plan;
    } catch {
      /* fall back to the local copy */
    }
  }
  return ((await import('../laboratorio/design_lab.json')).default as unknown as { plan: Record<string, PlanRow[]> }).plan;
}

export default function CuerpoTecnicoPage() {
  const staff = useLoaded<StaffDoc>(() => loadDoc<StaffDoc>('staff.json'), 'staff');
  const [plan, setPlan] = useState<Record<string, PlanRow[]> | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [pitcher, setPitcher] = useState<PitcherDoc | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadPlan().then(setPlan).catch(() => setPlan(null));
  }, []);

  useEffect(() => {
    if (!picked) return undefined;
    let live = true;
    setLoading(true);
    setPitcher(null);
    loadDoc<PitcherDoc>(`pitcher/${picked}.json`)
      .then(({ doc }) => live && setPitcher(doc))
      .catch(() => live && setPitcher(null))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [picked]);

  if (staff.state !== 'ready') return <Status loaded={staff} />;
  return (
    <BullpenView staff={staff.doc} source={staff.source} pitcher={pitcher} plan={plan}
      onPick={setPicked} pickedId={picked} loadingPitcher={loading} />
  );
}
