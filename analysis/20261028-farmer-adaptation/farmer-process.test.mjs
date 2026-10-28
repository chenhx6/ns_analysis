import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';

const project = path.resolve(import.meta.dirname, '../..');
const farmer = path.join(project, '.agents/skills/farmer/farmer.mjs');

function line(value) { return `${JSON.stringify(value)}\n`; }
function run(processPath, args, options) {
  return new Promise((resolve) => {
    const child = spawn(processPath, args, { ...options, windowsHide: true });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk; });
    child.stderr.on('data', (chunk) => { stderr += chunk; });
    child.on('close', (code) => resolve({ code, stdout, stderr }));
  });
}

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'chx-farmer-proc-'));
  const home = path.join(root, 'codex-home');
  const sessionDir = path.join(home, 'sessions', '2026', '10');
  const sessionFile = path.join(sessionDir, 'rollout-canary.jsonl');
  const queueLog = path.join(root, 'queue.log');

  fs.mkdirSync(path.join(root, '.codex'), { recursive: true });
  fs.mkdirSync(sessionDir, { recursive: true });

  fs.writeFileSync(path.join(root, '.codex/farmer.json'), JSON.stringify({
    schema_version: 1,
    project_root: root,
    poll_interval_ms: 10,
    watchdog_ms: 1000,
    max_attempts: 3,
    recovery_message: '[farmer resume]',
    recoverable_codes: ['server_overloaded'],
    recoverable_patterns: []
  }, null, 2));

  // Linux mock codex executable
  const fake = path.join(root, 'fake-codex.mjs');
  fs.writeFileSync(fake, `import fs from 'node:fs';
fs.appendFileSync(process.env.FARMER_QUEUE_LOG, JSON.stringify({ args: process.argv.slice(2), at: Date.now() }) + '\\n');
`);

  const fakeRunner = path.join(root, 'fake-codex.sh');
  fs.writeFileSync(fakeRunner, `#!/bin/sh
exec "${process.execPath}" "${fake}" "$@"
`);
  fs.chmodSync(fakeRunner, 0o755);

  fs.writeFileSync(sessionFile, [
    { type: 'session_meta', payload: { session_id: 'canary-session', cwd: root } },
    { type: 'event_msg', timestamp: '2026-10-01T00:00:01Z', payload: { type: 'task_complete', turn_id: 'failed-turn', error: { codex_error_info: 'server_overloaded', message: 'capacity' } } }
  ].map(line).join(''));

  const env = {
    ...process.env,
    CODEX_HOME: home,
    FARMER_QUEUE_LOG: queueLog,
    FARMER_CODEX_BIN: fakeRunner
  };

  const once = () => run(process.execPath, [farmer, 'once', '--project-root', root, '--codex-home', home], { cwd: project, env });
  t.after(() => {
    fs.rmSync(root, { recursive: true, force: true });
  });
  return { root, sessionFile, queueLog, once };
}

function append(file, timestamp, payload) {
  fs.appendFileSync(file, line({ type: 'event_msg', timestamp, payload }));
}
function queueCount(file) {
  return fs.existsSync(file) ? fs.readFileSync(file, 'utf8').split(/\r?\n/).filter(Boolean).length : 0;
}
function state(root) {
  return JSON.parse(fs.readFileSync(path.join(root, '_work/current/farmer/state.json'), 'utf8'))['canary-session'];
}

test('farmer process canary recovers once, tracks turn start, and marks complete', async (t) => {
  const f = fixture(t);
  const res = await f.once();
  assert.equal(res.code, 0, res.stderr);
  assert.equal(queueCount(f.queueLog), 1);
  assert.equal(state(f.root).pending, true);

  // Turn start after recovery
  append(f.sessionFile, '2026-10-01T00:00:02Z', { type: 'task_started', turn_id: 'recovery-turn' });
  await f.once();
  assert.equal(queueCount(f.queueLog), 1);
  assert.equal(state(f.root).status, 'running');

  // Turn successfully finished
  append(f.sessionFile, '2026-10-01T00:00:03Z', { type: 'task_complete', turn_id: 'recovery-turn' });
  await f.once();
  assert.equal(queueCount(f.queueLog), 1);
  assert.equal(state(f.root).status, 'complete');
  assert.equal(state(f.root).recovery_chain_active, false);
});
