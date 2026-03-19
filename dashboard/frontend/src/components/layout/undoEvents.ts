export interface UndoAction {
  id: string;
  message: string;
  onUndo: () => void;
}

const listeners = new Set<(action: UndoAction) => void>();

export function triggerUndo(message: string, onUndo: () => void) {
  const action: UndoAction = { id: Date.now().toString(), message, onUndo };
  listeners.forEach((fn) => fn(action));
}

export function subscribeUndo(fn: (action: UndoAction) => void) {
  listeners.add(fn);
  return () => { listeners.delete(fn); };
}
