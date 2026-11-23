const DEFAULT_DURATION = 5000;
const UNDO_DURATION = 8000;

// Kept outside React so navigation does not interrupt an undo window.
export function createToastStore({ now = Date.now, schedule = setTimeout, cancel = clearTimeout } = {}) {
  let sequence = 0;
  let snapshot = { toasts: [], hiddenKeys: new Set() };
  const entries = new Map();
  const listeners = new Set();
  const pauses = new Set();

  const publish = () => {
    snapshot = { ...snapshot, toasts: [...entries.values()].map(({ timer, ...entry }) => entry) };
    listeners.forEach((listener) => listener());
  };

  const remove = (id) => {
    const entry = entries.get(id);
    if (!entry) return;
    cancel(entry.timer);
    entries.delete(id);
  };

  const reveal = (key) => {
    const hiddenKeys = new Set(snapshot.hiddenKeys);
    hiddenKeys.delete(key);
    snapshot = { ...snapshot, hiddenKeys };
  };

  const arm = (entry) => {
    entry.startedAt = now();
    if (entry.duration && !pauses.size && entry.status === 'visible') {
      entry.timer = schedule(() => finish(entry.id), entry.remaining);
    }
  };

  const add = (message, options = {}) => {
    const { key } = options;
    if (key) {
      const existing = [...entries.values()].find((entry) => entry.key === key);
      if (existing?.status === 'working' || existing?.commit) return existing.id;
      if (existing) remove(existing.id);
    }
    const duration = options.duration ?? (options.type === 'error' ? 10000 : DEFAULT_DURATION);
    const entry = {
      ...options, id: ++sequence, message, duration, remaining: duration,
      type: options.type || 'success', status: 'visible', paused: pauses.size > 0,
    };
    entries.set(entry.id, entry);
    arm(entry);
    publish();
    return entry.id;
  };

  const finish = async (id) => {
    const entry = entries.get(id);
    if (!entry || entry.status !== 'visible') return;
    cancel(entry.timer);
    if (!entry.commit) {
      remove(id);
      publish();
      return;
    }
    entry.status = 'working';
    publish();
    try {
      await entry.commit();
      if (!entries.has(id)) return;
      // Retain the key after deletion so stale page data cannot show the item again.
      remove(id);
      publish();
    } catch (error) {
      if (!entries.has(id)) return;
      reveal(entry.key);
      remove(id);
      add(entry.errorMessage || 'Couldn’t delete item', { type: 'error', description: error.message });
    }
  };

  const action = async (id) => {
    const entry = entries.get(id);
    if (!entry || entry.status !== 'visible') return;
    cancel(entry.timer);
    entry.status = 'working';
    publish();
    try {
      if (entry.commit) reveal(entry.key);
      else await entry.action();
      if (!entries.has(id)) return;
      remove(id);
      add(entry.undoMessage || 'Change undone', { type: 'success' });
    } catch (error) {
      if (!entries.has(id)) return;
      entry.status = 'visible';
      entry.remaining = entry.duration;
      arm(entry);
      add('Couldn’t undo change', { type: 'error', description: error.message });
    }
  };

  return {
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    getSnapshot: () => snapshot,
    success: (message, options) => add(message, { ...options, type: 'success' }),
    error: (message, options) => add(message, { ...options, type: 'error' }),
    info: (message, options) => add(message, { ...options, type: 'info' }),
    undoable({ key, message, commit, ...options }) {
      if (snapshot.hiddenKeys.has(key)) return;
      snapshot = { ...snapshot, hiddenKeys: new Set([...snapshot.hiddenKeys, key]) };
      return add(message, {
        duration: UNDO_DURATION, type: 'info', actionLabel: 'Undo',
        description: 'You can undo this before the timer ends.', ...options, key, commit,
      });
    },
    dismiss: finish,
    action,
    pause(reason) {
      if (pauses.has(reason)) return;
      if (!pauses.size) entries.forEach((entry) => {
        cancel(entry.timer);
        entry.remaining = Math.max(0, entry.remaining - (now() - entry.startedAt));
        entry.paused = true;
      });
      pauses.add(reason);
      publish();
    },
    resume(reason) {
      if (!pauses.delete(reason) || pauses.size) return;
      entries.forEach((entry) => { entry.paused = false; arm(entry); });
      publish();
    },
    clear() {
      entries.forEach((entry) => cancel(entry.timer));
      entries.clear();
      pauses.delete('focus');
      pauses.delete('hover');
      snapshot = { toasts: [], hiddenKeys: new Set() };
      publish();
    },
    hasPending: () => [...entries.values()].some((entry) => entry.commit || entry.status === 'working'),
  };
}
