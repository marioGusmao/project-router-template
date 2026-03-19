const STATUS_COLORS: Record<string, string> = {
  normalized: 'bg-zinc-600/30 text-zinc-300 border border-zinc-500/30',
  classified: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  needs_review: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  ambiguous: 'bg-orange-500/20 text-orange-400 border border-orange-500/30',
  pending_project: 'bg-rose-500/20 text-rose-400 border border-rose-500/30',
  dispatched: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  processed: 'bg-slate-500/20 text-slate-400 border border-slate-500/30',
  parse_errors: 'bg-red-500/20 text-red-400 border border-red-500/30',
  needs_extraction: 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
  suggestion: 'bg-violet-500/20 text-violet-400 border border-violet-500/30',
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[status] || 'bg-zinc-700 text-zinc-300'}`}
    >
      {status?.replace(/_/g, ' ')}
    </span>
  );
}
