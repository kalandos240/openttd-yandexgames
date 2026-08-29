/* Ensure bundled OpenTTD AI content is installed after IDBFS restore but before main().
 *
 * The platform runtime defines window.yandexRestoreOpenTTDCloud() before the
 * Emscripten runtime is loaded. The OpenTTD runtime-fixes layer wraps that
 * function and synchronously installs SimpleAI plus its API compatibility
 * chain before its first await. This hook intercepts the first populate=true
 * FS.syncfs() performed by OpenTTD's preRun code, invokes that wrapper after
 * IDBFS is available, applies the local competitor invariant, and then
 * immediately releases startup. Cloud/player I/O is deliberately allowed to
 * finish in the background and can never gate OpenTTD main().
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

  /* The cloud restore wrapper deliberately performs network/player work in the
   * background. Do not let that async boundary delay the one setting OpenTTD
   * must see before main(): the number of computer competitors. In particular,
   * do not touch competitor_start_time here; a user-selected value of 0 must
   * survive exactly as configured in the New Game settings. */
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

        const installAndRestore = window.yandexRestoreOpenTTDCloud;
        if (typeof installAndRestore !== 'function') {
          window.__openttdAIPrerunState = 'installer-missing';
          console.error('[OpenTTD/AI] Startup AI installer is missing');
          finish();
          return;
        }

        window.__openttdAIPrerunState = 'installing';
        try {
          /* Calling an async function executes synchronously up to its first
           * await. The runtime-fixes wrapper installs SimpleAI and every compat
           * script before awaiting cloud restore. Apply the local competitor
           * invariant in the same JS turn, before OpenTTD's syncfs run
           * dependency is released. */
          const personalDir = '/home/web_user/.openttd';
          const backgroundRestore = installAndRestore(FS, personalDir);
          forceStartupAIConfig(FS, personalDir);
          window.__openttdAIPrerunReady = true;
          window.__openttdAIPrerunState = 'ready';
          finish();

          Promise.resolve(backgroundRestore).catch((error) => {
            console.warn('[OpenTTD/AI] Background platform restore failed after local AI installation', error);
          });
        } catch (error) {
          window.__openttdAIPrerunState = 'install-error';
          console.error('[OpenTTD/AI] Bundled AI startup installation threw', error);
          finish();
        }
      });
    };
  };

  /* Emscripten's pre.js is part of openttd-runtime.js and appends its preRun
   * callback after this file has loaded. Decorate every callback appended from
   * this point onward so the first one that actually runs installs our syncfs
   * interceptor before OpenTTD's own startup callback can populate IDBFS.
   */
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
