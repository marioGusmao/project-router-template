import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getNotes, getProjects, getStatus, suggestProject, type NoteListItem, type Project, type StatusResponse } from '../lib/api';
import { StatusBadge } from '../components/StatusBadge';
import { ConfidenceBar } from '../components/ConfidenceBar';
import { NoteDetail } from '../components/notes/NoteDetail';
import { useKeyboard } from '../hooks/useKeyboard';
import { SourceIcon } from '../components/SourceIcon';

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

  const [focusedIndex, setFocusedIndex] = useState(-1);

  // Batch selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const lastSelectedIndex = useRef<number | null>(null);

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

  const handleProjectSuggested = (noteId: string, _source: string, project: string) => {
    setNotes((prev) =>
      prev.map((n) =>
        n.source_note_id === noteId ? { ...n, user_suggested_project: project } : n,
      ),
    );
  };

  const handleDecided = (noteId: string, _source: string, _decision: string) => {
    setNotes((prev) => prev.filter((n) => n.source_note_id !== noteId));
    setTotal((prev) => Math.max(0, prev - 1));
    closeDetail();
  };

  // Reset focused index and selection when notes change
  useEffect(() => {
    setFocusedIndex(-1);
    setSelectedIds(new Set());
    lastSelectedIndex.current = null;
  }, [notes]);

  // Batch selection handlers
  const toggleSelect = useCallback((idx: number, shiftKey: boolean) => {
    const id = notes[idx]?.source_note_id;
    if (!id) return;

    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (shiftKey && lastSelectedIndex.current !== null) {
        const lo = Math.min(lastSelectedIndex.current, idx);
        const hi = Math.max(lastSelectedIndex.current, idx);
        for (let i = lo; i <= hi; i++) {
          next.add(notes[i].source_note_id);
        }
      } else if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
    lastSelectedIndex.current = idx;
  }, [notes]);

  const toggleSelectAll = useCallback(() => {
    setSelectedIds((prev) => {
      if (prev.size === notes.length) return new Set();
      return new Set(notes.map((n) => n.source_note_id));
    });
  }, [notes]);

  const handleBulkSuggest = useCallback(async (project: string) => {
    if (!project) return;
    for (const id of selectedIds) {
      const note = notes.find((n) => n.source_note_id === id);
      if (note) {
        await suggestProject(id, note.source, project);
      }
    }
    setSelectedIds(new Set());
    lastSelectedIndex.current = null;
    loadNotes();
  }, [selectedIds, notes, loadNotes]);

  const keyboardHandlers = useMemo(() => ({
    'j': () => {
      setFocusedIndex((prev) => Math.min(prev + 1, notes.length - 1));
    },
    'k': () => {
      setFocusedIndex((prev) => Math.max(prev - 1, 0));
    },
    'enter': () => {
      if (focusedIndex >= 0 && focusedIndex < notes.length) {
        selectNote(notes[focusedIndex]);
      }
    },
    'escape': () => {
      if (selectedId) {
        closeDetail();
      } else {
        setFocusedIndex(-1);
      }
    },
    'p': () => {
      if (focusedIndex >= 0 && focusedIndex < notes.length && !selectedId) {
        selectNote(notes[focusedIndex]);
      }
    },
  }), [notes, focusedIndex, selectedId]);

  useKeyboard(keyboardHandlers);

  const totalPages = Math.ceil(total / perPage);

  const statuses = [
    'normalized', 'classified', 'needs_review', 'ambiguous',
    'pending_project', 'dispatched', 'processed',
  ];

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
    <div className="flex gap-0" style={{ margin: -32 }}>
      {/* Table section */}
      <div className={`flex-1 min-w-0 ${selectedId ? 'w-3/5' : 'w-full'}`}>
        {/* Filter bar */}
        <div
          className="sticky z-30 backdrop-blur-sm"
          style={{ top: 56, padding: '16px 32px', background: 'rgba(10,10,11,0.9)' }}
        >
          <div
            className="card flex items-center gap-3 flex-wrap"
            style={{ padding: 14 }}
          >
            <select
              value={filterStatus}
              onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
              style={selectStyle}
            >
              <option value="">All statuses</option>
              {statuses.map((s) => (
                <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
              ))}
            </select>

            <select
              value={filterSource}
              onChange={(e) => { setFilterSource(e.target.value); setPage(1); }}
              style={selectStyle}
            >
              <option value="">All sources</option>
              {sources.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>

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

            <div className="flex-1" style={{ minWidth: 200, position: 'relative' }}>
              <svg
                className="absolute text-zinc-600"
                style={{ left: 10, top: '50%', transform: 'translateY(-50%)', width: 14, height: 14 }}
                fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') { setPage(1); loadNotes(); } }}
                placeholder="Search notes..."
                style={{
                  ...selectStyle,
                  width: '100%',
                  paddingLeft: 32,
                }}
              />
            </div>

            <span className="text-zinc-500 font-medium tabular-nums" style={{ fontSize: 11 }}>
              {total} note{total !== 1 ? 's' : ''}
            </span>
          </div>
        </div>

        {/* Table */}
        <div style={{ padding: '0 32px 32px' }}>
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
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr style={{ background: 'rgba(255,255,255,0.02)' }}>
                    <th style={{ padding: '12px 0 12px 20px', width: 36 }}>
                      <input
                        type="checkbox"
                        checked={notes.length > 0 && selectedIds.size === notes.length}
                        ref={(el) => { if (el) el.indeterminate = selectedIds.size > 0 && selectedIds.size < notes.length; }}
                        onChange={toggleSelectAll}
                        className="accent-blue-500 cursor-pointer"
                        style={{ width: 15, height: 15 }}
                      />
                    </th>
                    <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Title</th>
                    <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Status</th>
                    <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Project</th>
                    <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Confidence</th>
                    <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Source</th>
                    <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Age</th>
                  </tr>
                </thead>
                <tbody>
                  {notes.map((note, idx) => (
                    <tr
                      key={`${note.source}-${note.source_note_id}`}
                      onClick={() => { setFocusedIndex(idx); selectNote(note); }}
                      className={`table-row-hover cursor-pointer ${
                        selectedId === note.source_note_id ? 'bg-blue-500/5' : ''
                      } ${focusedIndex === idx && selectedId !== note.source_note_id ? 'bg-zinc-800/40' : ''}`}
                      style={{
                        borderTop: '1px solid rgba(255,255,255,0.04)',
                        boxShadow:
                          selectedId === note.source_note_id
                            ? 'inset 3px 0 0 0 #3b82f6'
                            : focusedIndex === idx
                              ? 'inset 3px 0 0 0 rgba(161,161,170,0.4)'
                              : undefined,
                      }}
                    >
                      <td style={{ padding: '14px 0 14px 20px', width: 36 }} onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedIds.has(note.source_note_id)}
                          onChange={() => {/* handled by onClick */}}
                          onClick={(e) => { toggleSelect(idx, e.shiftKey); }}
                          className="accent-blue-500 cursor-pointer"
                          style={{ width: 15, height: 15 }}
                        />
                      </td>
                      <td style={{ padding: '14px 20px', minWidth: 300 }} className="text-zinc-100">
                        <div className="flex items-center gap-2.5">
                          <SourceIcon source={note.source} />
                          <span className="truncate block" style={{ maxWidth: 380 }}>
                            {note.title || note.source_note_id}
                          </span>
                        </div>
                      </td>
                      <td style={{ padding: '14px 20px' }}>
                        <StatusBadge status={note.status} />
                      </td>
                      <td style={{ padding: '14px 20px', fontSize: 12 }}>
                        {note.user_suggested_project && note.user_suggested_project !== note.project ? (
                          <span className="text-violet-400">
                            Suggested: {note.user_suggested_project}
                          </span>
                        ) : (
                          <span className="text-zinc-400">{note.project || '--'}</span>
                        )}
                      </td>
                      <td style={{ padding: '14px 20px' }}>
                        <ConfidenceBar value={note.confidence ?? 0} />
                      </td>
                      <td className="font-mono text-zinc-500" style={{ padding: '14px 20px', fontSize: 12 }}>
                        {note.source}
                      </td>
                      <td className={`tabular-nums ${ageColor(note.queue_age_seconds)}`} style={{ padding: '14px 20px', fontSize: 12 }}>
                        {formatAge(note.queue_age_seconds)}
                      </td>
                    </tr>
                  ))}
                  {notes.length === 0 && (
                    <tr>
                      <td colSpan={7} className="text-center text-zinc-500" style={{ padding: '64px 20px' }}>
                        No notes found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div
                className="flex items-center justify-between"
                style={{ padding: '12px 20px', borderTop: '1px solid rgba(255,255,255,0.04)' }}
              >
                <span className="text-zinc-500 tabular-nums" style={{ fontSize: 11 }}>
                  Showing {(page - 1) * perPage + 1}--{Math.min(page * perPage, total)} of {total}
                </span>
                <div className="flex items-center gap-2">
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
                    Previous
                  </button>
                  <span className="text-zinc-500 tabular-nums" style={{ fontSize: 12, padding: '0 8px' }}>
                    {page} / {totalPages}
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
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Detail panel */}
      {selectedId && (
        <div className="min-w-96 sticky" style={{ width: '40%', top: 56, height: 'calc(100vh - 56px)' }}>
          <NoteDetail noteId={selectedId} source={selectedSource} onClose={closeDetail} onProjectSuggested={handleProjectSuggested} onDecided={handleDecided} />
        </div>
      )}

      {/* Floating batch action bar */}
      {selectedIds.size > 0 && (
        <div
          className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-4 px-5 py-3 rounded-xl border border-white/[0.08] backdrop-blur-xl shadow-2xl"
          style={{ background: 'linear-gradient(135deg, rgba(24,24,27,0.95), rgba(39,39,42,0.9))', marginLeft: 120 }}
        >
          <span className="text-sm text-zinc-300 font-medium">{selectedIds.size} selected</span>
          <select
            className="bg-white/[0.04] border border-white/[0.08] rounded-lg text-sm text-zinc-200 px-3 py-1.5"
            onChange={async (e) => {
              await handleBulkSuggest(e.target.value);
            }}
            value=""
          >
            <option value="">Suggest project...</option>
            {projects.map(p => <option key={p.key} value={p.key}>{p.display_name || p.key}</option>)}
          </select>
          <button onClick={() => setSelectedIds(new Set())} className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors">
            Clear
          </button>
        </div>
      )}
    </div>
  );
}
