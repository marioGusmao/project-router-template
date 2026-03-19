import { useState, useEffect } from 'react';
import Markdown from 'react-markdown';
import { getNote, suggestProject, decideNote, getProjects, type NoteDetail as NoteDetailType, type Project } from '../../lib/api';
import { StatusBadge } from '../StatusBadge';
import { ConfidenceBar } from '../ConfidenceBar';
import { triggerUndo } from '../layout/UndoSnackbar';

interface Props {
  noteId: string;
  source: string;
  onClose: () => void;
  onProjectSuggested?: (noteId: string, source: string, project: string) => void;
}

function formatDate(iso: string | undefined): string {
  if (!iso) return '--';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function NoteDetail({ noteId, source, onClose, onProjectSuggested }: Props) {
  const [note, setNote] = useState<NoteDetailType | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [suggestedProject, setSuggestedProject] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [deciding, setDeciding] = useState(false);
  const [decideDone, setDecideDone] = useState<string | null>(null);
  const [showClassification, setShowClassification] = useState(false);
  const [showMetadata, setShowMetadata] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [n, p] = await Promise.all([
          getNote(noteId, source),
          getProjects(),
        ]);
        setNote(n);
        setProjects(p.projects ?? []);
        setSuggestedProject(n.user_suggested_project ?? '');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [noteId, source]);

  const handleSuggest = async () => {
    if (!suggestedProject || !note) return;
    setSaving(true);
    setSaved(false);
    const previousProject = note.user_suggested_project || null;
    try {
      await suggestProject(noteId, source, suggestedProject);
      setNote({ ...note, user_suggested_project: suggestedProject });
      onProjectSuggested?.(noteId, source, suggestedProject);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      triggerUndo(`Suggested "${suggestedProject}" for ${noteId}`, async () => {
        try {
          if (previousProject) {
            await suggestProject(noteId, source, previousProject);
            setNote(prev => prev ? { ...prev, user_suggested_project: previousProject } : prev);
            setSuggestedProject(previousProject);
          } else {
            await suggestProject(noteId, source, '');
            setNote(prev => prev ? { ...prev, user_suggested_project: undefined } : prev);
            setSuggestedProject('');
          }
        } catch {
          // silent
        }
      });
    } catch {
      // silent
    } finally {
      setSaving(false);
    }
  };

  const handleDecide = async (decision: string) => {
    if (!note) return;
    const project = suggestedProject || note.project;
    if (decision === 'approve') {
      if (!project) return;
      if (!window.confirm(`Approve for ${project}? This is a canonical decision.`)) return;
    }
    setDeciding(true);
    setDecideDone(null);
    try {
      await decideNote(
        noteId,
        source,
        decision,
        decision === 'approve' ? project ?? undefined : undefined,
      );
      const refreshed = await getNote(noteId, source);
      setNote(refreshed);
      onProjectSuggested?.(noteId, source, refreshed.project ?? '');
      setDecideDone(decision);
      setTimeout(() => setDecideDone(null), 2000);
    } catch {
      // silent
    } finally {
      setDeciding(false);
    }
  };

  const selectStyle: React.CSSProperties = {
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: 8,
    padding: '6px 12px',
    fontSize: 13,
    color: '#e4e4e7',
    outline: 'none',
  };

  if (loading) {
    return (
      <div
        className="h-full space-y-4"
        style={{
          background: 'linear-gradient(135deg, rgba(24,24,27,0.95) 0%, rgba(39,39,42,0.6) 100%)',
          borderLeft: '1px solid rgba(255,255,255,0.06)',
          padding: 24,
        }}
      >
        <div className="animate-pulse rounded-lg" style={{ height: 24, width: '75%', background: 'rgba(255,255,255,0.05)' }} />
        <div className="animate-pulse rounded-lg" style={{ height: 16, width: '50%', background: 'rgba(255,255,255,0.03)' }} />
        <div className="animate-pulse rounded-lg" style={{ height: 128, background: 'rgba(255,255,255,0.03)' }} />
      </div>
    );
  }

  if (error || !note) {
    return (
      <div
        className="h-full"
        style={{
          background: 'linear-gradient(135deg, rgba(24,24,27,0.95) 0%, rgba(39,39,42,0.6) 100%)',
          borderLeft: '1px solid rgba(255,255,255,0.06)',
          padding: 24,
        }}
      >
        <div className="flex justify-between items-center" style={{ marginBottom: 16 }}>
          <span className="text-zinc-400">Error</span>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 transition-colors"
            style={{ fontSize: 20, lineHeight: 1 }}
          >
            &times;
          </button>
        </div>
        <div className="text-zinc-500">{error ?? 'Note not found'}</div>
      </div>
    );
  }

  const candidates = note.candidate_projects ?? [];

  return (
    <div
      className="h-full overflow-y-auto"
      style={{
        background: 'linear-gradient(135deg, rgba(24,24,27,0.95) 0%, rgba(39,39,42,0.6) 100%)',
        borderLeft: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      {/* Header */}
      <div
        className="sticky top-0 backdrop-blur-xl"
        style={{
          background: 'rgba(24,24,27,0.9)',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          padding: 20,
          zIndex: 10,
        }}
      >
        <div className="flex items-start justify-between gap-3" style={{ marginBottom: 10 }}>
          <h2 className="text-lg font-semibold text-zinc-100 leading-tight tracking-tight">
            {note.title || note.source_note_id}
          </h2>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 transition-colors flex-shrink-0"
            style={{ fontSize: 20, lineHeight: 1, marginTop: 2 }}
          >
            &times;
          </button>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <StatusBadge status={note.status} />
          <span className="font-mono text-zinc-500" style={{ fontSize: 11 }}>{note.source_note_id}</span>
          <span className="text-zinc-600" style={{ fontSize: 12 }}>{formatDate(note.created_at)}</span>
        </div>
      </div>

      <div style={{ padding: 20 }} className="space-y-5">
        {/* Project row */}
        <div className="flex items-center gap-3 flex-wrap">
          {note.project && (
            <span className="text-sm text-zinc-300">
              Assigned: <span className="font-medium text-zinc-100">{note.project}</span>
            </span>
          )}
          {note.user_suggested_project && note.user_suggested_project !== note.project && (
            <span className="text-sm text-violet-400">
              Suggested: {note.user_suggested_project}
            </span>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <select
            value={suggestedProject}
            onChange={(e) => setSuggestedProject(e.target.value)}
            className="flex-1"
            style={selectStyle}
          >
            <option value="">Suggest project...</option>
            {projects.map((p) => (
              <option key={p.key} value={p.key}>
                {p.display_name || p.key}
              </option>
            ))}
          </select>
          <button
            onClick={handleSuggest}
            disabled={!suggestedProject || saving}
            className="text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            style={{
              padding: '6px 16px',
              background: '#3b82f6',
              borderRadius: 8,
              border: 'none',
            }}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
          {saved && (
            <span className="text-emerald-400 font-medium animate-in" style={{ fontSize: 12 }}>
              Saved
            </span>
          )}
        </div>

        {/* Quick Actions */}
        <div>
          <span
            className="uppercase tracking-widest font-semibold text-zinc-400 block"
            style={{ fontSize: 10, letterSpacing: '0.12em', marginBottom: 8 }}
          >
            Quick Actions
          </span>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => handleDecide('approve')}
              disabled={deciding || !(suggestedProject || note.project)}
              className="rounded-lg px-3 py-1.5 text-xs font-medium transition-all text-white disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ background: '#059669' }}
              onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.background = '#10b981'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = '#059669'; }}
            >
              Approve &#x2713;
            </button>
            <button
              onClick={() => handleDecide('reject')}
              disabled={deciding}
              className="rounded-lg px-3 py-1.5 text-xs font-medium transition-all text-rose-400 border border-rose-600/30 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ background: 'rgba(225,29,72,0.2)' }}
              onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.background = 'rgba(225,29,72,0.3)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(225,29,72,0.2)'; }}
            >
              Reject &#x2715;
            </button>
            <button
              onClick={() => handleDecide('ambiguous')}
              disabled={deciding}
              className="rounded-lg px-3 py-1.5 text-xs font-medium transition-all text-orange-400 border border-orange-600/30 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ background: 'rgba(234,88,12,0.2)' }}
              onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.background = 'rgba(234,88,12,0.3)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(234,88,12,0.2)'; }}
            >
              Ambiguous ?
            </button>
            <button
              onClick={() => handleDecide('defer')}
              disabled={deciding}
              className="rounded-lg px-3 py-1.5 text-xs font-medium transition-all text-sky-400 border border-sky-600/30 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ background: 'rgba(14,165,233,0.2)' }}
              onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.background = 'rgba(14,165,233,0.3)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(14,165,233,0.2)'; }}
            >
              Rever mais tarde
            </button>
            <button
              onClick={() => handleDecide('needs-review')}
              disabled={deciding}
              className="rounded-lg px-3 py-1.5 text-xs font-medium transition-all text-amber-400 border border-amber-600/30 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ background: 'rgba(217,119,6,0.2)' }}
              onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.background = 'rgba(217,119,6,0.3)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(217,119,6,0.2)'; }}
            >
              Needs Review
            </button>
            <button
              onClick={() => handleDecide('pending-project')}
              disabled={deciding}
              className="rounded-lg px-3 py-1.5 text-xs font-medium transition-all text-zinc-400 border border-zinc-600/30 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ background: 'rgba(82,82,91,0.2)' }}
              onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.background = 'rgba(82,82,91,0.3)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(82,82,91,0.2)'; }}
            >
              Pending Project
            </button>
          </div>
          {decideDone && (
            <span className="text-emerald-400 font-medium animate-in block" style={{ fontSize: 12, marginTop: 6 }}>
              Done ({decideDone})
            </span>
          )}
        </div>

        {/* Content */}
        {note.body && (
          <div
            className="rounded-xl"
            style={{
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(255,255,255,0.04)',
              padding: 20,
            }}
          >
            <div className="prose prose-invert prose-sm max-w-none text-zinc-300 [&_h1]:text-zinc-100 [&_h2]:text-zinc-100 [&_h3]:text-zinc-200 [&_strong]:text-zinc-200 [&_a]:text-blue-400 [&_code]:text-amber-300 [&_code]:bg-zinc-700/50 [&_code]:px-1 [&_code]:rounded">
              <Markdown>{note.body}</Markdown>
            </div>
          </div>
        )}

        {/* Files */}
        {(() => {
          const filePath = note.file_path;
          if (!filePath) return null;

          const ext = filePath.split('.').pop()?.toLowerCase() ?? '';
          const filename = filePath.split('/').pop() ?? '';
          const fileUrl = `/api/notes/${note.source_note_id}/file/${encodeURIComponent(filename)}?source=${note.source}`;

          const isImage = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext);
          const isAudio = ['mp3', 'wav', 'ogg', 'm4a', 'aac', 'flac', 'webm'].includes(ext);
          const isPdf = ext === 'pdf';

          if (!isImage && !isAudio && !isPdf) return null;

          return (
            <div
              className="rounded-xl"
              style={{
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid rgba(255,255,255,0.04)',
                padding: 20,
              }}
            >
              <span
                className="uppercase tracking-widest font-semibold text-zinc-400 block"
                style={{ fontSize: 10, letterSpacing: '0.12em', marginBottom: 12 }}
              >
                Files
              </span>
              {isImage && (
                <img
                  src={fileUrl}
                  alt={filename}
                  className="rounded-lg"
                  style={{ maxWidth: '100%', maxHeight: 400, objectFit: 'contain' }}
                />
              )}
              {isAudio && (
                <audio controls style={{ width: '100%' }}>
                  <source src={fileUrl} />
                  Your browser does not support the audio element.
                </audio>
              )}
              {isPdf && (
                <div>
                  <embed
                    src={fileUrl}
                    type="application/pdf"
                    style={{ width: '100%', height: 400, borderRadius: 8 }}
                  />
                  <a
                    href={fileUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:text-blue-300 transition-colors"
                    style={{ fontSize: 12, marginTop: 8, display: 'inline-block' }}
                  >
                    Open PDF in new tab
                  </a>
                </div>
              )}
              <div className="font-mono text-zinc-500" style={{ fontSize: 11, marginTop: 8 }}>
                {filename}
              </div>
            </div>
          );
        })()}

        {/* Classification (collapsible) */}
        <div
          className="rounded-xl overflow-hidden"
          style={{ border: '1px solid rgba(255,255,255,0.06)' }}
        >
          <button
            onClick={() => setShowClassification(!showClassification)}
            className="w-full flex items-center justify-between text-zinc-400 hover:text-zinc-300 transition-colors"
            style={{ padding: '12px 16px' }}
          >
            <span className="uppercase tracking-widest font-semibold" style={{ fontSize: 10, letterSpacing: '0.12em' }}>
              Classification
            </span>
            <svg
              className={`w-4 h-4 transition-transform duration-200 ${showClassification ? 'rotate-180' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {showClassification && (
            <div style={{ padding: '0 16px 16px' }} className="space-y-3">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-zinc-500" style={{ fontSize: 11 }}>Capture Kind</span>
                  <div className="text-zinc-300">{note.capture_kind || '--'}</div>
                </div>
                <div>
                  <span className="text-zinc-500" style={{ fontSize: 11 }}>Intent</span>
                  <div className="text-zinc-300">{note.intent || '--'}</div>
                </div>
                <div>
                  <span className="text-zinc-500" style={{ fontSize: 11 }}>Destination</span>
                  <div className="text-zinc-300">{note.destination || '--'}</div>
                </div>
                <div>
                  <span className="text-zinc-500" style={{ fontSize: 11 }}>Confidence</span>
                  <ConfidenceBar value={note.confidence ?? 0} />
                </div>
              </div>
              {candidates.length > 0 && (
                <div>
                  <span className="text-zinc-500" style={{ fontSize: 11 }}>Candidates</span>
                  <div className="space-y-1" style={{ marginTop: 4 }}>
                    {candidates.map((c) => (
                      <div key={c.project} className="flex items-center justify-between text-sm">
                        <span className="text-zinc-300">{c.project}</span>
                        <span className="font-mono text-zinc-500" style={{ fontSize: 11 }}>
                          {Math.round(c.score * 100)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Metadata (collapsible) */}
        <div
          className="rounded-xl overflow-hidden"
          style={{ border: '1px solid rgba(255,255,255,0.06)' }}
        >
          <button
            onClick={() => setShowMetadata(!showMetadata)}
            className="w-full flex items-center justify-between text-zinc-400 hover:text-zinc-300 transition-colors"
            style={{ padding: '12px 16px' }}
          >
            <span className="uppercase tracking-widest font-semibold" style={{ fontSize: 10, letterSpacing: '0.12em' }}>
              Metadata
            </span>
            <svg
              className={`w-4 h-4 transition-transform duration-200 ${showMetadata ? 'rotate-180' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {showMetadata && (
            <div style={{ padding: '0 16px 16px' }} className="space-y-3">
              {note.tags && note.tags.length > 0 && (
                <div>
                  <span className="text-zinc-500" style={{ fontSize: 11 }}>Keywords</span>
                  <div className="flex flex-wrap gap-1.5" style={{ marginTop: 4 }}>
                    {note.tags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex text-zinc-300 font-mono"
                        style={{
                          fontSize: 11,
                          background: 'rgba(255,255,255,0.04)',
                          border: '1px solid rgba(255,255,255,0.04)',
                          padding: '3px 8px',
                          borderRadius: 6,
                        }}
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {note.thread_id && (
                <div className="text-sm">
                  <span className="text-zinc-500" style={{ fontSize: 11 }}>Thread</span>
                  <div className="font-mono text-zinc-400" style={{ fontSize: 12 }}>{note.thread_id}</div>
                </div>
              )}
              {note.file_path && (
                <div className="text-sm">
                  <span className="text-zinc-500" style={{ fontSize: 11 }}>File Path</span>
                  <div className="font-mono text-zinc-400 break-all" style={{ fontSize: 12 }}>{note.file_path}</div>
                </div>
              )}
              {note.source && (
                <div className="text-sm">
                  <span className="text-zinc-500" style={{ fontSize: 11 }}>Source</span>
                  <div className="font-mono text-zinc-400" style={{ fontSize: 12 }}>{note.source}</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
