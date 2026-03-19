import { useState, useEffect } from 'react';
import { getTriageItems, type TriageItem } from '../lib/api';
import { StatusBadge } from '../components/StatusBadge';
import { ConfidenceBar } from '../components/ConfidenceBar';

interface Swimlane {
  key: string;
  label: string;
  color: string;
  items: TriageItem[];
}

const SWIMLANE_DEFS: Array<{ key: string; label: string; color: string; statuses: string[] }> = [
  { key: 'suggestion', label: 'Suggested Reassignment', color: 'border-violet-500/40', statuses: ['suggestion'] },
  { key: 'parse_errors', label: 'Parse Errors', color: 'border-red-500/40', statuses: ['parse_errors'] },
  { key: 'needs_extraction', label: 'Needs Extraction', color: 'border-amber-500/40', statuses: ['needs_extraction'] },
  { key: 'pending_project', label: 'Pending Project', color: 'border-rose-500/40', statuses: ['pending_project'] },
  { key: 'ambiguous', label: 'Ambiguous', color: 'border-orange-500/40', statuses: ['ambiguous'] },
  { key: 'needs_review', label: 'Needs Review', color: 'border-amber-500/40', statuses: ['needs_review'] },
];

export function TriagePage() {
  const [items, setItems] = useState<TriageItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());

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

  if (loading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-32 bg-zinc-900 border border-zinc-800 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-8 text-center text-zinc-400">
        Failed to load triage: {error}
      </div>
    );
  }

  // Categorize items into swimlanes
  const swimlanes: Swimlane[] = SWIMLANE_DEFS.map((def) => {
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
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-12 text-center">
        <div className="text-zinc-500 text-lg mb-2">No triage items</div>
        <div className="text-zinc-600 text-sm">All notes are properly classified</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {swimlanes.map((lane) => (
        <div key={lane.key} className={`bg-zinc-900 border ${lane.color} rounded-lg`}>
          {/* Header */}
          <button
            onClick={() => toggle(lane.key)}
            className="w-full flex items-center justify-between px-4 py-3 text-left"
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-zinc-200">{lane.label}</span>
              <span className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full">
                {lane.items.length}
              </span>
            </div>
            <svg
              className={`w-4 h-4 text-zinc-500 transition-transform ${collapsed.has(lane.key) ? '' : 'rotate-180'}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* Cards */}
          {!collapsed.has(lane.key) && (
            <div className="px-4 pb-4 grid gap-2">
              {lane.items.map((item) => (
                <div
                  key={`${item.source}-${item.source_note_id}`}
                  className="bg-zinc-800/60 border border-zinc-700/50 rounded-lg p-3"
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="min-w-0">
                      <div className="text-sm text-zinc-100 font-medium truncate">
                        {item.title || item.source_note_id}
                      </div>
                      {item.excerpt && (
                        <div className="text-xs text-zinc-500 mt-1 line-clamp-2">{item.excerpt}</div>
                      )}
                    </div>
                    <StatusBadge status={item.status} />
                  </div>
                  <div className="flex items-center gap-3 flex-wrap">
                    <ConfidenceBar value={item.confidence ?? 0} />
                    {item.candidate_projects?.length > 0 && (
                      <div className="flex gap-1 flex-wrap">
                        {item.candidate_projects.slice(0, 3).map((c) => (
                          <span
                            key={c.project}
                            className="text-xs bg-zinc-700/50 text-zinc-400 px-1.5 py-0.5 rounded"
                          >
                            {c.project} ({Math.round(c.score * 100)}%)
                          </span>
                        ))}
                      </div>
                    )}
                    {item.user_suggested_project && (
                      <span className="text-xs text-violet-400">
                        Suggested: {item.user_suggested_project}
                      </span>
                    )}
                    <span className="text-xs font-mono text-zinc-600 ml-auto">
                      {item.source}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
