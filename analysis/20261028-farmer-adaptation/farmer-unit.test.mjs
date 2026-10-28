import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  acquireRecoveryLock,
  batchDelay,
  classifyError,
  inside,
  inspect,
  manualRetryLease,
  parseSessionEvents,
  reconcileUnobservedStates,
  recoveryStep,
  releaseRecoveryLock,
  validateConfig,
  RECOVERY_LOCK_TTL_MS,
  SAFE_MAX_ATTEMPTS
} from '../../.agents/skills/farmer/farmer.mjs';

const config = {
  max_attempts: 99,
  recoverable_codes: ['server_overloaded', 'rate_limit_exceeded', 'temporarily_unavailable'],
  recoverable_patterns: ['Selected model is at capacity', 'temporarily unavailable', 'service unavailable', 'rate limit', 'timed out', 'connection reset'],
  recovery_message: 'resume'
};

test('farmer classifies transient and terminal errors', () => {
  assert.equal(classifyError({ message: 'Selected model is at capacity. Please try a different model.' }, config), 'transient-message');
  assert.equal(classifyError({ codex_error_info: 'server_overloaded', message: 'busy' }, config), 'server_overloaded');
  assert.equal(classifyError({ code: 'rate_limit_exceeded', message: 'too many requests' }, config), 'rate_limit_exceeded');
  assert.equal(classifyError({ message: 'authentication failed' }, config), null);
  assert.equal(classifyError({ message: 'context length exceeded' }, config), null);
  assert.equal(classifyError({ message: 'permission denied' }, config), null);
  assert.equal(classifyError({ message: 'turn cancelled by user' }, config), null);
});

test('farmer uses ten-at-a-time delays capped at ten seconds', () => {
  assert.equal(batchDelay(1), 2000);
  assert.equal(batchDelay(10), 2000);
  assert.equal(batchDelay(11), 4000);
  assert.equal(batchDelay(20), 4000);
  assert.equal(batchDelay(21), 6000);
  assert.equal(batchDelay(30), 6000);
  assert.equal(batchDelay(31), 8000);
  assert.equal(batchDelay(40), 8000);
  assert.equal(batchDelay(41), 10000);
  assert.equal(batchDelay(99), 10000);
});

test('farmer validates finite and unlimited attempt configuration', () => {
  assert.equal(validateConfig({ max_attempts: null }).max_attempts, null);
  assert.equal(validateConfig({ max_attempts: 99 }).max_attempts, 99);
  assert.throws(() => validateConfig({ max_attempts: 0 }), /positive integer/);
  assert.throws(() => validateConfig({ max_attempts: 1.5 }), /positive integer/);
  assert.equal(validateConfig({ max_attempts: null, watchdog_ms: 1000 }).watchdog_ms, 1000);
  assert.throws(() => validateConfig({ max_attempts: null, watchdog_ms: 0 }), /watchdog_ms/);
});

test('farmer scopes sessions to the project', () => {
  assert.equal(inside('/home/ys/data_401/data/chx_20260622/analysis', '/home/ys/data_401/data/chx_20260622'), true);
  assert.equal(inside('/home/ys/data_401/data/chx_20260622', '/home/ys/data_401/data/chx_20260622'), true);
  assert.equal(inside('/home/ys/data_401/data/Ge', '/home/ys/data_401/data/chx_20260622'), false);
  assert.equal(inside('/tmp/other', '/home/ys/data_401/data/chx_20260622'), false);
});

test('farmer reads current top-level Codex session metadata', () => {
  const parsed = parseSessionEvents([
    JSON.stringify({ type: 'session_meta', session_id: 's1', cwd: '/home/ys/data_401/data/chx_20260622' }),
    JSON.stringify({ type: 'event_msg', timestamp: '2026-01-01T00:00:01Z', payload: { type: 'task_started', turn_id: 't1' } })
  ], '/home/ys/data_401/data/chx_20260622');
  assert.equal(parsed.id, 's1');
  assert.equal(parsed.cwd, '/home/ys/data_401/data/chx_20260622');
  assert.equal(parsed.latest.payload.type, 'task_started');
});

test('farmer expands rollout tail when tool output hides lifecycle event', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'chx-farmer-rollout-'));
  const home = path.join(root, 'codex-home');
  const dir = path.join(home, 'sessions', '2026', '10');
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, 'rollout.jsonl');
  const filler = JSON.stringify({ type: 'response_item', payload: { type: 'reasoning', summary: 'x'.repeat(1000) } });
  fs.writeFileSync(file, [
    JSON.stringify({ type: 'session_meta', session_id: 'large-s1', cwd: root }),
    JSON.stringify({ type: 'event_msg', timestamp: '2026-10-01T00:00:01Z', payload: { type: 'task_started', turn_id: 't1' } }),
    ...Array(1400).fill(filler)
  ].join('\n') + '\n');
  try {
    const found = inspect(root, home).find(session => session.id === 'large-s1');
    assert.equal(found.latest.payload.type, 'task_started');
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('farmer recovery lock acquires and expires safely', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'chx-farmer-lock-'));
  try {
    const lock1 = acquireRecoveryLock(root, 1000);
    assert.ok(lock1);
    const lock2 = acquireRecoveryLock(root, 1000);
    assert.equal(lock2, null);
    // Expired lock should be reclaimed
    const lock3 = acquireRecoveryLock(root, 1000 + RECOVERY_LOCK_TTL_MS + 10);
    assert.ok(lock3);
    releaseRecoveryLock(lock3);
    const lock4 = acquireRecoveryLock(root, 2000);
    assert.ok(lock4);
    releaseRecoveryLock(lock4);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('farmer recoveryStep lifecycle handling', () => {
  const session = {
    id: 's-lifecycle',
    cwd: '/home/ys/data_401/data/chx_20260622',
    latest: {
      timestamp: '2026-10-01T00:00:01Z',
      payload: { type: 'task_complete', turn_id: 't-err', error: { codex_error_info: 'server_overloaded', message: 'capacity' } }
    }
  };
  let queued = false;
  const queueMock = () => { queued = true; return { status: 0 }; };
  const step1 = recoveryStep(session, {}, { ...config, max_attempts: 3, watchdog_ms: 10000 }, 1000, queueMock);
  assert.equal(queued, true);
  assert.equal(step1.status, 'recovery-pending');
  assert.equal(step1.attempts, 1);

  // Watchdog timeout triggers queue-stuck circuit breaker
  const step2 = recoveryStep(session, step1, { ...config, max_attempts: 3, watchdog_ms: 10000 }, 1000 + 15000, queueMock);
  assert.equal(step2.status, 'queue-stuck');

  // Manual retry clears circuit breaker
  const retryLease = manualRetryLease(session, step2);
  assert.equal(retryLease.status, 'manual-retry-requested');
  assert.equal(retryLease.breaker_cleared, true);
});
