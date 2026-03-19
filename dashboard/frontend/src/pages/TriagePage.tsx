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
      <div className="space-y-5">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-40 bg-zinc-900/80 border border-zinc-800/60 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-zinc-900/80 border border-zinc-800/60 rounded-xl p-8 text-center text-zinc-400">
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
      <div className="bg-zinc-900/80 border border-zinc-800/60 rounded-xl p-16 text-center">
        <div className="text-zinc-400 text-lg font-medium mb-2">No triage items</div>
        <div className="text-zinc-600 text-sm">All notes are properly classified</div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {swimlanes.map((lane) => (
        <div key={lane.key} className={`bg-zinc-900/50 rounded-xl border ${lane.color} overflow-hidden`}>
          {/* Header */}
          <button
            onClick={() => toggle(lane.key)}
            className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-zinc-800/20 transition-colors"
          >
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-zinc-200">{lane.label}</span>
              <span className="text-[11px] font-medium bg-zinc-800/80 text-zinc-400 px-2.5 py-1 rounded-full tabular-nums">
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
            <div className="px-5 pb-5 space-y-2">
              {lane.items.map((item) => (
                <div
                  key={`${item.source}-${item.source_note_id}`}
                  className="bg-zinc-800/40 border border-zinc-700/30 rounded-lg p-4 hover:bg-zinc-800/60 transition-colors"
                >
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="min-w-0 flex-1">
                      <div className="text-sm text-zinc-100 font-medium truncate">
                        {item.title || item.source_note_id}
                      </div>
                      {item.excerpt && (
                        <div className="text-xs text-zinc-500 mt-1.5 line-clamp-2 leading-relaxed">{item.excerpt}</div>
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
                            className="text-[11px] bg-zinc-700/40 text-zinc-400 px-2 py-0.5 rounded-md font-medium"
                          >
                            {c.project} ({Math.round(c.score * 100)}%)
                          </span>
                        ))}
                      </div>
                    )}
                    {item.user_suggested_project && (
                      <span className="text-xs text-violet-400 font-medium">
                        Suggested: {item.user_suggested_project}
                      </span>
                    )}
                    <span className="text-[11px] font-mono text-zinc-600 ml-auto">
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
