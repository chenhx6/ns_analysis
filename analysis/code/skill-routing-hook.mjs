// Inject the project's one routing policy; let the agent select skills by task.
import { readFileSync } from 'node:fs';
import { dirname, resolve, relative, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
let input = '';
for await (const chunk of process.stdin) {
  input += chunk;
  if (input.length > 1024 * 1024) throw new Error('Hook payload exceeds 1 MiB');
}
const payload = JSON.parse(input || '{}');
const event = payload.hook_event_name;
if (!['SessionStart', 'UserPromptSubmit'].includes(event)) process.exit(0);
const cwd = relative(root, resolve(payload.cwd || root));
if (cwd === '..' || cwd.startsWith('../') || isAbsolute(cwd)) process.exit(0);
const instructions = readFileSync(resolve(root, 'AGENTS.md'), 'utf8');
const start = '<!-- PROJECT:AUTO-SKILLS:START -->';
const end = '<!-- PROJECT:AUTO-SKILLS:END -->';
const begin = instructions.indexOf(start);
const finish = instructions.indexOf(end, begin + start.length);
if (begin < 0 || finish < 0) throw new Error('Project automatic skill policy is missing');
process.stdout.write(JSON.stringify({ hookSpecificOutput: {
  hookEventName: event,
  additionalContext: instructions.slice(begin + start.length, finish).trim(),
} }) + '\n');
