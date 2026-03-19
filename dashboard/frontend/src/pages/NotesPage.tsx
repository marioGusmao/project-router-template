import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getNotes, getProjects, getStatus, type NoteListItem, type Project, type StatusResponse } from '../lib/api';
import { StatusBadge } from '../components/StatusBadge';
import { ConfidenceBar } from '../components/ConfidenceBar';
import { NoteDetail } from '../components/notes/NoteDetail';

function formatAge(seconds: number | undefined): string {
  if (seconds === undefined || seconds === null) return '--';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  return `${Math.round(seconds / 86400)}d`;
}

function ageColor(seconds: number | undefined): string {
  if (seconds === undefined || seconds === null) return 'text-zinc-500';
  if (seconds < 3600) return 'text-zinc-400';
  if (seconds < 86400) return 'text-amber-500';
  return 'text-rose-500';
}

export function NotesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [notes, setNotes] = useState<NoteListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [sources, setSources] = useState<string[]>([]);

  const [filterStatus, setFilterStatus] = useState(searchParams.get('status') ?? '');
  const [filterSource, setFilterSource] = useState(searchParams.get('source') ?? '');
  const [filterProject, setFilterProject] = useState(searchParams.get('project') ?? '');
  const [search, setSearch] = useState(searchParams.get('search') ?? '');

  const selectedId = searchParams.get('id');
  const selectedSource = searchParams.get('source') ?? '';

  const perPage = 25;

  const loadNotes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {
        page: String(page),
        per_page: String(perPage),
      };
      if (filterStatus) params.status = filterStatus;
      if (filterSource) params.source = filterSource;
      if (filterProject) params.project = filterProject;
      if (search) params.search = search;

      const res = await getNotes(params);
      setNotes(res.notes ?? []);
      setTotal(res.total ?? 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [page, filterStatus, filterSource, filterProject, search]);

  useEffect(() => {
    loadNotes();
  }, [loadNotes]);

  useEffect(() => {
    async function loadMeta() {
      try {
        const [p, s] = await Promise.all([getProjects(), getStatus()]);
        setProjects(p.projects ?? []);
        setSources((s as StatusResponse).sources ?? []);
      } catch {
        // silent
      }
    }
    loadMeta();
  }, []);

  const selectNote = (note: NoteListItem) => {
    setSearchParams({ id: note.source_note_id, source: note.source });
  };

  const closeDetail = () => {
    const params: Record<string, string> = {};
    if (filterStatus) params.status = filterStatus;
    if (filterSource) params.source = filterSource;
    if (filterProject) params.project = filterProject;
    if (search) params.search = search;
    setSearchParams(params);
  };

  const totalPages = Math.ceil(total / perPage);

  const statuses = [
    'normalized', 'classified', 'needs_review', 'ambiguous',
    'pending_project', 'dispatched', 'processed',
  ];

  return (
    <div className="flex gap-0 -m-6">
      {/* Table section */}
      <div className={`flex-1 min-w-0 ${selectedId ? 'w-[60%]' : 'w-full'}`}>
        {/* Filter bar */}
        <div className="sticky top-14 z-30 bg-zinc-950 border-b border-zinc-800 px-6 py-3 flex items-center gap-3 flex-wrap">
          <select
            value={filterStatus}
            onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
            className="bg-zinc-800 border border-zinc-700 rounded-md px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:border-blue-500"
          >
            <option value="">All statuses</option>
            {statuses.map((s) => (
              <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
            ))}
          </select>

          <select
            value={filterSource}
            onChange={(e) => { setFilterSource(e.target.value); setPage(1); }}
            className="bg-zinc-800 border border-zinc-700 rounded-md px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:border-blue-500"
          >
            <option value="">All sources</option>
            {sources.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

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

          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { setPage(1); loadNotes(); } }}
            placeholder="Search notes..."
            className="flex-1 min-w-[200px] bg-zinc-800 border border-zinc-700 rounded-md px-3 py-1.5 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-blue-500"
          />

          <span className="text-xs text-zinc-500">
            {total} note{total !== 1 ? 's' : ''}
          </span>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-6 space-y-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="h-10 bg-zinc-900 rounded animate-pulse" />
              ))}
            </div>
          ) : error ? (
            <div className="p-8 text-center text-zinc-500">{error}</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-zinc-500 uppercase tracking-wider">
                  <th className="px-6 py-2">Title</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Project</th>
                  <th className="px-4 py-2">Confidence</th>
                  <th className="px-4 py-2">Source</th>
                  <th className="px-4 py-2">Age</th>
                </tr>
              </thead>
              <tbody>
                {notes.map((note, i) => (
                  <tr
                    key={`${note.source}-${note.source_note_id}`}
                    onClick={() => selectNote(note)}
                    className={`border-t border-zinc-800/50 cursor-pointer hover:bg-zinc-800/50 transition-colors ${
                      i % 2 === 0 ? 'bg-zinc-900' : 'bg-zinc-950/50'
                    } ${selectedId === note.source_note_id ? 'bg-blue-500/10 border-l-2 border-l-blue-500' : ''}`}
                  >
                    <td className="px-6 py-2.5 text-zinc-100 truncate max-w-xs">
                      {note.title || note.source_note_id}
                    </td>
                    <td className="px-4 py-2.5">
                      <StatusBadge status={note.status} />
                    </td>
                    <td className="px-4 py-2.5 text-xs">
                      {note.user_suggested_project && note.user_suggested_project !== note.project ? (
                        <span className="text-violet-400">
                          Suggested: {note.user_suggested_project}
                        </span>
                      ) : (
                        <span className="text-zinc-300">{note.project || '--'}</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <ConfidenceBar value={note.confidence ?? 0} />
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs text-zinc-400">
                      {note.source}
                    </td>
                    <td className={`px-4 py-2.5 text-xs ${ageColor(note.queue_age_seconds)}`}>
                      {formatAge(note.queue_age_seconds)}
                    </td>
                  </tr>
                ))}
                {notes.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-zinc-500">
                      No notes found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 px-6 py-4 border-t border-zinc-800">
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

      {/* Detail panel */}
      {selectedId && (
        <div className="w-[40%] min-w-[380px] h-[calc(100vh-3.5rem)] sticky top-14">
          <NoteDetail noteId={selectedId} source={selectedSource} onClose={closeDetail} />
        </div>
      )}
    </div>
  );
}
