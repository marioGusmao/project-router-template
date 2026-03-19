import { type ReactNode, useState, useEffect, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { KeyboardHelp } from './KeyboardHelp';
import { CommandPalette } from './CommandPalette';
import { UndoSnackbar } from './UndoSnackbar';
import { RefreshIndicator } from '../RefreshIndicator';
import { getStatus, getTriageItems, getNotes, refreshIndex } from '../../lib/api';
import { useKeyboard } from '../../hooks/useKeyboard';

const ROUTE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/notes': 'Notes',
  '/triage': 'Triage',
  '/projects': 'Projects',
  '/archive': 'Archive',
  '/rejected': 'Rejected',
  '/deferred': 'Deferred',
};

const NAV_ROUTES = ['/', '/notes', '/triage', '/projects', '/archive', '/rejected', '/deferred'];

interface Props {
  children: ReactNode;
}

export function MainLayout({ children }: Props) {
  const location = useLocation();
  const navigate = useNavigate();
  const [indexAge, setIndexAge] = useState<number | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [counts, setCounts] = useState<{ notes: number; triage: number; projects: number; rejected: number; deferred: number }>({
    notes: 0,
    triage: 0,
    projects: 0,
    rejected: 0,
    deferred: 0,
  });

  const title =
    ROUTE_TITLES[location.pathname] ??
    (location.pathname.startsWith('/projects/') ? 'Project Detail' : 'Dashboard');

  const loadMeta = useCallback(async () => {
    try {
      const [status, triage, allReview] = await Promise.all([
        getStatus(),
        getTriageItems(),
        getNotes({ status: 'needs_review', per_page: '200' }),
      ]);
      setIndexAge(status.index_age_seconds ?? null);
      const reviewNotes = allReview.notes ?? [];
      const rejected = reviewNotes.filter(n => n.review_status === 'reject').length;
      const deferred = reviewNotes.filter(n => n.review_status === 'defer').length;
      setCounts({
        notes: status.normalized + status.review + status.compiled,
        triage: triage.items?.length ?? 0,
        projects: 0,
        rejected,
        deferred,
      });
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    loadMeta();
  }, [loadMeta]);

  const handleRefresh = useCallback(async () => {
    await refreshIndex();
    await loadMeta();
  }, [loadMeta]);

  useKeyboard({
    '?': () => setShowHelp(prev => !prev),
    'r': () => { handleRefresh(); },
    'escape': () => { setShowHelp(false); setShowCommandPalette(false); },
    'cmd+k': () => setShowCommandPalette(prev => !prev),
    '1': () => navigate(NAV_ROUTES[0]),
    '2': () => navigate(NAV_ROUTES[1]),
    '3': () => navigate(NAV_ROUTES[2]),
    '4': () => navigate(NAV_ROUTES[3]),
    '5': () => navigate(NAV_ROUTES[4]),
    '6': () => navigate(NAV_ROUTES[5]),
    '7': () => navigate(NAV_ROUTES[6]),
  });

  return (
    <div className="min-h-screen" style={{ background: '#0a0a0b' }}>
      <Sidebar counts={counts} />
      <div className="flex-1" style={{ marginLeft: 240 }}>
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
            <button
              onClick={() => setShowHelp(true)}
              className="text-zinc-600 hover:text-zinc-400 transition-colors text-sm font-mono"
              title="Keyboard shortcuts (?)"
            >
              ?
            </button>
            <RefreshIndicator ageSeconds={indexAge} onRefreshed={handleRefresh} />
          </div>
        </header>
        <main className="p-8" style={{ overflowX: 'hidden' }}>{children}</main>
      </div>
      {showHelp && <KeyboardHelp onClose={() => setShowHelp(false)} />}
      {showCommandPalette && <CommandPalette onClose={() => setShowCommandPalette(false)} />}
      <UndoSnackbar />
    </div>
  );
}
