const STATUS_STYLES: Record<string, { bg: string; text: string; glow: string }> = {
  classified: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', glow: 'shadow-[0_0_12px_rgba(16,185,129,0.15)]' },
  needs_review: { bg: 'bg-amber-500/10', text: 'text-amber-400', glow: 'shadow-[0_0_12px_rgba(245,158,11,0.15)]' },
  ambiguous: { bg: 'bg-orange-500/10', text: 'text-orange-400', glow: 'shadow-[0_0_12px_rgba(249,115,22,0.15)]' },
  pending_project: { bg: 'bg-rose-500/10', text: 'text-rose-400', glow: 'shadow-[0_0_12px_rgba(244,63,94,0.15)]' },
  dispatched: { bg: 'bg-blue-500/10', text: 'text-blue-400', glow: 'shadow-[0_0_12px_rgba(59,130,246,0.15)]' },
  processed: { bg: 'bg-slate-500/10', text: 'text-slate-400', glow: '' },
  normalized: { bg: 'bg-zinc-500/10', text: 'text-zinc-400', glow: '' },
  parse_errors: { bg: 'bg-red-500/10', text: 'text-red-400', glow: 'shadow-[0_0_12px_rgba(239,68,68,0.15)]' },
  needs_extraction: { bg: 'bg-amber-500/10', text: 'text-amber-300', glow: 'shadow-[0_0_12px_rgba(245,158,11,0.1)]' },
  suggestion: { bg: 'bg-violet-500/10', text: 'text-violet-400', glow: 'shadow-[0_0_12px_rgba(139,92,246,0.15)]' },
};

export function StatusBadge({ status }: { status: string }) {
  const s = STATUS_STYLES[status] ?? { bg: 'bg-zinc-800', text: 'text-zinc-400', glow: '' };
  return (
    <span
      className={`inline-flex items-center rounded-md font-medium tracking-wide uppercase ${s.bg} ${s.text} ${s.glow}`}
      style={{
        fontSize: 11,
        padding: '4px 10px',
        border: '1px solid currentColor',
        borderColor: 'rgba(255,255,255,0.04)',
      }}
    >
      {status?.replace(/_/g, ' ')}
    </span>
  );
}
