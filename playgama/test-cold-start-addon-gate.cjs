'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const scriptPath = path.join(__dirname, 'openttd-bundled-addons.js');
const source = fs.readFileSync(scriptPath, 'utf8');

const fetched = [];
const writes = [];
const fileSizes = new Map();
let previousRestoreCalls = 0;
let persisted = 0;

global.window = globalThis;
global.document = { baseURI: 'https://cold-start.invalid/game/' };
global.Module = { calledRun: false, postRun: [] };
global.requestIdleCallback = (callback) => {
  setTimeout(() => callback({ didTimeout: false, timeRemaining: () => 50 }), 0);
  return 1;
};
global.requestAnimationFrame = (callback) => setTimeout(() => callback(Date.now()), 0);
global.openttd_syncfs = (callback) => {
  persisted += 1;
  if (callback) callback(null);
};

// Keep the regression test runnable in both the GitHub host (new Node) and the
// pinned Emscripten 3.1.57 container (Node 16, which has no global Response).
const mockResponse = (body, { json = false } = {}) => {
  const bytes = json
    ? Buffer.from(JSON.stringify(body), 'utf8')
    : Buffer.from(body);
  return {
    ok: true,
    status: 200,
    async json() {
      if (json) return body;
      return JSON.parse(bytes.toString('utf8'));
    },
    async arrayBuffer() {
      return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
    },
  };
};

global.fetch = async (url) => {
  const value = String(url);
  fetched.push(value);
  if (value.endsWith('/PLAYGAMA-ALL-LICENSES.md')) {
    throw new Error('Runtime license fetch must stay removed');
  }
  if (value.endsWith('/OPENTTD-BUNDLED-ADDONS.json')) {
    return mockResponse({
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
    }, { json: true });
  }
  if (value.endsWith('/addons/test.grf')) {
    return mockResponse(Uint8Array.from([1, 2, 3, 4]));
  }
  if (value.endsWith('/addons/test-base.tar')) {
    return mockResponse(Uint8Array.from([5, 6, 7]));
  }
  throw new Error(`Unexpected cold-start fetch: ${value}`);
};
global.yandexRestoreOpenTTDCloud = async () => {
  previousRestoreCalls += 1;
};

// Minimal Emscripten-FS-compatible mock. Chunked writes are recorded on close
// so the test verifies the same API path used by large real NewGRFs.
const fakeFS = {
  mkdir() {},
  stat(target) {
    if (!fileSizes.has(target)) throw new Error('not found');
    return { size: fileSizes.get(target) };
  },
  open(target, mode) {
    assert.equal(mode, 'w');
    fileSizes.set(target, 0);
    return { target };
  },
  write(stream, data, offset, length, position) {
    assert.ok(data instanceof Uint8Array);
    assert.ok(offset >= 0 && length >= 0 && position >= 0);
    fileSizes.set(stream.target, Math.max(fileSizes.get(stream.target) || 0, position + length));
    return length;
  },
  close(stream) {
    writes.push({ target: stream.target, bytes: fileSizes.get(stream.target) || 0 });
  },
  unlink(target) {
    fileSizes.delete(target);
  },
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

  await sleep(2650);
  assert.ok(!fetched.some((url) => url.endsWith('/PLAYGAMA-ALL-LICENSES.md')),
    'runtime must never fetch the removed combined license document');
  assert.ok(fetched.some((url) => url.endsWith('/OPENTTD-BUNDLED-ADDONS.json')));
  assert.ok(fetched.some((url) => url.endsWith('/addons/test.grf')));
  assert.ok(fetched.some((url) => url.endsWith('/addons/test-base.tar')));
  assert.equal(global.__openttdBundledAddonsState, 'ready');

  const targets = writes.map((row) => row.target).sort();
  assert.deepEqual(targets, ['/baseset/test-base.tar', '/newgrf/test.grf']);
  assert.ok(targets.every((target) => !target.startsWith('/home/web_user/.openttd/')),
    'immutable bundled content must never be written into the persistent personal directory');
  assert.ok(targets.every((target) => !target.startsWith('/docs/')),
    'runtime license documents must not be materialized in MEMFS');
  assert.equal(global.__openttdBundledAddonsStatus.persistent, false);
  assert.equal(global.__openttdBundledAddonsStatus.chunked_writes, true);
  assert.equal(persisted, 0, 'bundled static content must never trigger an IDBFS persistence pass');

  console.log('PASS: bundled add-ons stay out of cold-start IDBFS; runtime licenses stay removed; writes are chunk-capable.');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
