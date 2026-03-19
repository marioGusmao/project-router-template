import { useState, useEffect } from 'react';
import { getTriageItems, type TriageItem } from '../lib/api';
import { StatusBadge } from '../components/StatusBadge';
import { SourceIcon } from '../components/SourceIcon';
import { ConfidenceBar } from '../components/ConfidenceBar';
import { NoteDetail } from '../components/notes/NoteDetail';

interface Swimlane {
  key: string;
  label: string;
  color: string;
  items: TriageItem[];
}

const SWIMLANE_DEFS: Array<{ key: string; label: string; color: string; statusColor: string; statuses: string[] }> = [
  { key: 'suggestion', label: 'Suggested Reassignment', color: '#8b5cf6', statusColor: 'text-violet-400', statuses: ['suggestion'] },
  { key: 'parse_errors', label: 'Parse Errors', color: '#ef4444', statusColor: 'text-red-400', statuses: ['parse_errors'] },
  { key: 'needs_extraction', label: 'Needs Extraction', color: '#f59e0b', statusColor: 'text-amber-400', statuses: ['needs_extraction'] },
  { key: 'pending_project', label: 'Pending Project', color: '#f43f5e', statusColor: 'text-rose-400', statuses: ['pending_project'] },
  { key: 'ambiguous', label: 'Ambiguous', color: '#f97316', statusColor: 'text-orange-400', statuses: ['ambiguous'] },
  { key: 'needs_review', label: 'Needs Review', color: '#eab308', statusColor: 'text-amber-400', statuses: ['needs_review'] },
];

