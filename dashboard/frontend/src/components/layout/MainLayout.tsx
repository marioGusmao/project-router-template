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
    <div className="flex min-h-screen bg-zinc-950">
      <Sidebar counts={counts} />
      <div className="flex-1 ml-[240px]">
        <header className="sticky top-0 z-40 h-14 bg-zinc-950/80 backdrop-blur-md border-b border-zinc-800/80 flex items-center justify-between px-8">
          <h1 className="text-lg font-semibold text-zinc-100 tracking-tight">{title}</h1>
          <div className="flex items-center gap-3">
            <RefreshIndicator ageSeconds={indexAge} onRefreshed={loadMeta} />
          </div>
        </header>
        <main className="p-8">{children}</main>
      </div>
    </div>
  );
}
