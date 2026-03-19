import { useEffect, useCallback } from 'react';

type KeyHandler = (e: KeyboardEvent) => void;

export function useKeyboard(handlers: Record<string, KeyHandler>) {
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    const target = e.target as HTMLElement;
    const tagName = target.tagName.toLowerCase();
    if (tagName === 'input' || tagName === 'textarea' || tagName === 'select' || target.isContentEditable) {
      return;
    }

    let key = e.key.toLowerCase();
    if (e.metaKey || e.ctrlKey) key = 'cmd+' + key;

    const handler = handlers[key];
    if (handler) {
      e.preventDefault();
      handler(e);
    }
  }, [handlers]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}
