import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getStatus, getNotes, type StatusResponse, type NoteListItem } from '../lib/api';
import { StatusBadge } from '../components/StatusBadge';

function formatAge(seconds: number | undefined): string {
  if (seconds === undefined || seconds === null) return '--';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  return `${Math.round(seconds / 86400)}d`;
}

export function DashboardPage() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [recentNotes, setRecentNotes] = useState<NoteListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [s, n] = await Promise.all([
          getStatus(),
          getNotes({ per_page: '10' }),
        ]);
        setStatus(s);
        setRecentNotes(n.notes ?? []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="space-y-5">
        <div className="grid grid-cols-3 gap-5">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-32 bg-zinc-900/80 border border-zinc-800/60 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-zinc-900/80 border border-zinc-800/60 rounded-xl p-8 text-center text-zinc-400">
        Failed to load dashboard: {error}
      </div>
    );
  }

  const sumObj = (obj: any): number => {
    if (typeof obj === 'number') return obj;
    if (obj && typeof obj === 'object') return Object.values(obj).reduce((a: number, v: any) => a + sumObj(v), 0);
    return 0;
  };

  const cards = [
    { title: 'RAW', count: sumObj(status?.raw), color: 'text-zinc-200', subtitle: 'Unprocessed captures' },
    { title: 'NORMALIZED', count: sumObj(status?.normalized), color: 'text-blue-400', subtitle: 'Parsed notes' },
    { title: 'IN REVIEW', count: sumObj(status?.review), color: 'text-amber-400', subtitle: 'Awaiting decision' },
    { title: 'COMPILED', count: sumObj(status?.compiled), color: 'text-emerald-400', subtitle: 'Ready for dispatch' },
    { title: 'DISPATCHED', count: sumObj(status?.dispatched), color: 'text-blue-400', subtitle: 'Sent downstream' },
    { title: 'PROCESSED', count: sumObj(status?.processed), color: 'text-slate-400', subtitle: 'Completed' },
  ];

  // Flatten review breakdown: { voicenotes: { ambiguous: 0, ... }, ... } -> { ambiguous: N, ... }
  const reviewObj = status?.review ?? {};
  const reviewBreakdown: Record<string, number> = {};
  for (const source of Object.values(reviewObj) as Record<string, number>[]) {
    if (source && typeof source === 'object') {
      for (const [queue, count] of Object.entries(source)) {
        reviewBreakdown[queue] = (reviewBreakdown[queue] ?? 0) + (typeof count === 'number' ? count : 0);
      }
    }
  }
  const hasBreakdown = Object.values(reviewBreakdown).some(v => v > 0);

  return (
    <div className="space-y-6">
      {/* Status Cards */}
      <div className="grid grid-cols-3 gap-5">
        {cards.map((card) => (
          <div
            key={card.title}
            className="bg-zinc-900/80 border border-zinc-800/60 rounded-xl p-5 shadow-sm"
          >
            <div className="text-[11px] uppercase tracking-[0.08em] font-medium text-zinc-500 mb-2">
              {card.title}
            </div>
            <div className={`text-4xl font-bold ${card.color} tracking-tight`}>
              {card.count}
            </div>
            <div className="text-xs text-zinc-600 mt-1">{card.subtitle}</div>
          </div>
        ))}
      </div>

      {/* Review Breakdown */}
      {hasBreakdown && (
        <div className="bg-zinc-900/80 border border-zinc-800/60 rounded-xl p-5 shadow-sm">
          <div className="text-[11px] uppercase tracking-[0.08em] font-medium text-zinc-500 mb-4">
            Review Breakdown
          </div>
          <div className="flex flex-wrap gap-3">
            {Object.entries(reviewBreakdown).map(([key, val]) => (
              <div key={key} className="flex items-center gap-2.5 bg-zinc-800/40 rounded-lg px-3 py-2">
                <StatusBadge status={key} />
                <span className="text-sm font-semibold font-mono text-zinc-200 tabular-nums">{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Notes */}
      <div className="bg-zinc-900/80 border border-zinc-800/60 rounded-xl shadow-sm overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800/60">
          <span className="text-[11px] uppercase tracking-[0.08em] font-medium text-zinc-500">
            Recent Notes
          </span>
          <Link to="/notes" className="text-xs text-blue-400 hover:text-blue-300 transition-colors">
            View all
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-zinc-900">
                <th className="text-left text-[11px] uppercase tracking-[0.08em] font-medium text-zinc-500 px-5 py-3">Title</th>
                <th className="text-left text-[11px] uppercase tracking-[0.08em] font-medium text-zinc-500 px-5 py-3">Status</th>
                <th className="text-left text-[11px] uppercase tracking-[0.08em] font-medium text-zinc-500 px-5 py-3">Project</th>
                <th className="text-left text-[11px] uppercase tracking-[0.08em] font-medium text-zinc-500 px-5 py-3">Source</th>
                <th className="text-left text-[11px] uppercase tracking-[0.08em] font-medium text-zinc-500 px-5 py-3">Age</th>
              </tr>
            </thead>
            <tbody>
              {recentNotes.map((note) => (
                <tr
                  key={note.source_note_id}
                  className="border-t border-zinc-800/40 hover:bg-zinc-800/30 transition-colors"
                >
                  <td className="px-5 py-3 text-zinc-100 min-w-[300px]">
                    <Link to={`/notes?id=${note.source_note_id}&source=${note.source}`} className="hover:text-blue-400 transition-colors truncate block max-w-md">
                      {note.title || note.source_note_id}
                    </Link>
                  </td>
                  <td className="px-5 py-3">
                    <StatusBadge status={note.status} />
                  </td>
                  <td className="px-5 py-3 text-zinc-400 text-xs">
                    {note.project || '--'}
                  </td>
                  <td className="px-5 py-3 text-zinc-500 font-mono text-xs">
                    {note.source}
                  </td>
                  <td className="px-5 py-3 text-zinc-500 text-xs tabular-nums">
                    {formatAge(note.queue_age_seconds)}
                  </td>
                </tr>
              ))}
              {recentNotes.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center text-zinc-500">
                    No notes found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
