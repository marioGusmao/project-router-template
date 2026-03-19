import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getNotes, getProjects, type NoteListItem, type Project } from '../lib/api';
import { StatusBadge } from '../components/StatusBadge';
import { ConfidenceBar } from '../components/ConfidenceBar';

type Tab = 'active' | 'review' | 'archived';

const TAB_FILTERS: Record<Tab, string[]> = {
  active: ['normalized', 'classified', 'compiled'],
  review: ['needs_review', 'ambiguous', 'pending_project'],
  archived: ['dispatched', 'processed'],
};

export function ProjectDetailPage() {
  const { key } = useParams<{ key: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [notes, setNotes] = useState<NoteListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [notesLoading, setNotesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('active');

  useEffect(() => {
    async function loadProject() {
      try {
        const res = await getProjects();
        const p = (res.projects ?? []).find((pr) => pr.key === key);
        setProject(p ?? null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    }
    loadProject();
  }, [key]);

  const loadNotes = useCallback(async () => {
    if (!key) return;
    setNotesLoading(true);
    try {
      const statuses = TAB_FILTERS[tab];
      const allNotes: NoteListItem[] = [];
      for (const status of statuses) {
        const res = await getNotes({ project: key, status, per_page: '100' });
        allNotes.push(...(res.notes ?? []));
      }
      setNotes(allNotes);
    } catch {
      // silent
    } finally {
      setNotesLoading(false);
    }
  }, [key, tab]);

  useEffect(() => {
    loadNotes();
  }, [loadNotes]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-24 bg-zinc-900 border border-zinc-800 rounded-lg animate-pulse" />
        <div className="h-64 bg-zinc-900 border border-zinc-800 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-8 text-center text-zinc-400">
        Failed to load project: {error}
      </div>
    );
  }

  if (!project) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-8 text-center">
        <div className="text-zinc-500 mb-2">Project not found: {key}</div>
        <Link to="/projects" className="text-sm text-blue-400 hover:text-blue-300">
          Back to projects
        </Link>
      </div>
    );
  }

  const tabs: Array<{ key: Tab; label: string }> = [
    { key: 'active', label: 'Active' },
    { key: 'review', label: 'In Review' },
    { key: 'archived', label: 'Archived' },
  ];

  return (
    <div className="space-y-4">
      {/* Project header */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <div className="flex items-start justify-between mb-2">
          <div>
            <Link to="/projects" className="text-xs text-zinc-500 hover:text-zinc-400 mb-1 inline-block">
              &larr; Projects
            </Link>
            <h2 className="text-xl font-semibold text-zinc-100">
              {project.display_name || project.key}
            </h2>
          </div>
          {project.language && (
            <span className="text-xs bg-zinc-800 border border-zinc-700 text-zinc-400 px-2 py-0.5 rounded">
              {project.language}
            </span>
          )}
        </div>
        {project.keywords && project.keywords.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {project.keywords.map((kw) => (
              <span
                key={kw}
                className="inline-flex px-2 py-0.5 rounded-full bg-zinc-800 border border-zinc-700 text-xs text-zinc-300"
              >
                {kw}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-zinc-800">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-zinc-500 hover:text-zinc-300'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Notes table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        {notesLoading ? (
          <div className="p-6 space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-10 bg-zinc-800 rounded animate-pulse" />
            ))}
          </div>
        ) : notes.length === 0 ? (
          <div className="p-8 text-center text-zinc-500">
            No {tab} notes for this project
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-zinc-500 uppercase tracking-wider">
                <th className="px-4 py-2">Title</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Confidence</th>
                <th className="px-4 py-2">Source</th>
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
                    <Link
                      to={`/notes?id=${note.source_note_id}&source=${note.source}`}
                      className="hover:text-blue-400"
                    >
                      {note.title || note.source_note_id}
                    </Link>
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={note.status} />
                  </td>
                  <td className="px-4 py-2.5">
                    <ConfidenceBar value={note.confidence ?? 0} />
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs text-zinc-400">
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
