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

  return (
    <div className="space-y-0">
      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <select
          value={filterProject}
          onChange={(e) => { setFilterProject(e.target.value); setPage(1); }}
          className="bg-zinc-800 border border-zinc-700 rounded-md px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:border-blue-500"
        >
          <option value="">All projects</option>
          {projects.map((p) => (
            <option key={p.key} value={p.key}>{p.display_name || p.key}</option>
          ))}
        </select>
        <span className="text-xs text-zinc-500">
          {total} archived note{total !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        {loading ? (
          <div className="p-6 space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-10 bg-zinc-800 rounded animate-pulse" />
            ))}
          </div>
        ) : error ? (
          <div className="p-8 text-center text-zinc-500">{error}</div>
        ) : notes.length === 0 ? (
          <div className="p-12 text-center text-zinc-500">No archived notes</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-zinc-500 uppercase tracking-wider">
                <th className="px-4 py-2">Title</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Project</th>
                <th className="px-4 py-2">Source</th>
                <th className="px-4 py-2">Date</th>
              </tr>
            </thead>
            <tbody>
              {notes.map((note, i) => (
                <tr
                  key={`${note.source}-${note.source_note_id}`}
                  className={`border-t border-zinc-800/50 hover:bg-zinc-800/50 ${
                    i % 2 === 0 ? 'bg-zinc-900' : 'bg-zinc-950/50'
                  }`}
                >
                  <td className="px-4 py-2.5 text-zinc-100 truncate max-w-sm">
                    {note.title || note.source_note_id}
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={note.status} />
                  </td>
                  <td className="px-4 py-2.5 text-zinc-300 text-xs">
                    {note.project || '--'}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs text-zinc-400">
                    {note.source}
                  </td>
                  <td className="px-4 py-2.5 text-zinc-500 text-xs">
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
        <div className="flex items-center justify-center gap-2 pt-4">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page <= 1}
            className="px-3 py-1 text-sm bg-zinc-800 border border-zinc-700 rounded text-zinc-300 hover:bg-zinc-700 disabled:opacity-40"
          >
            Prev
          </button>
          <span className="text-sm text-zinc-400">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page >= totalPages}
            className="px-3 py-1 text-sm bg-zinc-800 border border-zinc-700 rounded text-zinc-300 hover:bg-zinc-700 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
