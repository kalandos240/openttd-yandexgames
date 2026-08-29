/* Install bundled OpenTTD AI content after IDBFS restore but before main().
 *
 * This hook is deliberately platform-neutral. It guarantees that SimpleAI and
 * its library archives are scanner-visible before AI::Initialize(), then calls
 * the existing platform restore wrapper so the OpenTTD 15.3 compatibility
 * chain is installed synchronously before that wrapper reaches its first await.
 * Player-selected max_no_competitors and competitors_interval are never changed.
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

  const ensureDir = (FS, path) => {
    let current = '';
    for (const part of String(path).split('/').filter(Boolean)) {
      current += '/' + part;
      try { FS.mkdir(current); } catch (_) {}
    }
  };

  const base64ToBytes = (value) => {
    const raw = atob(value || '');
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
    return bytes;
  };

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
    for (const [relativePath, encoded] of entries) {
      if (!relativePath.startsWith('ai/')) {
        throw new Error('Unexpected bundled AI install path: ' + relativePath);
      }
      const fullPath = personalDir + '/' + relativePath;
      ensureDir(FS, fullPath.slice(0, fullPath.lastIndexOf('/')));
      const bytes = base64ToBytes(encoded);
      if (!bytes.length) throw new Error('Empty bundled AI archive: ' + relativePath);

      let needsWrite = true;
      try { needsWrite = FS.stat(fullPath).size !== bytes.length; } catch (_) {}
      if (needsWrite) FS.writeFile(fullPath, bytes);

      const size = FS.stat(fullPath).size;
      if (size !== bytes.length) {
        throw new Error(`Bundled AI archive verification failed for ${relativePath}: ${size}/${bytes.length}`);
      }
      installed++;
    }

    window.__openttdAIArchiveCount = installed;
    window.__openttdAIArchivesReady = installed === entries.length;
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
      window.__openttdAIPrerunState = 'idb-loading';

      return nativeSyncfs(true, function(err) {
        const finish = () => {
          if (typeof callback === 'function') callback(err);
        };

        if (err) {
          window.__openttdAIPrerunState = 'idb-error';
          console.warn('[OpenTTD/AI] Initial IDBFS restore reported an error; installing bundled AI anyway', err);
        }

        window.__openttdAIPrerunState = 'installing';
        try {
          const personalDir = '/home/web_user/.openttd';

          /* First guarantee that the scanner-visible tar archives exist. */
          installBundledAIArchives(FS, personalDir);

          /* The wrapper installs compat_14.nut ... compat_1.2.nut before its
           * first await. Cloud/player work may continue after main() is released. */
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