export function TriagePage() {
  const [items, setItems] = useState<TriageItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [selectedNote, setSelectedNote] = useState<{ id: string; source: string } | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await getTriageItems();
        setItems(res.items ?? []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const toggle = (key: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const selectItem = (item: TriageItem) => {
    if (selectedNote?.id === item.source_note_id && selectedNote?.source === item.source) {
      setSelectedNote(null);
    } else {
      setSelectedNote({ id: item.source_note_id, source: item.source });
    }
  };

  const closeDetail = () => {
    setSelectedNote(null);
  };

  const handleProjectSuggested = (noteId: string, _source: string, project: string) => {
    setItems((prev) =>
      prev.map((it) =>
        it.source_note_id === noteId ? { ...it, user_suggested_project: project } : it,
      ),
    );
  };

  const [fadingId, setFadingId] = useState<string | null>(null);

  const handleDecided = (noteId: string, _source: string, _decision: string) => {
    setFadingId(noteId);
    setSelectedNote(null);
    setTimeout(() => {
      setItems((prev) => prev.filter((it) => it.source_note_id !== noteId));
      setFadingId(null);
    }, 1200);
  };

  if (loading) {
    return (
      <div className="space-y-5">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="card animate-pulse"
            style={{ height: 160, animationDelay: `${i * 100}ms` }}
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="card" style={{ padding: 48, textAlign: 'center', color: '#a1a1aa' }}>
        Failed to load triage: {error}
      </div>
    );
  }

  // Categorize items into swimlanes
  const swimlanes: (Swimlane & { statusColor: string })[] = SWIMLANE_DEFS.map((def) => {
    let laneItems: TriageItem[];
    if (def.key === 'suggestion') {
      laneItems = items.filter(
        (it) => it.user_suggested_project && it.user_suggested_project !== it.project,
      );
    } else {
      laneItems = items.filter((it) => def.statuses.includes(it.status ?? it.category ?? ''));
    }
    return { ...def, items: laneItems };
  }).filter((lane) => lane.items.length > 0);

  if (swimlanes.length === 0) {
    return (
      <div className="card" style={{ padding: 64, textAlign: 'center' }}>
        <div className="text-zinc-400 text-lg font-medium" style={{ marginBottom: 8 }}>
          No triage items
        </div>
        <div className="text-zinc-600 text-sm">All notes are properly classified</div>
      </div>
    );
  }

  return (
    <div className="flex gap-0" style={{ margin: '-32px', width: 'calc(100% + 64px)', overflowX: 'hidden' }}>
      {/* Swimlanes section */}
      <div className={`flex-1 min-w-0 ${selectedNote ? 'w-3/5' : 'w-full'}`} style={{ padding: 32 }}>
        <div className="space-y-5">
          {swimlanes.map((lane, laneIdx) => (
            <div
              key={lane.key}
              className="card animate-in overflow-hidden"
              style={{
                animationDelay: `${laneIdx * 100}ms`,
                borderLeftWidth: 2,
                borderLeftColor: lane.color,
              }}
            >
              {/* Header */}
              <button
                onClick={() => toggle(lane.key)}
                className="w-full flex items-center justify-between text-left transition-colors"
                style={{
                  padding: '16px 20px',
                  background: collapsed.has(lane.key) ? 'transparent' : 'rgba(255,255,255,0.01)',
                }}
              >
                <div className="flex items-center gap-3">
                  <span className={`text-sm font-semibold ${lane.statusColor}`}>
                    {lane.label}
                  </span>
                  <span
                    className="font-medium font-mono tabular-nums text-zinc-400"
                    style={{
                      fontSize: 11,
                      background: 'rgba(255,255,255,0.06)',
                      borderRadius: 9999,
                      padding: '2px 10px',
                    }}
                  >
                    {lane.items.length}
                  </span>
                </div>
                <svg
                  className={`w-4 h-4 text-zinc-500 transition-transform duration-200 ${collapsed.has(lane.key) ? '' : 'rotate-180'}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {/* Cards */}
              {!collapsed.has(lane.key) && (
                <div style={{ padding: '0 20px 20px' }} className="space-y-2">
                  {lane.items.map((item) => {
                    const isSelected = selectedNote?.id === item.source_note_id && selectedNote?.source === item.source;
                    return (
                      <div
                        key={`${item.source}-${item.source_note_id}`}
                        onClick={() => selectItem(item)}
                        className={`rounded-xl transition-all duration-200 cursor-pointer ${fadingId === item.source_note_id ? 'note-fade-out' : ''} ${isSelected ? 'bg-blue-500/5' : 'hover:bg-white/5'}`}
                        style={{
                          background: isSelected ? 'rgba(59,130,246,0.05)' : 'rgba(255,255,255,0.02)',
                          border: '1px solid rgba(255,255,255,0.04)',
                          padding: 16,
                          boxShadow: isSelected ? 'inset 3px 0 0 0 #3b82f6' : undefined,
                        }}
                      >
                        <div className="flex items-start justify-between gap-3" style={{ marginBottom: 12 }}>
                          <div className="min-w-0 flex-1">
                            <div className="text-sm text-zinc-100 font-medium truncate flex items-center gap-2">
                              <SourceIcon source={item.source} />
                              {item.title || item.source_note_id}
                            </div>
                            {item.excerpt && (
                              <div
                                className="text-zinc-500 leading-relaxed line-clamp-2"
                                style={{ fontSize: 12, marginTop: 6 }}
                              >
                                {item.excerpt}
                              </div>
                            )}
                          </div>
                          <StatusBadge status={item.status} />
                        </div>
                        <div className="flex items-center gap-3 flex-wrap">
                          <ConfidenceBar value={item.confidence ?? 0} />
                          {item.candidate_projects?.length > 0 && (
                            <div className="flex gap-1.5 flex-wrap">
                              {item.candidate_projects.slice(0, 3).map((c) => (
                                <span
                                  key={c.project}
                                  className="font-medium text-zinc-400 font-mono"
                                  style={{
                                    fontSize: 11,
                                    background: 'rgba(255,255,255,0.04)',
                                    border: '1px solid rgba(255,255,255,0.04)',
                                    padding: '2px 8px',
                                    borderRadius: 6,
                                  }}
                                >
                                  {c.project} ({Math.round(c.score * 100)}%)
                                </span>
                              ))}
                            </div>
                          )}
                          {item.user_suggested_project && (
                            <span className="text-violet-400 font-medium" style={{ fontSize: 12 }}>
                              Suggested: {item.user_suggested_project}
                            </span>
                          )}
                          <span className="font-mono text-zinc-600 ml-auto" style={{ fontSize: 11 }}>
                            {item.source}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Detail panel */}
      {selectedNote && (
        <div className="sticky flex-shrink-0" style={{ width: 480, top: 56, height: 'calc(100vh - 56px)' }}>
          <NoteDetail
            noteId={selectedNote.id}
            source={selectedNote.source}
            onClose={closeDetail}
            onProjectSuggested={handleProjectSuggested}
            onDecided={handleDecided}
          />
        </div>
      )}
    </div>
  );
}
