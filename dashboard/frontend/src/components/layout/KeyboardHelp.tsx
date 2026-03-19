import { useEffect, useRef } from 'react';

interface Props {
  onClose: () => void;
}

const shortcuts: { key: string; description: string }[] = [
  { key: '?', description: 'Show this help' },
  { key: 'j', description: 'Navigate notes down' },
  { key: 'k', description: 'Navigate notes up' },
  { key: 'Enter', description: 'Open note detail' },
  { key: 'Escape', description: 'Close panel / modal' },
  { key: 'p', description: 'Suggest project for selected note' },
  { key: 'r', description: 'Refresh index' },
  { key: '\u2318K', description: 'Command palette' },
  { key: '1', description: 'Go to Dashboard' },
  { key: '2', description: 'Go to Notes' },
  { key: '3', description: 'Go to Triage' },
  { key: '4', description: 'Go to Projects' },
  { key: '5', description: 'Go to Archive' },
];

export function KeyboardHelp({ onClose }: Props) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) {
      onClose();
    }
  };

  return (
    <div
      ref={overlayRef}
      onClick={handleOverlayClick}
      className="fixed inset-0 z-[100] flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
    >
      <div
        className="rounded-2xl shadow-2xl"
        style={{
          width: 420,
          background: 'linear-gradient(135deg, rgba(24,24,27,0.98) 0%, rgba(39,39,42,0.95) 100%)',
          border: '1px solid rgba(255,255,255,0.08)',
          padding: 28,
        }}
      >
        <div className="flex items-center justify-between" style={{ marginBottom: 20 }}>
          <h2 className="text-lg font-semibold text-zinc-100 tracking-tight">
            Keyboard Shortcuts
          </h2>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 transition-colors"
            style={{ fontSize: 20, lineHeight: 1 }}
          >
            &times;
          </button>
        </div>
        <div className="space-y-2">
          {shortcuts.map((s) => (
            <div key={s.key} className="flex items-center justify-between" style={{ padding: '4px 0' }}>
              <span
                className="font-mono text-zinc-100"
                style={{
                  fontSize: 12,
                  background: 'rgba(39,39,42,0.8)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 6,
                  padding: '2px 8px',
                  minWidth: 32,
                  textAlign: 'center',
                  display: 'inline-block',
                }}
              >
                {s.key}
              </span>
              <span className="text-zinc-300" style={{ fontSize: 13 }}>
                {s.description}
              </span>
            </div>
          ))}
        </div>
        <div
          className="text-zinc-600 text-center"
          style={{ fontSize: 11, marginTop: 16, paddingTop: 12, borderTop: '1px solid rgba(255,255,255,0.06)' }}
        >
          Press <span className="font-mono text-zinc-500">Esc</span> to close
        </div>
      </div>
    </div>
  );
}
