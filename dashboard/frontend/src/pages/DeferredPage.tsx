import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getNotes, type NoteListItem } from '../lib/api';
import { SourceIcon } from '../components/SourceIcon';

function formatDate(iso: string | undefined): string {
  if (!iso) return '--';
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}

export function DeferredPage() {
  const navigate = useNavigate();
  const [notes, setNotes] = useState<NoteListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await getNotes({ status: 'needs_review', per_page: '200' });
        const deferred = (res.notes ?? []).filter(
          (n) => n.review_status === 'defer',
        );
        setNotes(deferred);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <svg className="w-5 h-5 text-sky-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h2 className="text-lg font-semibold text-zinc-100 tracking-tight">Deferred Notes</h2>
        <span
          className="font-medium font-mono tabular-nums text-zinc-400"
          style={{
            fontSize: 11,
            background: 'rgba(255,255,255,0.06)',
            borderRadius: 9999,
            padding: '2px 10px',
          }}
        >
          {notes.length}
        </span>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div style={{ padding: 24 }} className="space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="animate-pulse rounded-lg"
                style={{ height: 44, background: 'rgba(255,255,255,0.03)' }}
              />
            ))}
          </div>
        ) : error ? (
          <div className="text-center text-zinc-500" style={{ padding: 48 }}>{error}</div>
        ) : notes.length === 0 ? (
          <div className="text-center text-zinc-500" style={{ padding: 64 }}>No deferred notes</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: 'rgba(255,255,255,0.02)' }}>
                <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Title</th>
                <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Date</th>
                <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Source</th>
              </tr>
            </thead>
            <tbody>
              {notes.map((note) => (
                <tr
                  key={`${note.source}-${note.source_note_id}`}
                  onClick={() => navigate(`/notes?id=${encodeURIComponent(note.source_note_id)}&source=${encodeURIComponent(note.source)}`)}
                  className="table-row-hover cursor-pointer"
                  style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}
                >
                  <td style={{ padding: '14px 20px', minWidth: 300 }} className="text-zinc-100">
                    <div className="flex items-center gap-2.5">
                      <SourceIcon source={note.source} />
                      <span className="truncate block" style={{ maxWidth: 500 }}>
                        {note.title || note.source_note_id}
                      </span>
                    </div>
                  </td>
                  <td className="text-zinc-500 tabular-nums" style={{ padding: '14px 20px', fontSize: 12 }}>
                    {formatDate(note.created_at)}
                  </td>
                  <td className="font-mono text-zinc-500" style={{ padding: '14px 20px', fontSize: 12 }}>
                    {note.source}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
