import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { getNotes, type NoteListItem } from '../../lib/api';

interface Props {
  onClose: () => void;
  onRefresh?: () => void;
}

interface Command {
  id: string;
  label: string;
  shortcut?: string;
  action: () => void;
}

export function CommandPalette({ onClose, onRefresh }: Props) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const [noteResults, setNoteResults] = useState<NoteListItem[]>([]);
  const [searching, setSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const navCommands: Command[] = useMemo(() => [
    { id: 'nav-dashboard', label: 'Dashboard', shortcut: '1', action: () => { navigate('/'); onClose(); } },
    { id: 'nav-notes', label: 'Notes', shortcut: '2', action: () => { navigate('/notes'); onClose(); } },
    { id: 'nav-triage', label: 'Triage', shortcut: '3', action: () => { navigate('/triage'); onClose(); } },
    { id: 'nav-projects', label: 'Projects', shortcut: '4', action: () => { navigate('/projects'); onClose(); } },
    { id: 'nav-archive', label: 'Archive', shortcut: '5', action: () => { navigate('/archive'); onClose(); } },
    { id: 'cmd-refresh', label: 'Refresh Index', shortcut: 'R', action: () => { onRefresh?.(); onClose(); } },
  ], [navigate, onClose, onRefresh]);

  const noteCommands: Command[] = useMemo(() => noteResults.map((note) => ({
    id: `note-${note.source}-${note.source_note_id}`,
    label: note.title || note.source_note_id,
    action: () => {
      navigate(`/notes?id=${encodeURIComponent(note.source_note_id)}&source=${encodeURIComponent(note.source)}`);
      onClose();
    },
  })), [noteResults, navigate, onClose]);

  const items = useMemo(() => query.trim()
    ? [
        ...navCommands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase())),
        ...noteCommands,
      ]
    : navCommands, [query, navCommands, noteCommands]);

  // Search notes when query changes
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    const trimmed = query.trim();
    if (!trimmed) {
      setNoteResults([]);
      setSearching(false);
      return;
    }

    setSearching(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await getNotes({ search: trimmed, per_page: '8' });
        setNoteResults(res.notes ?? []);
      } catch {
        setNoteResults([]);
      } finally {
        setSearching(false);
      }
    }, 200);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  // Reset active index when items change
  useEffect(() => {
    setActiveIndex(0);
  }, [items.length]);

  // Auto-focus on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Scroll active item into view
  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const active = list.children[activeIndex] as HTMLElement | undefined;
    active?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((prev) => Math.min(prev + 1, items.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (items[activeIndex]) {
        items[activeIndex].action();
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  }, [items, activeIndex, onClose]);

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) {
      onClose();
    }
  };

  return (
    <div
      ref={overlayRef}
      onClick={handleOverlayClick}
      className="fixed inset-0 z-[100] flex items-start justify-center"
      style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)', paddingTop: '15vh' }}
    >
      <div
        className="rounded-2xl shadow-2xl overflow-hidden"
        style={{
          width: 520,
          maxHeight: '60vh',
          background: 'linear-gradient(135deg, rgba(24,24,27,0.98) 0%, rgba(39,39,42,0.95) 100%)',
          border: '1px solid rgba(255,255,255,0.08)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Search input */}
        <div
          className="flex items-center gap-3"
          style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}
        >
          <svg
            className="text-zinc-500 flex-shrink-0"
            style={{ width: 16, height: 16 }}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search notes, projects, commands..."
            className="flex-1 bg-transparent text-zinc-100 placeholder-zinc-600 outline-none"
            style={{ fontSize: 14 }}
          />
          <span
            className="font-mono text-zinc-600 flex-shrink-0"
            style={{
              fontSize: 10,
              background: 'rgba(39,39,42,0.8)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 4,
              padding: '2px 6px',
            }}
          >
            ESC
          </span>
        </div>

        {/* Results list */}
        <div
          ref={listRef}
          className="overflow-y-auto"
          style={{ padding: '8px', maxHeight: 'calc(60vh - 60px)' }}
        >
          {items.length === 0 && !searching && (
            <div className="text-zinc-500 text-center" style={{ padding: '32px 16px', fontSize: 13 }}>
              No results found
            </div>
          )}
          {searching && items.length === 0 && (
            <div className="text-zinc-500 text-center" style={{ padding: '32px 16px', fontSize: 13 }}>
              Searching...
            </div>
          )}
          {items.map((item, idx) => (
            <button
              key={item.id}
              onClick={() => item.action()}
              onMouseEnter={() => setActiveIndex(idx)}
              className="w-full text-left flex items-center justify-between rounded-lg transition-colors"
              style={{
                padding: '10px 14px',
                fontSize: 13,
                background: activeIndex === idx ? 'rgba(255,255,255,0.06)' : 'transparent',
                color: activeIndex === idx ? '#f4f4f5' : '#a1a1aa',
              }}
            >
              <div className="flex items-center gap-3 min-w-0">
                <span
                  className="flex-shrink-0"
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    background: item.id.startsWith('note-')
                      ? 'rgba(139,92,246,0.6)'
                      : item.id.startsWith('cmd-')
                        ? 'rgba(59,130,246,0.6)'
                        : 'rgba(161,161,170,0.4)',
                  }}
                />
                <span className="truncate">{item.label}</span>
              </div>
              {item.shortcut && (
                <span
                  className="font-mono text-zinc-600 flex-shrink-0"
                  style={{
                    fontSize: 11,
                    background: 'rgba(39,39,42,0.8)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: 4,
                    padding: '1px 6px',
                    minWidth: 22,
                    textAlign: 'center',
                  }}
                >
                  {item.shortcut}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Footer hint */}
        <div
          className="flex items-center justify-center gap-4 text-zinc-600"
          style={{ fontSize: 11, padding: '10px 16px', borderTop: '1px solid rgba(255,255,255,0.06)' }}
        >
          <span><span className="font-mono text-zinc-500">↑↓</span> navigate</span>
          <span><span className="font-mono text-zinc-500">↵</span> select</span>
          <span><span className="font-mono text-zinc-500">esc</span> close</span>
        </div>
      </div>
    </div>
  );
}
