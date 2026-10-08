#!/usr/bin/env node
// Keep upstream mode handling, but emit the maintained project skill.
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const upstream = path.join(root, 'analysis/vendor/ponytail/hooks');
const entries = {
  SessionStart: 'ponytail-activate.js',
  UserPromptSubmit: 'ponytail-mode-tracker.js',
};
const entry = entries[process.argv[2]];
if (!entry) throw new Error('Expected SessionStart or UserPromptSubmit');

const instructions = require(path.join(upstream, 'ponytail-instructions.js'));
const original = instructions.getPonytailInstructions;
instructions.getPonytailInstructions = (mode) => {
  if (mode === 'review') return original(mode);
  const body = fs.readFileSync(path.join(root, '.codex/skills/ponytail/SKILL.md'), 'utf8');
  return 'PONYTAIL MODE ACTIVE — level: ' + mode + '\n\n' +
    instructions.filterSkillBodyForMode(body, mode);
};
require(path.join(upstream, entry));
