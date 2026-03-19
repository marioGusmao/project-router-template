export function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  let color: string;
  if (pct >= 85) {
    color = 'bg-emerald-500';
  } else if (pct >= 60) {
    color = 'bg-amber-500';
  } else {
    color = 'bg-rose-500';
  }

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-zinc-400 font-mono">{pct}%</span>
    </div>
  );
}
