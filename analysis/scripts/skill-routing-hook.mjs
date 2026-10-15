// Inject the project's one routing policy; let the agent select skills by task.
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
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
const profilePath = resolve(root, 'analysis/scripts/agent-prompt.txt');
const profile = readFileSync(profilePath);
if (!profile.toString('utf8').trim()) throw new Error('Project research profile is empty');
const context = [instructions.slice(begin + start.length, finish).trim()];
// Skip only a fresh co launch; clear/resume still need their own context restoration.
const alreadyInjected = event === 'SessionStart' && payload.source === 'startup'
  && process.env.CHX_CO_PROMPT_SHA256 === createHash('sha256').update(profile).digest('hex');
if (event === 'SessionStart' && !alreadyInjected) context.unshift(profile.toString('utf8').trim());
if (event === 'UserPromptSubmit') context.push(`研究背景与常规判断边界见 ${JSON.stringify(profilePath)}；需要时读取，不因任务专业性额外增加确认门槛。`);
process.stdout.write(JSON.stringify({ hookSpecificOutput: {
  hookEventName: event,
  additionalContext: context.join('\n\n'),
} }) + '\n');
