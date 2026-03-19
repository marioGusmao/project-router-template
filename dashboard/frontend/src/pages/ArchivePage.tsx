import { useState, useEffect, useCallback } from 'react';
import { getNotes, getProjects, type NoteListItem, type Project } from '../lib/api';
import { StatusBadge } from '../components/StatusBadge';

function formatDate(iso: string | undefined): string {
  if (!iso) return '--';
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}

export function ArchivePage() {
  const [notes, setNotes] = useState<NoteListItem[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterProject, setFilterProject] = useState('');

  const perPage = 25;

  useEffect(() => {
    async function loadProjects() {
      try {
        const res = await getProjects();
        setProjects(res.projects ?? []);
      } catch {
        // silent
      }
    }
    loadProjects();
  }, []);

  const loadNotes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Load both dispatched and processed
      const params: Record<string, string> = {
        page: String(page),
        per_page: String(perPage),
        status: 'dispatched',
      };
      if (filterProject) params.project = filterProject;

      const [dispatched, processed] = await Promise.all([
        getNotes(params),
        getNotes({ ...params, status: 'processed' }),
      ]);

      const combined = [...(dispatched.notes ?? []), ...(processed.notes ?? [])];
      setNotes(combined);
      setTotal((dispatched.total ?? 0) + (processed.total ?? 0));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [page, filterProject]);

  useEffect(() => {
    loadNotes();
  }, [loadNotes]);

  const totalPages = Math.max(1, Math.ceil(total / perPage));

  const selectStyle: React.CSSProperties = {
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: 8,
    padding: '6px 12px',
    fontSize: 13,
    color: '#e4e4e7',
    outline: 'none',
  };

  return (
    <div className="space-y-5">
      {/* Filters */}
      <div className="flex items-center gap-3">
        <select
          value={filterProject}
          onChange={(e) => { setFilterProject(e.target.value); setPage(1); }}
          style={selectStyle}
        >
          <option value="">All projects</option>
          {projects.map((p) => (
            <option key={p.key} value={p.key}>{p.display_name || p.key}</option>
          ))}
        </select>
        <span className="text-zinc-500 font-medium tabular-nums" style={{ fontSize: 11 }}>
          {total} archived note{total !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div style={{ padding: 24 }} className="space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
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
          <div className="text-center text-zinc-500" style={{ padding: 64 }}>No archived notes</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: 'rgba(255,255,255,0.02)' }}>
                <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Title</th>
                <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Status</th>
                <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Project</th>
                <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Source</th>
                <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Date</th>
              </tr>
            </thead>
            <tbody>
              {notes.map((note) => (
                <tr
                  key={`${note.source}-${note.source_note_id}`}
                  className="table-row-hover"
                  style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}
                >
                  <td className="text-zinc-100 truncate" style={{ padding: '14px 20px', maxWidth: 400 }}>
                    {note.title || note.source_note_id}
                  </td>
                  <td style={{ padding: '14px 20px' }}>
                    <StatusBadge status={note.status} />
                  </td>
                  <td className="text-zinc-400" style={{ padding: '14px 20px', fontSize: 12 }}>
                    {note.project || '--'}
                  </td>
                  <td className="font-mono text-zinc-500" style={{ padding: '14px 20px', fontSize: 12 }}>
                    {note.source}
                  </td>
                  <td className="text-zinc-500 tabular-nums" style={{ padding: '14px 20px', fontSize: 12 }}>
                    {formatDate(note.created_at)}
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
