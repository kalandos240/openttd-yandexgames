'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const scriptPath = path.join(__dirname, 'openttd-ai-prerun.js');
const source = fs.readFileSync(scriptPath, 'utf8');

const personal = '/home/web_user/.openttd';
const keys = [
  `${personal}/newgrf/firs-5.2.0.grf`,
  `${personal}/newgrf/iron-horse-4.29.0.grf`,
  `${personal}/newgrf/custom-user-set.grf`,
  `${personal}/baseset/OpenGFX2_Classic-0.8.1.tar`,
  `${personal}/PLAYGAMA-LICENSES.md`,
  `${personal}/save/important-user-save.sav`,
  `${personal}/openttd.cfg`,
];
const deleted = [];
const fileSizes = new Map();
let nativePopulateCalls = 0;
let populateSawMigration = false;
let cloudRestoreCalls = 0;

global.window = globalThis;
global.Module = { preRun: [] };
global.__openttdClassicAIArchives = {
  'ai/534d504c-test.tar': 'AQI=',
  'ai/library/51554248-test.tar': 'AwQ=',
};
global.yandexRestoreOpenTTDCloud = async () => { cloudRestoreCalls += 1; };

global.IDBFS = {
  DB_STORE_NAME: 'FILE_DATA',
  getDB(name, callback) {
    assert.equal(name, personal);
    callback(null, {
      transaction(storeNames, mode) {
        assert.deepEqual(storeNames, ['FILE_DATA']);
        assert.equal(mode, 'readwrite');
        const tx = {};
        const store = {
          delete(key) { deleted.push(String(key)); },
          openKeyCursor() {
            const request = {};
            let index = 0;
            const advance = () => {
              if (index >= keys.length) {
                request.onsuccess?.({ target: { result: null } });
                setImmediate(() => tx.oncomplete?.());
                return;
              }
              const key = keys[index++];
              request.onsuccess?.({
                target: {
                  result: {
                    primaryKey: key,
                    continue: () => setImmediate(advance),
                  },
                },
              });
            };
            setImmediate(advance);
            return request;
          },
        };
        tx.objectStore = (name) => {
          assert.equal(name, 'FILE_DATA');
          return store;
        };
        return tx;
      },
    });
  },
};

global.FS = {
  mkdir() {},
  stat(target) {
    if (!fileSizes.has(target)) throw new Error('ENOENT');
    return { size: fileSizes.get(target) };
  },
  writeFile(target, data) { fileSizes.set(target, data.byteLength); },
  syncfs(populate, callback) {
    assert.equal(populate, true);
    nativePopulateCalls += 1;
    populateSawMigration = deleted.includes(`${personal}/newgrf/firs-5.2.0.grf`) &&
      deleted.includes(`${personal}/newgrf/iron-horse-4.29.0.grf`) &&
      deleted.includes(`${personal}/baseset/OpenGFX2_Classic-0.8.1.tar`);
    setImmediate(() => callback(null));
  },
};

(async () => {
  vm.runInThisContext(source, { filename: scriptPath });
  assert.equal(global.__openttdAIPrerunState, 'armed');

  let populateFinished;
  const finished = new Promise((resolve) => { populateFinished = resolve; });

  // Simulate OpenTTD's os/emscripten/pre.js appending its filesystem preRun
  // callback after our hook has armed Module.preRun.push().
  global.Module.preRun.push(() => {
    global.FS.syncfs(true, (error) => {
      assert.equal(error, null);
      populateFinished();
    });
  });

  assert.equal(global.Module.preRun.length, 1);
  global.Module.preRun[0]();
  await finished;
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(nativePopulateCalls, 1, 'native IDBFS populate must execute exactly once');
  assert.equal(populateSawMigration, true, 'known large bundled blobs must be deleted before native populate begins');

  assert.ok(deleted.includes(`${personal}/newgrf/firs-5.2.0.grf`));
  assert.ok(deleted.includes(`${personal}/newgrf/iron-horse-4.29.0.grf`));
  assert.ok(deleted.includes(`${personal}/baseset/OpenGFX2_Classic-0.8.1.tar`));
  assert.ok(deleted.includes(`${personal}/PLAYGAMA-LICENSES.md`));

  assert.ok(!deleted.includes(`${personal}/newgrf/custom-user-set.grf`), 'unknown user NewGRFs must be preserved');
  assert.ok(!deleted.includes(`${personal}/save/important-user-save.sav`), 'user saves must be preserved');
  assert.ok(!deleted.includes(`${personal}/openttd.cfg`), 'user settings must be preserved');

  assert.equal(global.__openttdLegacyBundledIDBStatus, 'complete');
  assert.equal(global.__openttdLegacyBundledIDBPurged, 4);
  assert.equal(global.__openttdAIArchivesReady, true);
  assert.equal(cloudRestoreCalls, 1);

  console.log('PASS: old bundled GRF blobs are purged before IDBFS populate without touching saves/settings/user content.');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});