import { useState } from 'react';
import { refreshIndex } from '../lib/api';

interface Props {
  ageSeconds: number | null;
  onRefreshed?: () => void;
}

export function RefreshIndicator({ ageSeconds, onRefreshed }: Props) {
  const [refreshing, setRefreshing] = useState(false);

  let dotColor = 'bg-zinc-500';
  let dotGlow = '';
  let label = '...';

  if (ageSeconds !== null) {
    if (ageSeconds < 300) {
      dotColor = 'bg-emerald-500';
      dotGlow = '0 0 8px rgba(16,185,129,0.4)';
    } else if (ageSeconds < 3600) {
      dotColor = 'bg-amber-500';
      dotGlow = '0 0 8px rgba(245,158,11,0.4)';
    } else {
      dotColor = 'bg-rose-500';
      dotGlow = '0 0 8px rgba(244,63,94,0.4)';
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
      className="flex items-center gap-2.5 rounded-lg text-zinc-500 hover:text-zinc-300 disabled:opacity-50 transition-all duration-200"
      style={{
        padding: '6px 14px',
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.06)',
        fontSize: 12,
      }}
    >
      <span
        className={`rounded-full ${dotColor} ${refreshing ? 'animate-pulse' : ''}`}
        style={{ width: 7, height: 7, boxShadow: dotGlow }}
      />
      <span className="font-medium">
        {refreshing ? 'Rebuilding...' : label}
      </span>
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
