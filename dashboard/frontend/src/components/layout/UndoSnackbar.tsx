import { useState, useEffect, useCallback } from 'react';

interface UndoAction {
  id: string;
  message: string;
  onUndo: () => void;
}

// Global state for snackbar
let showSnackbar: (action: UndoAction) => void = () => {};

export function triggerUndo(message: string, onUndo: () => void) {
  showSnackbar({ id: Date.now().toString(), message, onUndo });
}

export function UndoSnackbar() {
  const [action, setAction] = useState<UndoAction | null>(null);
  const [remaining, setRemaining] = useState(8);

  showSnackbar = useCallback((a: UndoAction) => {
    setAction(a);
    setRemaining(8);
  }, []);

  useEffect(() => {
    if (!action) return;
    const timer = setInterval(() => {
      setRemaining(prev => {
        if (prev <= 1) {
          setAction(null);
          return 8;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [action?.id]);

  if (!action) return null;

  return (
    <div
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-4 px-5 py-3 rounded-xl border border-white/[0.08] backdrop-blur-xl shadow-2xl shadow-black/40"
      style={{ background: 'linear-gradient(135deg, rgba(24,24,27,0.95), rgba(39,39,42,0.9))' }}
    >
      <span className="text-sm text-zinc-200">{action.message}</span>
      <button
        onClick={() => { action.onUndo(); setAction(null); }}
        className="text-sm font-medium text-blue-400 hover:text-blue-300 transition-colors"
      >
        Undo
      </button>
      <span className="text-xs text-zinc-500 font-mono tabular-nums">{remaining}s</span>
      <div className="w-16 h-1 rounded-full bg-white/[0.06] overflow-hidden">
        <div
          className="h-full bg-blue-500/60 rounded-full transition-all duration-1000 ease-linear"
          style={{ width: `${(remaining / 8) * 100}%` }}
        />
      </div>
    </div>
  );
}
