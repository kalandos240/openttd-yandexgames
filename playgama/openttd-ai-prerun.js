/* Ensure bundled OpenTTD AI content is installed after IDBFS restore but before main().
 *
 * The platform runtime defines window.yandexRestoreOpenTTDCloud() before the
 * Emscripten runtime is loaded. openttd-playgama-fixes.js wraps that function
 * with the SimpleAI + compatibility installer. This hook intercepts the first
 * populate=true FS.syncfs() performed by OpenTTD's preRun code and delays its
 * completion callback until the installer/restore wrapper has finished.
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
          Promise.resolve(installAndRestore(FS, '/home/web_user/.openttd')).then(
            () => {
              window.__openttdAIPrerunReady = true;
              window.__openttdAIPrerunState = 'ready';
              finish();
            },
            (error) => {
              window.__openttdAIPrerunState = 'install-error';
              console.error('[OpenTTD/AI] Bundled AI startup installation failed', error);
              finish();
            },
          );
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
