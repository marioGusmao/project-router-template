import { useState } from 'react';
import { refreshIndex } from '../lib/api';

interface Props {
  ageSeconds: number | null;
  onRefreshed?: () => void;
}

export function RefreshIndicator({ ageSeconds, onRefreshed }: Props) {
  const [refreshing, setRefreshing] = useState(false);

  let dotColor = 'bg-zinc-500';
  let label = '...';

  if (ageSeconds !== null) {
    if (ageSeconds < 300) {
      dotColor = 'bg-emerald-500';
    } else if (ageSeconds < 3600) {
      dotColor = 'bg-amber-500';
    } else {
      dotColor = 'bg-rose-500';
    }

    if (ageSeconds < 60) {
      label = `${Math.round(ageSeconds)}s ago`;
    } else if (ageSeconds < 3600) {
      label = `${Math.round(ageSeconds / 60)}m ago`;
    } else {
      label = `${Math.round(ageSeconds / 3600)}h ago`;
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refreshIndex();
      onRefreshed?.();
    } catch {
      // silently fail
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <button
      onClick={handleRefresh}
      disabled={refreshing}
      className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-zinc-800 border border-zinc-700 hover:bg-zinc-700 transition-colors text-xs text-zinc-400 disabled:opacity-50"
    >
      <span className={`w-2 h-2 rounded-full ${dotColor} ${refreshing ? 'animate-pulse' : ''}`} />
      <span>Index: {refreshing ? 'rebuilding...' : label}</span>
      <svg
        className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
        />
      </svg>
    </button>
  );
}
