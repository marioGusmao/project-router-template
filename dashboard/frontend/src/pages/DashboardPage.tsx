import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getStatus, getNotes, type StatusResponse, type NoteListItem } from '../lib/api';
import { StatusBadge } from '../components/StatusBadge';
import { SourceIcon } from '../components/SourceIcon';

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
      <div className="space-y-6">
        <div className="grid grid-cols-3 gap-5">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="card animate-pulse"
              style={{ height: 140, padding: 24, animationDelay: `${i * 80}ms` }}
            />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card" style={{ padding: 48, textAlign: 'center', color: '#a1a1aa' }}>
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
    { title: 'RAW', count: sumObj(status?.raw), color: '#e4e4e7', subtitle: 'Unprocessed captures' },
    { title: 'NORMALIZED', count: sumObj(status?.normalized), color: '#60a5fa', subtitle: 'Parsed notes' },
    { title: 'IN REVIEW', count: sumObj(status?.review), color: '#fbbf24', subtitle: 'Awaiting decision' },
    { title: 'COMPILED', count: sumObj(status?.compiled), color: '#34d399', subtitle: 'Ready for dispatch' },
    { title: 'DISPATCHED', count: sumObj(status?.dispatched), color: '#60a5fa', subtitle: 'Sent downstream' },
    { title: 'PROCESSED', count: sumObj(status?.processed), color: '#94a3b8', subtitle: 'Completed' },
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
        {cards.map((card, i) => (
          <div
            key={card.title}
            className="card animate-in"
            style={{ padding: 24, animationDelay: `${i * 80}ms` }}
          >
            <div
              className="font-semibold uppercase tracking-widest text-zinc-500"
              style={{ fontSize: 10, letterSpacing: '0.12em', marginBottom: 12 }}
            >
              {card.title}
            </div>
            <div
              className="font-bold tracking-tighter"
              style={{ fontSize: 48, lineHeight: 1, color: card.color }}
            >
              {card.count}
            </div>
            <div className="text-zinc-600" style={{ fontSize: 13, marginTop: 8 }}>
              {card.subtitle}
            </div>
          </div>
        ))}
      </div>

      {/* Review Breakdown */}
      {hasBreakdown && (
        <div
          className="card animate-in"
          style={{ padding: 24, animationDelay: `${cards.length * 80}ms` }}
        >
          <div
            className="font-semibold uppercase tracking-widest text-zinc-500"
            style={{ fontSize: 10, letterSpacing: '0.12em', marginBottom: 16 }}
          >
            Review Breakdown
          </div>
          <div className="flex flex-wrap gap-3">
            {Object.entries(reviewBreakdown).map(([key, val]) => (
              <div
                key={key}
                className="flex items-center gap-2.5 rounded-xl"
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  padding: '8px 14px',
                }}
              >
                <StatusBadge status={key} />
                <span className="font-semibold font-mono text-zinc-200 tabular-nums text-sm">
                  {val}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Notes */}
      <div
        className="card animate-in overflow-hidden"
        style={{ animationDelay: `${(cards.length + 1) * 80}ms` }}
      >
        <div
          className="flex items-center justify-between px-6 py-4"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
        >
          <span
            className="font-semibold uppercase tracking-widest text-zinc-500"
            style={{ fontSize: 10, letterSpacing: '0.12em' }}
          >
            Recent Notes
          </span>
          <Link
            to="/notes"
            className="text-blue-400 hover:text-blue-300 transition-colors"
            style={{ fontSize: 12 }}
          >
            View all
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: 'rgba(255,255,255,0.02)' }}>
                <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Title</th>
                <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Status</th>
                <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Project</th>
                <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Source</th>
                <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Age</th>
              </tr>
            </thead>
            <tbody>
              {recentNotes.map((note) => (
                <tr
                  key={note.source_note_id}
                  className="table-row-hover"
                  style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}
                >
                  <td style={{ padding: '14px 20px', minWidth: 300 }} className="text-zinc-100">
                    <Link
                      to={`/notes?id=${note.source_note_id}&source=${note.source}`}
                      className="hover:text-blue-400 transition-colors flex items-center gap-2.5"
                    >
                      <SourceIcon source={note.source} />
                      <span className="truncate" style={{ maxWidth: 380 }}>
                        {note.title || note.source_note_id}
                      </span>
                    </Link>
                  </td>
                  <td style={{ padding: '14px 20px' }}>
                    <StatusBadge status={note.status} />
                  </td>
                  <td className="text-zinc-400" style={{ padding: '14px 20px', fontSize: 12 }}>
                    {note.project || '--'}
                  </td>
                  <td className="text-zinc-500 font-mono" style={{ padding: '14px 20px', fontSize: 12 }}>
                    {note.source}
                  </td>
                  <td className="text-zinc-500 tabular-nums" style={{ padding: '14px 20px', fontSize: 12 }}>
                    {formatAge(note.queue_age_seconds)}
                  </td>
                </tr>
              ))}
              {recentNotes.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center text-zinc-500" style={{ padding: '48px 20px' }}>
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
