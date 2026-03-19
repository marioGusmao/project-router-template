export function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round((value ?? 0) * 100);
  const color = pct >= 85 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-500' : 'bg-rose-500';
  const textColor = pct >= 85 ? 'text-emerald-400' : pct >= 60 ? 'text-amber-400' : 'text-rose-400';
  return (
    <div className="flex items-center gap-2">
      <div
        className="rounded-full overflow-hidden"
        style={{ width: 40, height: 6, background: 'rgba(255,255,255,0.06)' }}
      >
        <div
          className={`h-full rounded-full ${color} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`font-mono tabular-nums ${textColor}`} style={{ fontSize: 11 }}>
        {pct}%
      </span>
    </div>
  );
}
