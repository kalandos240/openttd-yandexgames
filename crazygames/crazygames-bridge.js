(() => {
  'use strict';
  if (window.__openttdCrazyGamesBridgeInstalled) return;
  window.__openttdCrazyGamesBridgeInstalled = true;

  const sdkReady = window.crazyGamesSDKReady || Promise.resolve(null);
  const CLOUD_CONFIG_KEY = window.openttdBootTouchUi ? 'openttdMobileConfigV1' : 'openttdConfigV1';
  const CLOUD_SAVE_KEY = 'openttdSaveV1';
  const CLOUD_VERSION = 1;
  const MAX_RAW_SAVE = 512000;
  const CLOUD_DEBOUNCE_MS = 2500;

  let gameplayActive = false;
  let platformGameplayStarted = false;
  let loadingStopped = false;
  let cloudTimer = 0;
  let cloudDisabled = false;
  let lastConfig = null;
  let lastSaveSignature = null;
  let adOpen = false;

  const ensureDir = (FS, path) => {
    let current = '';
    for (const part of String(path).split('/').filter(Boolean)) {
      current += '/' + part;
      try { FS.mkdir(current); } catch (_) {}
    }
  };

  const statTime = stat => {
    try { return Number(stat && stat.mtime) || 0; } catch (_) { return 0; }
  };

  const listFilesRecursive = (FS, dir, out = []) => {
    let entries;
    try { entries = FS.readdir(dir); } catch (_) { return out; }
    for (const name of entries) {
      if (name === '.' || name === '..') continue;
      const path = dir.replace(/\/$/, '') + '/' + name;
      try {
        const stat = FS.stat(path);
        if (FS.isDir(stat.mode)) listFilesRecursive(FS, path, out);
        else if (FS.isFile(stat.mode)) out.push({ path, stat });
      } catch (_) {}
    }
    return out;
  };

  const newestSave = (FS, personalDir) => listFilesRecursive(FS, personalDir)
    .filter(item => /\.sav$/i.test(item.path))
    .sort((a, b) => statTime(b.stat) - statTime(a.stat))[0] || null;

  const bytesToBase64 = bytes => {
    let out = '';
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      out += String.fromCharCode(...bytes.subarray(i, Math.min(bytes.length, i + chunk)));
    }
    return btoa(out);
  };

  const base64ToBytes = value => {
    const raw = atob(String(value || ''));
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
    return bytes;
  };

  const saveSignature = save => save ? `${save.path.split('/').pop()}\t${statTime(save.stat)}\t${Number(save.stat?.size || 0)}` : '';

  async function getSDK(timeoutMs = 4000) {
    return await Promise.race([
      Promise.resolve(sdkReady),
      new Promise(resolve => setTimeout(() => resolve(null), timeoutMs)),
    ]);
  }

  function dataGet(sdk, key) {
    if (!sdk || !sdk.data || cloudDisabled) return null;
    try { return sdk.data.getItem(key); }
    catch (error) {
      if (error && error.code === 'dataModuleDisabled') cloudDisabled = true;
      console.warn('[CrazyGames/OpenTTD] Data read unavailable', error);
      return null;
    }
  }

  function dataSet(sdk, key, value) {
    if (!sdk || !sdk.data || cloudDisabled) return false;
    try { sdk.data.setItem(key, value); return true; }
    catch (error) {
      if (error && error.code === 'dataModuleDisabled') cloudDisabled = true;
      console.warn('[CrazyGames/OpenTTD] Data write unavailable', error);
      return false;
    }
  }

  window.crazyGamesRestoreOpenTTDCloud = async function(FS, personalDir) {
    const sdk = await getSDK();
    if (!sdk || !sdk.data) return;
    try {
      const configRaw = dataGet(sdk, CLOUD_CONFIG_KEY);
      const saveRaw = dataGet(sdk, CLOUD_SAVE_KEY);
      const configPayload = configRaw ? JSON.parse(configRaw) : null;
      const savePayload = saveRaw ? JSON.parse(saveRaw) : null;

      if (configPayload?.version === CLOUD_VERSION && typeof configPayload.config === 'string') {
        lastConfig = configPayload.config;
        const path = personalDir + '/' + (window.openttdConfigFilename || 'openttd.cfg');
        let local = '';
        try { local = FS.readFile(path, { encoding: 'utf8' }); } catch (_) {}
        if (!local.trim()) FS.writeFile(path, configPayload.config);
      }

      if (savePayload?.version === CLOUD_VERSION && savePayload.name && savePayload.data) {
        const localSave = newestSave(FS, personalDir);
        const cloudMtime = Number(savePayload.mtime || savePayload.updatedAt || 0);
        if (!localSave || statTime(localSave.stat) < cloudMtime) {
          const bytes = base64ToBytes(savePayload.data);
          if (bytes.length && bytes.length <= MAX_RAW_SAVE) {
            const dir = personalDir + '/save';
            ensureDir(FS, dir);
            const name = String(savePayload.name).replace(/[^A-Za-z0-9_. ()\-]/g, '_');
            const path = dir + '/' + name;
            FS.writeFile(path, bytes);
            try { const date = new Date(cloudMtime || Date.now()); FS.utime(path, date, date); } catch (_) {}
            lastSaveSignature = saveSignature({ path, stat: FS.stat(path) });
            console.info('[CrazyGames/OpenTTD] Restored cloud save', name);
          }
        }
      }

      if (typeof FS.syncfs === 'function') {
        await new Promise(resolve => { try { FS.syncfs(false, () => resolve()); } catch (_) { resolve(); } });
      }
    } catch (error) {
      console.warn('[CrazyGames/OpenTTD] Cloud restore failed', error);
    }
  };

  async function flushCloud(FS, personalDir) {
    const sdk = await getSDK();
    if (!sdk || !sdk.data || cloudDisabled) return;
    try {
      const configPath = personalDir + '/' + (window.openttdConfigFilename || 'openttd.cfg');
      let config = '';
      try { config = FS.readFile(configPath, { encoding: 'utf8' }); } catch (_) {}
      if (config !== lastConfig) {
        const payload = JSON.stringify({ version: CLOUD_VERSION, updatedAt: Date.now(), config });
        if (dataSet(sdk, CLOUD_CONFIG_KEY, payload)) lastConfig = config;
      }

      const save = newestSave(FS, personalDir);
      const signature = saveSignature(save);
      if (save && signature !== lastSaveSignature) {
        const bytes = FS.readFile(save.path);
        if (bytes.length <= MAX_RAW_SAVE) {
          const payload = JSON.stringify({
            version: CLOUD_VERSION,
            updatedAt: Date.now(),
            mtime: statTime(save.stat) || Date.now(),
            name: save.path.split('/').pop(),
            data: bytesToBase64(bytes),
          });
          if (dataSet(sdk, CLOUD_SAVE_KEY, payload)) lastSaveSignature = signature;
        }
      }
    } catch (error) {
      console.warn('[CrazyGames/OpenTTD] Cloud backup failed', error);
    }
  }

  window.crazyGamesBackupOpenTTDCloud = function(FS, personalDir) {
    clearTimeout(cloudTimer);
    cloudTimer = setTimeout(() => flushCloud(FS, personalDir), CLOUD_DEBOUNCE_MS);
  };

  async function reportGameplay(active) {
    const sdk = await getSDK();
    if (!sdk || !sdk.game) return;
    if (active && !platformGameplayStarted) {
      try {
        if (!loadingStopped && typeof sdk.game.loadingStop === 'function') {
          sdk.game.loadingStop();
          loadingStopped = true;
        }
        if (typeof sdk.game.gameplayStart === 'function') sdk.game.gameplayStart();
        platformGameplayStarted = true;
      } catch (error) {
        console.warn('[CrazyGames/OpenTTD] gameplayStart failed', error);
      }
    } else if (!active && platformGameplayStarted) {
      try {
        if (typeof sdk.game.gameplayStop === 'function') sdk.game.gameplayStop();
      } catch (error) {
        console.warn('[CrazyGames/OpenTTD] gameplayStop failed', error);
      }
      platformGameplayStarted = false;
    }
  }

  window.crazyGamesGameSetGameplay = function(active) {
    gameplayActive = !!active;
    reportGameplay(gameplayActive && !adOpen);
  };

  const setNativePause = paused => {
    try {
      if (typeof Module !== 'undefined' && Module.calledRun === true && typeof Module._em_openttd_set_platform_pause === 'function') {
        Module._em_openttd_set_platform_pause(paused ? 1 : 0);
      }
    } catch (error) {
      console.warn('[CrazyGames/OpenTTD] Platform pause failed', error);
    }
  };

  async function requestAd(type) {
    if (adOpen) return false;
    const sdk = await getSDK();
    if (!sdk || !sdk.ad || typeof sdk.ad.requestAd !== 'function') return false;
    adOpen = true;
    const wasGameplay = gameplayActive;
    reportGameplay(false);
    setNativePause(true);
    if (typeof window.openttdSetPlatformAudioEnabled === 'function') window.openttdSetPlatformAudioEnabled(false);

    return await new Promise(resolve => {
      let done = false;
      const finish = success => {
        if (done) return;
        done = true;
        adOpen = false;
        setNativePause(false);
        if (typeof window.openttdSetPlatformAudioEnabled === 'function') {
          window.openttdSetPlatformAudioEnabled(!window.__crazyGamesMuteAudio);
        }
        if (wasGameplay) reportGameplay(true);
        resolve(!!success);
      };
      try {
        sdk.ad.requestAd(type, {
          adStarted: () => {},
          adFinished: () => finish(true),
          adError: error => { console.info('[CrazyGames/OpenTTD] Ad unavailable', error); finish(false); },
        });
      } catch (error) {
        console.warn('[CrazyGames/OpenTTD] Ad request failed', error);
        finish(false);
      }
    });
  }

  /* These are intentionally not called on a timer. OpenTTD has continuous gameplay,
     so the game may request an ad only from a genuine, non-disruptive break. */
  window.crazyGamesRequestMidgameAd = () => requestAd('midgame');
  window.crazyGamesRequestRewardedAd = () => requestAd('rewarded');

  /* Compatibility aliases required by the verified V28 WebAssembly glue. */
  window.yandexRestoreOpenTTDCloud = window.crazyGamesRestoreOpenTTDCloud;
  window.yandexBackupOpenTTDCloud = window.crazyGamesBackupOpenTTDCloud;
  window.yandexGameSetGameplay = window.crazyGamesGameSetGameplay;
})();
