import { useState } from 'react';

export function RefreshIndicator({ ageSeconds, onRefreshed }: { ageSeconds: number | null; onRefreshed: () => void }) {
  const [refreshing, setRefreshing] = useState(false);
  const [showRebuilt, setShowRebuilt] = useState(false);

  const age = ageSeconds ?? Infinity;
  const isGreen = age < 300;
  const isYellow = age >= 300 && age < 3600;
  const isRed = age >= 3600;

  const dotColor = isGreen ? 'bg-emerald-500' : isYellow ? 'bg-amber-500' : 'bg-rose-500';
  const dotGlow = isGreen ? 'shadow-[0_0_8px_rgba(16,185,129,0.4)]' : isYellow ? 'shadow-[0_0_8px_rgba(245,158,11,0.4)]' : 'shadow-[0_0_8px_rgba(244,63,94,0.4)]';
  const textColor = isGreen ? 'text-zinc-500' : isYellow ? 'text-amber-500/70' : 'text-rose-500/70';

  const label = age === Infinity ? '--' : age < 60 ? `${Math.round(age)}s` : age < 3600 ? `${Math.round(age / 60)}m` : 'Stale';

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await onRefreshed();
      setShowRebuilt(true);
      setTimeout(() => setShowRebuilt(false), 2000);
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <button onClick={handleRefresh} disabled={refreshing} className="flex items-center gap-2 text-sm hover:opacity-80 transition-opacity" title="Refresh index">
      <span className={`w-2 h-2 rounded-full ${dotColor} ${dotGlow} ${isRed ? 'animate-pulse' : ''}`} />
      {showRebuilt ? (
        <span className="text-emerald-400 text-xs font-medium">Rebuilt</span>
      ) : (
        <span className={`text-xs font-mono tabular-nums ${textColor}`}>
          {refreshing ? '...' : `Index: ${label}`}
        </span>
      )}
      <svg className={`w-3.5 h-3.5 text-zinc-600 ${refreshing ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
    </button>
  );
}
