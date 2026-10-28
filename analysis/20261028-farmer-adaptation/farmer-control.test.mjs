import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { readControl, writeControl, isDisabled, controlPath } from '../../.agents/skills/farmer/farmer-control.mjs';

const project = path.resolve(import.meta.dirname, '../..');
const cli = path.join(project, '.agents/skills/farmer/farmer.mjs');

function run(processPath, args, options) {
  return new Promise((resolve) => {
    const child = spawn(processPath, args, { ...options, windowsHide: true });
    child.on('close', (code) => resolve({ code }));
  });
}

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'chx-farmer-ctrl-'));
  const home = path.join(root, 'codex-home');
  t.after(() => {
    fs.rmSync(root, { recursive: true, force: true });
  });
  fs.mkdirSync(path.join(root, '.codex'), { recursive: true });
  fs.mkdirSync(home, { recursive: true });
  fs.writeFileSync(path.join(root, '.codex/farmer.json'), JSON.stringify({
    schema_version: 1,
    project_root: root,
    poll_interval_ms: 10,
    watchdog_ms: 100,
    max_attempts: 3,
    recovery_message: 'resume',
    recoverable_codes: ['server_overloaded'],
    recoverable_patterns: []
  }, null, 2));

  return {
    root,
    home,
    run: (...args) => run(process.execPath, [cli, ...args, '--project-root', root, '--codex-home', home], {
      cwd: project
    })
  };
}

test('farmer-control module read, write, and disabled checks', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'chx-farmer-unit-ctrl-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));

  assert.equal(isDisabled(root), false);
  const initial = readControl(root);
  assert.equal(initial.disabled, false);

  writeControl(root, { disabled: true, reason: 'test-pause' });
  assert.equal(isDisabled(root), true);
  const updated = readControl(root);
  assert.equal(updated.disabled, true);
  assert.equal(updated.reason, 'test-pause');

  writeControl(root, { disabled: false });
  assert.equal(isDisabled(root), false);
});

test('farmer CLI disable and enable toggle emergency pause in filesystem', async (t) => {
  const f = fixture(t);
  assert.equal(isDisabled(f.root), false);

  const disableRes = await f.run('disable', '--reason', 'testing emergency pause');
  assert.equal(disableRes.code, 0);
  assert.equal(isDisabled(f.root), true);
  assert.equal(readControl(f.root).reason, 'testing emergency pause');

  // When disabled, ensure, start, once are no-ops and never create lock.json
  for (const command of ['ensure', 'once']) {
    const r = await f.run(command);
    assert.equal(r.code, 0);
  }
  assert.equal(fs.existsSync(path.join(f.root, '_work/current/farmer/lock.json')), false);

  const enableRes = await f.run('enable');
  assert.equal(enableRes.code, 0);
  assert.equal(isDisabled(f.root), false);
});
