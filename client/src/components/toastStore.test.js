import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createToastStore } from './toastStore.js';

function setup() {
  let time = 0;
  let timerId = 0;
  const timers = new Map();
  const store = createToastStore({
    now: () => time,
    schedule: (callback, delay) => {
      timers.set(++timerId, { callback, at: time + delay });
      return timerId;
    },
    cancel: (id) => timers.delete(id),
  });
  const advance = async (duration) => {
    const target = time + duration;
    for (;;) {
      const next = [...timers].sort((a, b) => a[1].at - b[1].at)[0];
      if (!next || next[1].at > target) break;
      time = next[1].at;
      timers.delete(next[0]);
      await next[1].callback();
    }
    time = target;
  };
  return { store, advance };
}

test('undo cancels deletion and reveals the original item without calling the API', async () => {
  const { store, advance } = setup();
  let commits = 0;
  const id = store.undoable({ key: 'event:1', message: 'Event deleted', commit: () => commits++ });
  assert.equal(store.getSnapshot().hiddenKeys.has('event:1'), true);
  await advance(4000);
  await store.action(id);
  await advance(20000);
  assert.equal(commits, 0);
  assert.equal(store.getSnapshot().hiddenKeys.has('event:1'), false);
});

test('deletion waits for the complete undo window and keeps stale data hidden after success', async () => {
  const { store, advance } = setup();
  let commits = 0;
  store.undoable({ key: 'event:1', message: 'Deleted', commit: () => commits++ });
  await advance(7999);
  assert.equal(commits, 0);
  await advance(1);
  assert.equal(commits, 1);
  assert.equal(store.getSnapshot().hiddenKeys.has('event:1'), true);
  assert.equal(store.getSnapshot().toasts.length, 0);
});

test('hover, keyboard focus and hidden tabs pause the timer independently', async () => {
  const { store, advance } = setup();
  let commits = 0;
  store.undoable({ key: 'event:1', message: 'Deleted', commit: () => commits++ });
  await advance(3000);
  store.pause('hover');
  store.pause('focus');
  store.pause('hidden');
  await advance(20000);
  store.resume('hover');
  store.resume('hidden');
  await advance(20000);
  assert.equal(commits, 0);
  store.resume('focus');
  await advance(4999);
  assert.equal(commits, 0);
  await advance(1);
  assert.equal(commits, 1);
});

test('new notifications respect an already paused stack', async () => {
  const { store, advance } = setup();
  store.pause('hidden');
  store.success('Saved');
  await advance(30000);
  assert.equal(store.getSnapshot().toasts.length, 1);
  store.resume('hidden');
  await advance(5000);
  assert.equal(store.getSnapshot().toasts.length, 0);
});

test('failed deletion restores the item and reports the API error', async () => {
  const { store, advance } = setup();
  store.undoable({ key: 'event:1', message: 'Deleted', commit: async () => { throw new Error('Connection lost'); } });
  await advance(8000);
  assert.equal(store.getSnapshot().hiddenKeys.has('event:1'), false);
  assert.equal(store.getSnapshot().toasts[0].type, 'error');
  assert.equal(store.getSnapshot().toasts[0].description, 'Connection lost');
});

test('dismiss finalizes a pending deletion once and disables undo during the request', async () => {
  const { store } = setup();
  let commits = 0;
  let resolve;
  const id = store.undoable({ key: 'event:1', message: 'Deleted', commit: () => {
    commits++;
    return new Promise(done => { resolve = done; });
  } });
  const pending = store.dismiss(id);
  assert.equal(store.getSnapshot().toasts[0].status, 'working');
  await store.dismiss(id);
  await store.action(id);
  assert.equal(commits, 1);
  resolve();
  await pending;
  assert.equal(store.getSnapshot().hiddenKeys.has('event:1'), true);
});

test('multiple deletions have independent undo windows', async () => {
  const { store, advance } = setup();
  const committed = [];
  const first = store.undoable({ key: 'event:1', message: 'One', commit: () => committed.push(1) });
  store.undoable({ key: 'event:2', message: 'Two', commit: () => committed.push(2) });
  await store.action(first);
  await advance(8000);
  assert.deepEqual(committed, [2]);
  assert.deepEqual([...store.getSnapshot().hiddenKeys], ['event:2']);
});

test('duplicate actions cannot schedule the same deletion twice', async () => {
  const { store, advance } = setup();
  let commits = 0;
  const options = { key: 'event:1', message: 'Deleted', commit: () => commits++ };
  store.undoable(options);
  store.undoable(options);
  await advance(8000);
  assert.equal(commits, 1);
});

test('clearing an account cancels pending deletes and removes stale filters', async () => {
  const { store, advance } = setup();
  let commits = 0;
  store.undoable({ key: 'event:1', message: 'Deleted', commit: () => commits++ });
  store.clear();
  await advance(8000);
  assert.equal(commits, 0);
  assert.equal(store.getSnapshot().hiddenKeys.size, 0);
  assert.equal(store.hasPending(), false);
});

test('late failures from a cleared account do not display in the next account', async () => {
  const { store } = setup();
  let reject;
  const id = store.undoable({ key: 'event:1', message: 'Deleted', commit: () => new Promise((_, fail) => { reject = fail; }) });
  const pending = store.dismiss(id);
  store.clear();
  reject(new Error('Old account request failed'));
  await pending;
  assert.equal(store.getSnapshot().toasts.length, 0);
});

test('success messages expire, errors allow more reading time, and persistent messages can be dismissed', async () => {
  const { store, advance } = setup();
  store.success('Saved');
  store.error('Couldn’t save');
  const persistent = store.info('Important', { duration: 0 });
  await advance(5000);
  assert.deepEqual(store.getSnapshot().toasts.map(item => item.type), ['error', 'info']);
  await advance(5000);
  assert.equal(store.getSnapshot().toasts.length, 1);
  await store.dismiss(persistent);
  assert.equal(store.getSnapshot().toasts.length, 0);
});

test('async undo actions run once and report completion', async () => {
  const { store } = setup();
  let calls = 0;
  let resolve;
  const id = store.success('Card moved', { action: () => {
    calls++;
    return new Promise(done => { resolve = done; });
  } });
  const pending = store.action(id);
  await store.action(id);
  assert.equal(calls, 1);
  resolve();
  await pending;
  assert.equal(store.getSnapshot().toasts[0].message, 'Change undone');
});

test('failed async undo remains available for retry', async () => {
  const { store } = setup();
  let fail = true;
  const id = store.success('Card moved', { action: async () => {
    if (fail) throw new Error('Connection lost');
  } });
  await store.action(id);
  assert.equal(store.getSnapshot().toasts.find(item => item.id === id).status, 'visible');
  assert.equal(store.getSnapshot().toasts.at(-1).message, 'Couldn’t undo change');
  fail = false;
  await store.action(id);
  assert.equal(store.getSnapshot().toasts.some(item => item.id === id), false);
  assert.equal(store.getSnapshot().toasts.at(-1).message, 'Change undone');
});
