import '../staff/pages.css';
import './presentacion.css';
import { useCallback } from 'react';
import { pageElement } from '../../routes';
import { loadDoc, Status, useLoaded, type Source } from '../staff/data';
import type { TourDocs } from './steps';
import { Tour } from './Tour';

async function load(): Promise<{ doc: TourDocs; source: Source }> {
  const [v, p, s, l] = await Promise.all([
    loadDoc<TourDocs['validation']>('validation.json'),
    loadDoc<TourDocs['parks']>('parks.json'),
    loadDoc<TourDocs['staff']>('staff.json'),
    loadDoc<TourDocs['leaderboard']>('leaderboard.json'),
  ]);
  return { doc: { validation: v.doc, parks: p.doc, staff: s.doc, leaderboard: l.doc }, source: v.source };
}

export default function PresentacionPage() {
  const loaded = useLoaded<TourDocs>(load, 'presentacion');
  const exit = useCallback(() => {
    window.location.hash = '#/';
  }, []);
  if (loaded.state !== 'ready') return <Status loaded={loaded} />;
  return (
    <Tour
      docs={loaded.doc}
      onExit={exit}
      renderPage={(path, feature, title) => pageElement({ path, feature, title, nav: false, task: 'HACK-071' })}
    />
  );
}
