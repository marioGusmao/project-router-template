import { useState, useEffect, useCallback } from 'react';
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

export function RejectedPage() {
  const navigate = useNavigate();
  const [notes, setNotes] = useState<NoteListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const perPage = 25;

  const loadNotes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getNotes({
        review_status: 'reject',
        per_page: String(perPage),
        page: String(page),
      });
      setNotes(res.notes ?? []);
      setTotal(res.total ?? 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    loadNotes();
  }, [loadNotes]);

  const totalPages = Math.max(1, Math.ceil(total / perPage));

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <svg className="w-5 h-5 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h2 className="text-lg font-semibold text-zinc-100 tracking-tight">Rejected Notes</h2>
        <span
          className="font-medium font-mono tabular-nums text-zinc-400"
          style={{
            fontSize: 11,
            background: 'rgba(255,255,255,0.06)',
            borderRadius: 9999,
            padding: '2px 10px',
          }}
        >
          {total}
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
          <div className="text-center text-zinc-500" style={{ padding: 64 }}>No rejected notes</div>
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

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3" style={{ paddingTop: 4 }}>
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page <= 1}
            className="font-medium text-zinc-300 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            style={{
              padding: '6px 14px',
              fontSize: 12,
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: 8,
            }}
          >
            Prev
          </button>
          <span className="text-zinc-400 tabular-nums" style={{ fontSize: 13 }}>
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page >= totalPages}
            className="font-medium text-zinc-300 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            style={{
              padding: '6px 14px',
              fontSize: 12,
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: 8,
            }}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
