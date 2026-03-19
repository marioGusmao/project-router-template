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
    <div className="flex gap-0 -m-8">
      {/* Table section */}
      <div className={`flex-1 min-w-0 ${selectedId ? 'w-[60%]' : 'w-full'}`}>
        {/* Filter bar */}
        <div className="sticky top-14 z-30 bg-zinc-950/90 backdrop-blur-sm px-8 py-4">
          <div className="bg-zinc-900/50 rounded-xl border border-zinc-800/40 p-3 flex items-center gap-3 flex-wrap">
            <select
              value={filterStatus}
              onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
              className="bg-zinc-800/80 border border-zinc-700/50 rounded-lg px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-colors"
            >
              <option value="">All statuses</option>
              {statuses.map((s) => (
                <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
              ))}
            </select>

            <select
              value={filterSource}
              onChange={(e) => { setFilterSource(e.target.value); setPage(1); }}
              className="bg-zinc-800/80 border border-zinc-700/50 rounded-lg px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-colors"
            >
              <option value="">All sources</option>
              {sources.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>

            <select
              value={filterProject}
              onChange={(e) => { setFilterProject(e.target.value); setPage(1); }}
              className="bg-zinc-800/80 border border-zinc-700/50 rounded-lg px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-colors"
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
              className="flex-1 min-w-[200px] bg-zinc-800/80 border border-zinc-700/50 rounded-lg px-3 py-1.5 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-colors"
            />

            <span className="text-[11px] text-zinc-500 font-medium tabular-nums">
              {total} note{total !== 1 ? 's' : ''}
            </span>
          </div>
        </div>

        {/* Table */}
        <div className="px-8 pb-8">
          <div className="bg-zinc-900/50 rounded-xl border border-zinc-800/40 overflow-hidden">
            {loading ? (
              <div className="p-6 space-y-2">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="h-10 bg-zinc-800/40 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : error ? (
              <div className="p-12 text-center text-zinc-500">{error}</div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-zinc-900">
                    <th className="text-left text-[11px] uppercase tracking-[0.08em] font-medium text-zinc-500 px-5 py-3">Title</th>
                    <th className="text-left text-[11px] uppercase tracking-[0.08em] font-medium text-zinc-500 px-5 py-3">Status</th>
                    <th className="text-left text-[11px] uppercase tracking-[0.08em] font-medium text-zinc-500 px-5 py-3">Project</th>
                    <th className="text-left text-[11px] uppercase tracking-[0.08em] font-medium text-zinc-500 px-5 py-3">Confidence</th>
                    <th className="text-left text-[11px] uppercase tracking-[0.08em] font-medium text-zinc-500 px-5 py-3">Source</th>
                    <th className="text-left text-[11px] uppercase tracking-[0.08em] font-medium text-zinc-500 px-5 py-3">Age</th>
                  </tr>
                </thead>
                <tbody>
                  {notes.map((note) => (
                    <tr
                      key={`${note.source}-${note.source_note_id}`}
                      onClick={() => selectNote(note)}
                      className={`border-t border-zinc-800/40 cursor-pointer hover:bg-zinc-800/30 transition-colors ${
                        selectedId === note.source_note_id ? 'bg-blue-500/10 border-l-2 border-l-blue-500' : ''
                      }`}
                    >
                      <td className="px-5 py-3 text-zinc-100 min-w-[300px]">
                        <span className="truncate block max-w-md">
                          {note.title || note.source_note_id}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        <StatusBadge status={note.status} />
                      </td>
                      <td className="px-5 py-3 text-xs">
                        {note.user_suggested_project && note.user_suggested_project !== note.project ? (
                          <span className="text-violet-400">
                            Suggested: {note.user_suggested_project}
                          </span>
                        ) : (
                          <span className="text-zinc-400">{note.project || '--'}</span>
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <ConfidenceBar value={note.confidence ?? 0} />
                      </td>
                      <td className="px-5 py-3 font-mono text-xs text-zinc-500">
                        {note.source}
                      </td>
                      <td className={`px-5 py-3 text-xs tabular-nums ${ageColor(note.queue_age_seconds)}`}>
                        {formatAge(note.queue_age_seconds)}
                      </td>
                    </tr>
                  ))}
                  {notes.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-5 py-16 text-center text-zinc-500">
                        No notes found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-5 py-3 border-t border-zinc-800/40">
                <span className="text-[11px] text-zinc-500 tabular-nums">
                  Showing {(page - 1) * perPage + 1}--{Math.min(page * perPage, total)} of {total}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page <= 1}
                    className="px-3 py-1.5 text-xs font-medium bg-zinc-800/60 border border-zinc-700/50 rounded-lg text-zinc-300 hover:bg-zinc-700/60 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    Previous
                  </button>
                  <span className="text-xs text-zinc-500 tabular-nums px-2">
                    {page} / {totalPages}
                  </span>
                  <button
                    onClick={() => setPage(Math.min(totalPages, page + 1))}
                    disabled={page >= totalPages}
                    className="px-3 py-1.5 text-xs font-medium bg-zinc-800/60 border border-zinc-700/50 rounded-lg text-zinc-300 hover:bg-zinc-700/60 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
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
