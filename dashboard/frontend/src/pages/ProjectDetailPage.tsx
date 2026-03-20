import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getNotes, getProjects, noteHref, noteKey, type NoteListItem, type Project } from '../lib/api';
import { StatusBadge } from '../components/StatusBadge';
import { ConfidenceBar } from '../components/ConfidenceBar';

type Tab = 'active' | 'review' | 'archived';

const TAB_FILTERS: Record<Tab, string> = {
  active: 'normalized,classified,compiled',
  review: 'needs_review,ambiguous,pending_project',
  archived: 'dispatched,processed',
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
      const res = await getNotes({ project: key, status: TAB_FILTERS[tab], per_page: '100' });
      setNotes(res.notes ?? []);
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
      <div className="space-y-5">
        <div className="card animate-pulse" style={{ height: 100 }} />
        <div className="card animate-pulse" style={{ height: 280 }} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card" style={{ padding: 48, textAlign: 'center', color: '#a1a1aa' }}>
        Failed to load project: {error}
      </div>
    );
  }

  if (!project) {
    return (
      <div className="card" style={{ padding: 48, textAlign: 'center' }}>
        <div className="text-zinc-500" style={{ marginBottom: 8 }}>Project not found: {key}</div>
        <Link to="/projects" className="text-sm text-blue-400 hover:text-blue-300 transition-colors">
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
    <div className="space-y-5">
      {/* Project header */}
      <div className="card animate-in" style={{ padding: 24 }}>
        <div className="flex items-start justify-between" style={{ marginBottom: 8 }}>
          <div>
            <Link
              to="/projects"
              className="text-zinc-500 hover:text-zinc-400 transition-colors inline-block"
              style={{ fontSize: 12, marginBottom: 4 }}
            >
              &larr; Projects
            </Link>
            <h2 className="text-2xl font-bold text-zinc-100 tracking-tight">
              {project.display_name || project.key}
            </h2>
          </div>
          {project.language && (
            <span
              className="text-blue-400 font-medium"
              style={{
                fontSize: 11,
                background: 'rgba(59,130,246,0.1)',
                padding: '3px 10px',
                borderRadius: 9999,
              }}
            >
              {project.language}
            </span>
          )}
        </div>
        {project.keywords && project.keywords.length > 0 && (
          <div className="flex flex-wrap gap-1.5" style={{ marginTop: 8 }}>
            {project.keywords.map((kw) => (
              <span
                key={kw}
                className="inline-flex font-mono text-zinc-400"
                style={{
                  fontSize: 11,
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.04)',
                  padding: '4px 8px',
                  borderRadius: 6,
                }}
              >
                {kw}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div
        className="flex gap-0"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
      >
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className="text-sm font-medium transition-colors"
            style={{
              padding: '10px 20px',
              borderBottom: tab === t.key ? '2px solid #3b82f6' : '2px solid transparent',
              color: tab === t.key ? '#60a5fa' : '#71717a',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Notes table */}
      <div className="card overflow-hidden">
        {notesLoading ? (
          <div style={{ padding: 24 }} className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="animate-pulse rounded-lg"
                style={{ height: 44, background: 'rgba(255,255,255,0.03)' }}
              />
            ))}
          </div>
        ) : notes.length === 0 ? (
          <div className="text-center text-zinc-500" style={{ padding: 48 }}>
            No {tab} notes for this project
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: 'rgba(255,255,255,0.02)' }}>
                <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Title</th>
                <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Status</th>
                <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Confidence</th>
                <th className="text-left font-semibold uppercase tracking-widest text-zinc-500" style={{ fontSize: 10, letterSpacing: '0.12em', padding: '12px 20px' }}>Source</th>
              </tr>
            </thead>
            <tbody>
              {notes.map((note) => (
                <tr
                  key={noteKey(note.source, note.source_note_id, note.source_project)}
                  className="table-row-hover"
                  style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}
                >
                  <td className="text-zinc-100 truncate" style={{ padding: '14px 20px', maxWidth: 400 }}>
                    <Link
                      to={noteHref(note)}
                      className="hover:text-blue-400 transition-colors"
                    >
                      {note.title || note.source_note_id}
                    </Link>
                  </td>
                  <td style={{ padding: '14px 20px' }}>
                    <StatusBadge status={note.status} />
                  </td>
                  <td style={{ padding: '14px 20px' }}>
                    <ConfidenceBar value={note.confidence ?? 0} />
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
