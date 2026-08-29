/* Ensure bundled OpenTTD AI content is installed after IDBFS restore but before main().
 *
 * The platform runtime defines window.yandexRestoreOpenTTDCloud() before the
 * Emscripten runtime is loaded. The OpenTTD runtime-fixes layer wraps that
 * function and synchronously installs SimpleAI plus its API compatibility
 * chain before its first await. This hook also installs the raw bundled AI
 * archives directly as a fail-safe, then intercepts the first populate=true
 * FS.syncfs() performed by OpenTTD's preRun code. Only after the local AI files
 * and startup config are present is OpenTTD's syncfs run dependency released.
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

  /* Install the BaNaNaS archives independently from the cloud wrapper. This is
   * intentionally redundant with openttd-playgama-fixes.js: a platform/cloud
   * integration regression must never leave OpenTTD with AI companies but no
   * script archive on disk when AI::Initialize() scans AI_DIR. */
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

  /* Cloud/player work may continue in the background. The settings OpenTTD
   * must see before main() are local. Do not rewrite competitors_interval:
   * the native web-port patch deliberately gives a user-selected 0 the meaning
   * "start requested competitors immediately". */
  const forceStartupAIConfig = (FS, personalDir) => {
    const path = personalDir + '/openttd.cfg';
    let config = '';
    try { config = FS.readFile(path, { encoding: 'utf8' }); } catch (_) {}

    if (/^max_no_competitors\s*=.*$/m.test(config)) {
      config = config.replace(/^max_no_competitors\s*=.*$/m, 'max_no_competitors = 3');
    } else if (/^\[difficulty\]\s*$/m.test(config)) {
      config = config.replace(/^\[difficulty\]\s*$/m, '[difficulty]\nmax_no_competitors = 3');
    } else {
      config += (config && !config.endsWith('\n') ? '\n' : '') + '[difficulty]\nmax_no_competitors = 3\n';
    }

    FS.writeFile(path, config);
    window.__openttdAIStartupConfigReady = true;
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

          /* Then run the platform wrapper, which installs the exact OpenTTD
           * 15.3 API compatibility chain before its first await. */
          const installAndRestore = window.yandexRestoreOpenTTDCloud;
          let backgroundRestore = null;
          if (typeof installAndRestore === 'function') {
            backgroundRestore = installAndRestore(FS, personalDir);
          } else {
            console.error('[OpenTTD/AI] Platform AI compatibility installer is missing');
          }

          forceStartupAIConfig(FS, personalDir);
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
