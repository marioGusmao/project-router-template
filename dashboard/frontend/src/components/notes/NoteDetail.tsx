import { useState, useEffect } from 'react';
import Markdown from 'react-markdown';
import { getNote, suggestProject, getProjects, type NoteDetail as NoteDetailType, type Project } from '../../lib/api';
import { StatusBadge } from '../StatusBadge';
import { ConfidenceBar } from '../ConfidenceBar';

interface Props {
  noteId: string;
  source: string;
  onClose: () => void;
}

function formatDate(iso: string | undefined): string {
  if (!iso) return '--';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function NoteDetail({ noteId, source, onClose }: Props) {
  const [note, setNote] = useState<NoteDetailType | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [suggestedProject, setSuggestedProject] = useState('');
  const [saving, setSaving] = useState(false);
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
    try {
      await suggestProject(noteId, source, suggestedProject);
      setNote({ ...note, user_suggested_project: suggestedProject });
    } catch {
      // silent
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full bg-zinc-900 border-l border-zinc-800 p-6 space-y-4">
        <div className="h-6 bg-zinc-800 rounded animate-pulse w-3/4" />
        <div className="h-4 bg-zinc-800 rounded animate-pulse w-1/2" />
        <div className="h-32 bg-zinc-800 rounded animate-pulse" />
      </div>
    );
  }

  if (error || !note) {
    return (
      <div className="h-full bg-zinc-900 border-l border-zinc-800 p-6">
        <div className="flex justify-between items-center mb-4">
          <span className="text-zinc-400">Error</span>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">&times;</button>
        </div>
        <div className="text-zinc-500">{error ?? 'Note not found'}</div>
      </div>
    );
  }

  const candidates = note.candidate_projects ?? [];

  return (
    <div className="h-full bg-zinc-900 border-l border-zinc-800 overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-zinc-900/95 backdrop-blur-sm border-b border-zinc-800 p-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h2 className="text-xl font-semibold text-zinc-100 leading-tight">
            {note.title || note.source_note_id}
          </h2>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 text-xl leading-none flex-shrink-0 mt-1"
          >
            &times;
          </button>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <StatusBadge status={note.status} />
          <span className="font-mono text-xs text-zinc-500">{note.source_note_id}</span>
          <span className="text-xs text-zinc-500">{formatDate(note.created_at)}</span>
        </div>
      </div>

      <div className="p-4 space-y-4">
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
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded-md px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:border-blue-500"
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
            className="px-4 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded-md disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>

        {/* Content */}
        {note.body && (
          <div className="bg-zinc-800/50 border border-zinc-700/50 rounded-lg p-4">
            <div className="prose prose-invert prose-sm max-w-none text-zinc-300 [&_h1]:text-zinc-100 [&_h2]:text-zinc-100 [&_h3]:text-zinc-200 [&_strong]:text-zinc-200 [&_a]:text-blue-400 [&_code]:text-amber-300 [&_code]:bg-zinc-700/50 [&_code]:px-1 [&_code]:rounded">
              <Markdown>{note.body}</Markdown>
            </div>
          </div>
        )}

        {/* Classification (collapsible) */}
        <div className="border border-zinc-800 rounded-lg">
          <button
            onClick={() => setShowClassification(!showClassification)}
            className="w-full flex items-center justify-between px-4 py-2.5 text-sm text-zinc-400 hover:text-zinc-300"
          >
            <span className="uppercase tracking-wider text-xs">Classification</span>
            <svg
              className={`w-4 h-4 transition-transform ${showClassification ? 'rotate-180' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {showClassification && (
            <div className="px-4 pb-4 space-y-3">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-zinc-500 text-xs">Capture Kind</span>
                  <div className="text-zinc-300">{note.capture_kind || '--'}</div>
                </div>
                <div>
                  <span className="text-zinc-500 text-xs">Intent</span>
                  <div className="text-zinc-300">{note.intent || '--'}</div>
                </div>
                <div>
                  <span className="text-zinc-500 text-xs">Destination</span>
                  <div className="text-zinc-300">{note.destination || '--'}</div>
                </div>
                <div>
                  <span className="text-zinc-500 text-xs">Confidence</span>
                  <ConfidenceBar value={note.confidence ?? 0} />
                </div>
              </div>
              {candidates.length > 0 && (
                <div>
                  <span className="text-zinc-500 text-xs">Candidates</span>
                  <div className="mt-1 space-y-1">
                    {candidates.map((c) => (
                      <div key={c.project} className="flex items-center justify-between text-sm">
                        <span className="text-zinc-300">{c.project}</span>
                        <span className="font-mono text-xs text-zinc-500">
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
        <div className="border border-zinc-800 rounded-lg">
          <button
            onClick={() => setShowMetadata(!showMetadata)}
            className="w-full flex items-center justify-between px-4 py-2.5 text-sm text-zinc-400 hover:text-zinc-300"
          >
            <span className="uppercase tracking-wider text-xs">Metadata</span>
            <svg
              className={`w-4 h-4 transition-transform ${showMetadata ? 'rotate-180' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {showMetadata && (
            <div className="px-4 pb-4 space-y-3">
              {note.tags && note.tags.length > 0 && (
                <div>
                  <span className="text-zinc-500 text-xs">Keywords</span>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {note.tags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex px-2 py-0.5 rounded-full bg-zinc-800 border border-zinc-700 text-xs text-zinc-300"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {note.thread_id && (
                <div className="text-sm">
                  <span className="text-zinc-500 text-xs">Thread</span>
                  <div className="font-mono text-xs text-zinc-400">{note.thread_id}</div>
                </div>
              )}
              {note.file_path && (
                <div className="text-sm">
                  <span className="text-zinc-500 text-xs">File Path</span>
                  <div className="font-mono text-xs text-zinc-400 break-all">{note.file_path}</div>
                </div>
              )}
              {note.source && (
                <div className="text-sm">
                  <span className="text-zinc-500 text-xs">Source</span>
                  <div className="font-mono text-xs text-zinc-400">{note.source}</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
