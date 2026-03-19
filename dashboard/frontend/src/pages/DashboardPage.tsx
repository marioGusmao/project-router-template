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
      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-28 bg-zinc-900 border border-zinc-800 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-8 text-center text-zinc-400">
        Failed to load dashboard: {error}
      </div>
    );
  }

  const cards = [
    { title: 'RAW', count: status?.raw ?? 0, color: 'text-zinc-300', subtitle: 'Unprocessed captures' },
    { title: 'NORMALIZED', count: status?.normalized ?? 0, color: 'text-blue-400', subtitle: 'Parsed notes' },
    { title: 'IN REVIEW', count: status?.review ?? 0, color: 'text-amber-400', subtitle: 'Awaiting decision' },
    { title: 'COMPILED', count: status?.compiled ?? 0, color: 'text-emerald-400', subtitle: 'Ready for dispatch' },
    { title: 'DISPATCHED', count: status?.dispatched ?? 0, color: 'text-blue-400', subtitle: 'Sent downstream' },
    { title: 'PROCESSED', count: status?.processed ?? 0, color: 'text-slate-400', subtitle: 'Completed' },
  ];

  const reviewBreakdown = status?.review_breakdown ?? {};
  const hasBreakdown = Object.keys(reviewBreakdown).length > 0;

  return (
    <div className="space-y-6">
      {/* Status Cards */}
      <div className="grid grid-cols-3 gap-4">
        {cards.map((card) => (
          <div
            key={card.title}
            className="bg-zinc-900 border border-zinc-800 rounded-lg p-4"
          >
            <div className="text-xs uppercase tracking-wider text-zinc-400 mb-1">
              {card.title}
            </div>
            <div className={`text-3xl font-bold ${card.color}`}>
              {card.count}
            </div>
            <div className="text-xs text-zinc-500 mt-1">{card.subtitle}</div>
          </div>
        ))}
      </div>

      {/* Review Breakdown */}
      {hasBreakdown && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs uppercase tracking-wider text-zinc-400 mb-3">
            Review Breakdown
          </div>
          <div className="flex flex-wrap gap-3">
            {Object.entries(reviewBreakdown).map(([key, val]) => (
              <div key={key} className="flex items-center gap-2">
                <StatusBadge status={key} />
                <span className="text-sm font-mono text-zinc-300">{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Notes */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg">
        <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
          <span className="text-xs uppercase tracking-wider text-zinc-400">
            Recent Notes
          </span>
          <Link to="/notes" className="text-xs text-blue-400 hover:text-blue-300">
            View all
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-zinc-500 uppercase tracking-wider">
                <th className="px-4 py-2">Title</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Project</th>
                <th className="px-4 py-2">Source</th>
                <th className="px-4 py-2">Age</th>
              </tr>
            </thead>
            <tbody>
              {recentNotes.map((note, i) => (
                <tr
                  key={note.source_note_id}
                  className={`border-t border-zinc-800/50 hover:bg-zinc-800/50 ${i % 2 === 0 ? 'bg-zinc-900' : 'bg-zinc-950/50'}`}
                >
                  <td className="px-4 py-2.5 text-zinc-100 truncate max-w-xs">
                    <Link to={`/notes?id=${note.source_note_id}&source=${note.source}`} className="hover:text-blue-400">
                      {note.title || note.source_note_id}
                    </Link>
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={note.status} />
                  </td>
                  <td className="px-4 py-2.5 text-zinc-300 text-xs">
                    {note.project || '--'}
                  </td>
                  <td className="px-4 py-2.5 text-zinc-400 font-mono text-xs">
                    {note.source}
                  </td>
                  <td className="px-4 py-2.5 text-zinc-500 text-xs">
                    {formatAge(note.queue_age_seconds)}
                  </td>
                </tr>
              ))}
              {recentNotes.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-zinc-500">
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
