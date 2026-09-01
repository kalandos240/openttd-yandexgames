/* Install bundled OpenTTD AI content after IDBFS restore but before main().
 *
 * This hook is deliberately platform-neutral. It guarantees that SimpleAI and
 * its library archives are scanner-visible before AI::Initialize(). It also
 * performs a targeted migration of OLD bundled NewGRF/base-graphics files that
 * earlier builds incorrectly persisted in IDBFS. Only known immutable package
 * filenames are removed; saves, settings and user-created data are untouched.
 */
(() => {
  'use strict';

  if (window.__openttdAIPrerunHookInstalled) return;
  window.__openttdAIPrerunHookInstalled = true;
  window.__openttdAIPrerunState = 'arming';

  const moduleObject = window.Module;
  if (!moduleObject || !Array.isArray(moduleObject.preRun)) {
    window.__openttdAIPrerunState = 'module-missing';
    console.error('[OpenTTD/AI] Module.preRun is unavailable before runtime startup');
    return;
  }

  const preRun = moduleObject.preRun;
  const nativePush = Array.prototype.push;
  let syncHookInstalled = false;
  let initialPopulateHandled = false;

  const LEGACY_STATIC_FILENAMES = new Set([
    'early-vehicle-set-0.0.2.grf',
    'steel-industry-0.7.2.grf',
    'firs-5.2.0.grf',
    'sailing-ships.grf',
    'iron-horse-4.29.0.grf',
    'road-hog-1.4.1.grf',
    'gist-0.21.10.grf',
    'ogfx2-settings-0.7.grf',
    'ogfx2-settings-1.0.grf',
    'opengfx2-settings-1.0.grf',
    'opengfx2-classic-1.0.grf',
    'OpenGFX2_Classic-0.8.1.tar',
    'PLAYGAMA-LICENSES.md',
  ]);

  const ensureDir = (FS, path) => {
    let current = '';
    for (const part of String(path).split('/').filter(Boolean)) {
      current += '/' + part;
      try { FS.mkdir(current); } catch (_) {}
    }
  };

  const base64DecodedLength = (value) => {
    const encoded = String(value || '');
    if (!encoded) return 0;
    let padding = 0;
    if (encoded.endsWith('==')) padding = 2;
    else if (encoded.endsWith('=')) padding = 1;
    return Math.max(0, Math.floor(encoded.length * 3 / 4) - padding);
  };

  const base64ToBytes = (value) => {
    const raw = atob(value || '');
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
    return bytes;
  };

  const isLegacyBundledIDBPath = (key, personalDir) => {
    if (typeof key !== 'string' || !key.startsWith(personalDir + '/')) return false;
    const relative = key.slice(personalDir.length + 1);
    const slash = relative.lastIndexOf('/');
    const name = slash >= 0 ? relative.slice(slash + 1) : relative;
    if (!LEGACY_STATIC_FILENAMES.has(name)) return false;
    return relative.startsWith('newgrf/') ||
      relative.startsWith('baseset/') ||
      relative === 'PLAYGAMA-LICENSES.md';
  };

  const purgeLegacyBundledIDBEntries = (personalDir) => new Promise((resolve) => {
    if (typeof IDBFS === 'undefined' || !IDBFS || typeof IDBFS.getDB !== 'function') {
      window.__openttdLegacyBundledIDBStatus = 'idbfs-unavailable';
      resolve(0);
      return;
    }

    IDBFS.getDB(personalDir, (dbError, db) => {
      if (dbError || !db) {
        window.__openttdLegacyBundledIDBStatus = 'db-unavailable';
        if (dbError) console.warn('[OpenTTD] Could not inspect old bundled IDBFS data', dbError);
        resolve(0);
        return;
      }

      let transaction;
      try {
        const storeName = IDBFS.DB_STORE_NAME || 'FILE_DATA';
        transaction = db.transaction([storeName], 'readwrite');
        const store = transaction.objectStore(storeName);
        const request = store.openKeyCursor();
        let removed = 0;

        request.onsuccess = (event) => {
          const cursor = event.target.result;
          if (!cursor) return;
          const key = cursor.primaryKey;
          if (isLegacyBundledIDBPath(key, personalDir)) {
            try {
              store.delete(key);
              removed += 1;
            } catch (error) {
              console.warn('[OpenTTD] Could not delete old bundled IDBFS key', key, error);
            }
          }
          cursor.continue();
        };

        transaction.oncomplete = () => {
          window.__openttdLegacyBundledIDBPurged = removed;
          window.__openttdLegacyBundledIDBStatus = 'complete';
          if (removed) console.info(`[OpenTTD] Removed ${removed} obsolete bundled-content IDBFS entries before startup restore`);
          resolve(removed);
        };
        transaction.onerror = (event) => {
          window.__openttdLegacyBundledIDBStatus = 'transaction-error';
          console.warn('[OpenTTD] Old bundled-content IDBFS cleanup failed', event.target?.error || event);
          resolve(removed);
        };
        transaction.onabort = () => {
          window.__openttdLegacyBundledIDBStatus = 'transaction-aborted';
          resolve(removed);
        };
      } catch (error) {
        window.__openttdLegacyBundledIDBStatus = 'cleanup-error';
        console.warn('[OpenTTD] Could not start old bundled-content IDBFS cleanup', error);
        resolve(0);
      }
    });
  });

  const installBundledAIArchives = (FS, personalDir) => {
    const bundle = window.__openttdClassicAIArchives;
    if (!bundle || typeof bundle !== 'object') {
      throw new Error('Bundled SimpleAI archive map is missing');
    }

    const entries = Object.entries(bundle);
    if (!entries.some(([name]) => name.startsWith('ai/')) ||
        !entries.some(([name]) => name.startsWith('ai/library/'))) {
      throw new Error('Bundled SimpleAI payload is missing AI or AI-library archives');
    }

    let installed = 0;
    let decoded = 0;
    let reused = 0;
    for (const [relativePath, encoded] of entries) {
      if (!relativePath.startsWith('ai/')) {
        throw new Error('Unexpected bundled AI install path: ' + relativePath);
      }
      const fullPath = personalDir + '/' + relativePath;
      ensureDir(FS, fullPath.slice(0, fullPath.lastIndexOf('/')));

      const expectedSize = base64DecodedLength(encoded);
      if (!expectedSize) throw new Error('Empty bundled AI archive: ' + relativePath);

      let currentSize = -1;
      try { currentSize = Number(FS.stat(fullPath).size); } catch (_) {}

      if (currentSize !== expectedSize) {
        const bytes = base64ToBytes(encoded);
        if (bytes.length !== expectedSize) {
          throw new Error(`Bundled AI decode length mismatch for ${relativePath}: ${bytes.length}/${expectedSize}`);
        }
        FS.writeFile(fullPath, bytes, { canOwn: true });
        decoded++;
      } else {
        reused++;
      }

      const size = Number(FS.stat(fullPath).size);
      if (size !== expectedSize) {
        throw new Error(`Bundled AI archive verification failed for ${relativePath}: ${size}/${expectedSize}`);
      }
      installed++;
    }

    window.__openttdAIArchiveCount = installed;
    window.__openttdAIArchivesReady = installed === entries.length;
    window.__openttdAIArchiveInstallStats = {
      total: entries.length,
      decoded,
      reused,
      sizeCheckBeforeDecode: true,
      zeroCopyMemfsWrites: true,
    };
    return installed;
  };

  const installSyncHook = () => {
    if (syncHookInstalled) return;
    if (typeof FS === 'undefined' || !FS || typeof FS.syncfs !== 'function') {
      throw new Error('Emscripten FS.syncfs is unavailable during preRun');
    }

    const nativeSyncfs = FS.syncfs.bind(FS);
    syncHookInstalled = true;
    window.__openttdAIPrerunState = 'sync-hooked';

    FS.syncfs = function(populate, callback) {
      if (populate !== true || initialPopulateHandled) {
        return nativeSyncfs(populate, callback);
      }

      initialPopulateHandled = true;
      window.__openttdAIPrerunState = 'idb-cleaning-static-content';
      const personalDir = '/home/web_user/.openttd';

      const runInitialPopulate = () => {
        window.__openttdAIPrerunState = 'idb-loading';
        nativeSyncfs(true, function(err) {
          const finish = () => {
            if (typeof callback === 'function') callback(err);
          };

          if (err) {
            window.__openttdAIPrerunState = 'idb-error';
            console.warn('[OpenTTD/AI] Initial IDBFS restore reported an error; installing bundled AI anyway', err);
          }

          window.__openttdAIPrerunState = 'installing';
          try {
            installBundledAIArchives(FS, personalDir);

            /* Platform wrappers install compat_14.nut ... compat_1.2.nut
             * synchronously before their first await. Cloud/player work may
             * continue after main() is released. */
            const installAndRestore = window.yandexRestoreOpenTTDCloud;
            let backgroundRestore = null;
            if (typeof installAndRestore === 'function') {
              backgroundRestore = installAndRestore(FS, personalDir);
            } else {
              console.error('[OpenTTD/AI] Platform AI compatibility installer is missing');
            }

            window.__openttdAIPrerunReady = true;
            window.__openttdAIPrerunState = 'ready';
            finish();

            if (backgroundRestore) {
              Promise.resolve(backgroundRestore).catch((error) => {
                console.warn('[OpenTTD/AI] Background platform restore failed after local AI installation', error);
              });
            }
          } catch (error) {
            window.__openttdAIPrerunState = 'install-error';
            console.error('[OpenTTD/AI] Bundled AI startup installation threw', error);
            finish();
          }
        });
      };

      /* Key-only IndexedDB cleanup is intentionally performed BEFORE native
       * IDBFS.populate. This prevents old 20+ MiB GRF blobs from ever being
       * deserialised into MEMFS on the first launch after this upgrade. */
      purgeLegacyBundledIDBEntries(personalDir)
        .catch((error) => console.warn('[OpenTTD] Bundled IDBFS migration failed open', error))
        .finally(runInitialPopulate);
    };
  };

  /* OpenTTD 15.3 os/emscripten/pre.js appends its filesystem preRun callback
   * with Module.preRun.push(...). Decorate callbacks appended from this point
   * onward so our syncfs interceptor is active before IDBFS populate starts. */
  preRun.push = function(...callbacks) {
    const wrapped = callbacks.map((callback) => {
      if (typeof callback !== 'function') return callback;
      return function(...args) {
        try {
          installSyncHook();
        } catch (error) {
          window.__openttdAIPrerunState = 'hook-error';
          console.error('[OpenTTD/AI] Could not install startup sync hook', error);
        }
        return callback.apply(this, args);
      };
    });
    return nativePush.apply(this, wrapped);
  };

  window.__openttdAIPrerunState = 'armed';
})();
