'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const scriptPath = path.join(__dirname, 'openttd-bundled-addons.js');
const source = fs.readFileSync(scriptPath, 'utf8');

const fetched = [];
const writes = [];
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
      items: [
        {
          content_id: 'newgrf/test',
          type: 'newgrf',
          asset: 'addons/test.grf',
          install_filename: 'test.grf',
          compression: 'none',
          packaged_bytes: 4,
          installed_bytes: 4,
        },
        {
          content_id: 'base-graphics/test',
          type: 'base-graphics',
          asset: 'addons/test-base.tar',
          install_filename: 'test-base.tar',
          compression: 'none',
          packaged_bytes: 3,
          installed_bytes: 3,
        },
      ],
    }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    });
  }
  if (value.endsWith('/addons/test.grf')) {
    return new Response(Uint8Array.from([1, 2, 3, 4]), { status: 200 });
  }
  if (value.endsWith('/addons/test-base.tar')) {
    return new Response(Uint8Array.from([5, 6, 7]), { status: 200 });
  }
  throw new Error(`Unexpected cold-start fetch: ${value}`);
};
global.yandexRestoreOpenTTDCloud = async () => {
  previousRestoreCalls += 1;
};

const fakeFS = {
  mkdir() {},
  stat() { throw new Error('not found'); },
  writeFile(target, data) { writes.push({ target, bytes: data.byteLength }); },
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
  assert.deepEqual(writes, [], 'optional add-ons must not write anything before Emscripten main()');
  assert.equal(global.__openttdBundledContentReady, undefined, 'optional content task must not exist before main()');

  global.Module.calledRun = true;
  for (const callback of [...global.Module.postRun]) callback();

  await sleep(250);
  assert.deepEqual(fetched, [], 'the first menu frames must render before optional add-on I/O starts');
  assert.deepEqual(writes, [], 'the first menu frames must render before optional add-on writes start');

  await sleep(1150);
  assert.ok(fetched.some((url) => url.endsWith('/PLAYGAMA-ALL-LICENSES.md')));
  assert.ok(fetched.some((url) => url.endsWith('/OPENTTD-BUNDLED-ADDONS.json')));
  assert.ok(fetched.some((url) => url.endsWith('/addons/test.grf')));
  assert.ok(fetched.some((url) => url.endsWith('/addons/test-base.tar')));
  assert.equal(global.__openttdBundledAddonsState, 'ready');

  const targets = writes.map((row) => row.target).sort();
  assert.deepEqual(targets, ['/baseset/test-base.tar', '/docs/PLAYGAMA-LICENSES.md', '/newgrf/test.grf']);
  assert.ok(targets.every((target) => !target.startsWith('/home/web_user/.openttd/')),
    'immutable bundled content must never be written into the persistent personal directory');
  assert.equal(global.__openttdBundledAddonsStatus.persistent, false);
  assert.equal(persisted, 0, 'bundled static content must never trigger an IDBFS persistence pass');

  console.log('PASS: bundled NewGRF/base graphics stay out of cold-start IDBFS and start only after main().');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});