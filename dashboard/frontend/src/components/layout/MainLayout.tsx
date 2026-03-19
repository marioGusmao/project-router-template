import { type ReactNode, useState, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { RefreshIndicator } from '../RefreshIndicator';
import { getStatus, getTriageItems } from '../../lib/api';

const ROUTE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/notes': 'Notes',
  '/triage': 'Triage',
  '/projects': 'Projects',
  '/archive': 'Archive',
};

interface Props {
  children: ReactNode;
}

export function MainLayout({ children }: Props) {
  const location = useLocation();
  const [indexAge, setIndexAge] = useState<number | null>(null);
  const [counts, setCounts] = useState<{ notes: number; triage: number; projects: number }>({
    notes: 0,
    triage: 0,
    projects: 0,
  });

  const title =
    ROUTE_TITLES[location.pathname] ??
    (location.pathname.startsWith('/projects/') ? 'Project Detail' : 'Dashboard');

  const loadMeta = useCallback(async () => {
    try {
      const [status, triage] = await Promise.all([getStatus(), getTriageItems()]);
      setIndexAge(status.index_age_seconds ?? null);
      setCounts({
        notes: status.normalized + status.review + status.compiled,
        triage: triage.items?.length ?? 0,
        projects: 0,
      });
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    loadMeta();
  }, [loadMeta]);

  return (
    <div className="min-h-screen" style={{ background: '#0a0a0b' }}>
      <Sidebar counts={counts} />
      <div className="flex-1" style={{ marginLeft: 240 }}>
        {/* Header with gradient bottom border */}
        <header
          className="sticky top-0 z-40 backdrop-blur-xl flex items-center justify-between px-8"
          style={{
            height: 56,
            background: 'rgba(10,10,11,0.8)',
            borderBottom: '1px solid transparent',
            backgroundImage: 'linear-gradient(rgba(10,10,11,0.8), rgba(10,10,11,0.8)), linear-gradient(90deg, rgba(59,130,246,0.1), rgba(255,255,255,0.06), rgba(59,130,246,0.1))',
            backgroundOrigin: 'border-box',
            backgroundClip: 'padding-box, border-box',
          }}
        >
          <h1 className="text-xl font-semibold text-zinc-100 tracking-tight">{title}</h1>
          <div className="flex items-center gap-3">
            <RefreshIndicator ageSeconds={indexAge} onRefreshed={loadMeta} />
          </div>
        </header>
        <main className="p-8">{children}</main>
      </div>
    </div>
  );
}
