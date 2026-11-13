const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const vm = require('node:vm');

const filename = path.resolve(__dirname, '../lib/api/sandbox-polling.ts');
const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
});
const context = { exports: {}, setTimeout };
vm.runInNewContext(compiled.outputText, context, { filename });
const { pollSandboxJob } = context.exports;
const result = { summary: { total_trades: 2 }, trades: [{ pnl: 3 }], equity_curve: [], pnl_calendar: [] };
const queued = { job_id: 'job-1', status: 'queued' };
const fast = { sleep: async () => {} };

test('queued -> running -> completed returns backend result unchanged', async () => {
  const states = [{ status: 'running' }, { status: 'completed', result_data: result }];
  assert.equal(await pollSandboxJob(queued, async id => { assert.equal(id, 'job-1'); return states.shift(); }, fast), result);
});

for (const status of ['failed', 'cancelled', 'canceled', 'REVOKED', 'expired', 'timeout', 'timed_out']) {
  test(`${status} stops polling immediately`, async () => {
    let calls = 0;
    await assert.rejects(pollSandboxJob(queued, async () => { calls++; return { status, message: 'terminal' }; }, fast), /terminal/);
    assert.equal(calls, 1);
  });
}

test('initial terminal and completed envelopes are handled', async () => {
  const noFetch = async () => assert.fail('No polling');
  await assert.rejects(pollSandboxJob({ ...queued, status: 'cancelled' }, noFetch), /cancelled/);
  assert.equal(await pollSandboxJob({ ...queued, status: 'completed', result_data: result }, noFetch), result);
});

test('wrapped responses and JSON result strings are normalized', async () => {
  const actual = await pollSandboxJob({ success: true, data: queued }, async () => ({ success: true, data: {
    status: 'completed', result_data: JSON.stringify({ success: true, data: result }),
  } }), fast);
  assert.equal(JSON.stringify(actual), JSON.stringify(result));
});

test('missing, corrupt and incomplete results fail instead of rendering empty success', async () => {
  for (const data of [null, '{bad', {}, { summary: {} }]) {
    await assert.rejects(pollSandboxJob(queued, async () => ({ status: 'completed', result_data: data }), fast), /result/);
  }
});

test('transient polling error retries without dispatching another job', async () => {
  let calls = 0;
  assert.equal(await pollSandboxJob(queued, async () => {
    if (++calls === 1) throw new Error('network');
    return { status: 'completed', result_data: result };
  }, fast), result);
  assert.equal(calls, 2);
});

test('repeated network errors stop after three attempts', async () => {
  let calls = 0;
  await assert.rejects(pollSandboxJob(queued, async () => { calls++; throw new Error('network'); }, fast), /NOT cancelled/);
  assert.equal(calls, 3);
});

test('missing and unauthorized jobs stop immediately', async () => {
  for (const status of [401, 403, 404]) {
    let calls = 0;
    await assert.rejects(pollSandboxJob(queued, async () => { calls++; throw { response: { status }, message: 'HTTP error' }; }, fast));
    assert.equal(calls, 1);
  }
});

test('deadline stops stale polling without claiming task cancellation', async () => {
  let now = 0;
  await assert.rejects(pollSandboxJob(queued, async () => queued, {
    now: () => now, sleep: async ms => { now += ms; }, timeoutMs: 6000,
  }), /NOT cancelled/);
  assert.equal(now, 6000);
});

test('unknown status fails closed', async () => {
  await assert.rejects(pollSandboxJob(queued, async () => ({ status: 'mystery' }), fast), /Unexpected/);
});

test('admin client uses polling helper and workspace clears Running on all paths', () => {
  const admin = fs.readFileSync(path.resolve(__dirname, '../lib/api/admin.ts'), 'utf8');
  const page = fs.readFileSync(path.resolve(__dirname, '../app/(admin)/admin/strategy-requests/strategies/[strategyId]/page.tsx'), 'utf8');
  assert.match(admin, /return pollSandboxJob<AdminStrategySandboxResult>/);
  assert.match(admin, /\/api\/v1\/jobs\/\$\{jobId\}/);
  assert.match(page, /setSandboxResult\(res\);\s+setSandboxing\(false\);/);
  assert.match(page, /finally\s*\{\s*setSandboxing\(false\);/);
});

test('reports actual queued and running progress to the UI', async () => {
  const updates = [];
  await pollSandboxJob({ job_id: 'job-1', status: 'queued', message: 'Waiting', progress: 0 },
    async () => ({ status: 'completed', progress: 100, message: 'Done', result_data: result }),
    { ...fast, onUpdate: value => updates.push(value) });
  assert.equal(updates[0].status, 'queued');
  assert.equal(updates[0].jobId, 'job-1');
  assert.equal(updates.at(-1).progress, 100);
});

test('sandbox does not forcibly override long or short directions', () => {
  const page = fs.readFileSync(path.resolve(__dirname, '../app/(admin)/admin/strategy-requests/strategies/[strategyId]/page.tsx'), 'utf8');
  const sandbox = page.slice(page.indexOf('const runSandbox = async () =>'), page.indexOf('const applyPreset = () =>'));
  assert.match(sandbox, /runtime_config: runtimePresetConfig/);
  assert.doesNotMatch(sandbox, /allow_long:\s*false/);
  assert.doesNotMatch(sandbox, /allow_short:\s*true/);
});
