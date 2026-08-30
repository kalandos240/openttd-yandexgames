'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const scriptPath = path.join(__dirname, 'openttd-bundled-addons.js');
const source = fs.readFileSync(scriptPath, 'utf8');

const fetched = [];
let previousRestoreCalls = 0;
let persisted = 0;

global.window = globalThis;
global.document = { baseURI: 'https://cold-start.invalid/game/' };
global.Module = { calledRun: false, postRun: [] };
global.requestIdleCallback = (callback) => {
  setTimeout(() => callback({ didTimeout: false, timeRemaining: () => 50 }), 0);
  return 1;
};
global.openttd_syncfs = (callback) => {
  persisted += 1;
  if (callback) callback(null);
};
global.fetch = async (url) => {
  const value = String(url);
  fetched.push(value);
  if (value.endsWith('/PLAYGAMA-ALL-LICENSES.md')) {
    return new Response(new Uint8Array(2048), { status: 200 });
  }
  if (value.endsWith('/OPENTTD-BUNDLED-ADDONS.json')) {
    return new Response(JSON.stringify({
      manifest_version: 1,
      enabled_by_default: false,
      items: [],
    }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    });
  }
  throw new Error(`Unexpected cold-start fetch: ${value}`);
};
global.yandexRestoreOpenTTDCloud = async () => {
  previousRestoreCalls += 1;
};

const fakeFS = {
  mkdir() {},
  stat() { throw new Error('not found'); },
  writeFile() {},
};

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

(async () => {
  vm.runInThisContext(source, { filename: scriptPath });
  assert.equal(typeof global.yandexRestoreOpenTTDCloud, 'function');

  await global.yandexRestoreOpenTTDCloud(fakeFS, '/home/web_user/.openttd');

  assert.equal(previousRestoreCalls, 1, 'the AI/cloud compatibility chain must still run during preRun');
  assert.equal(global.__openttdBundledAddonsState, 'waiting-for-main');
  assert.deepEqual(fetched, [], 'optional add-ons must not fetch anything before Emscripten main()');
  assert.equal(global.__openttdBundledContentReady, undefined, 'optional content task must not exist before main()');

  // Simulate the exact state transition that was missing from the old smoke
  // coverage: a pristine first load enters main only after all run dependencies
  // are released.
  global.Module.calledRun = true;
  for (const callback of [...global.Module.postRun]) callback();

  await sleep(250);
  assert.deepEqual(fetched, [], 'the first menu frames must render before optional add-on I/O starts');

  await sleep(1150);
  assert.ok(
    fetched.some((url) => url.endsWith('/PLAYGAMA-ALL-LICENSES.md')),
    'license bundle must start after main()',
  );
  assert.ok(
    fetched.some((url) => url.endsWith('/OPENTTD-BUNDLED-ADDONS.json')),
    'manifest must start after main()',
  );
  assert.equal(global.__openttdBundledAddonsState, 'ready');

  await sleep(25);
  assert.ok(persisted >= 1, 'post-start optional content may persist only after main()');

  console.log('PASS: optional NewGRF/license I/O is excluded from the cold-start critical path.');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
