(() => {
  'use strict';

  const CLOUD_CONFIG_KEY = 'openttdConfigV1';
  const CLOUD_SAVE_KEY = 'openttdSaveV1';
  const CLOUD_VERSION = 1;
  const MAX_RAW_SAVE = 120000;
  const MAX_CLOUD_JSON = 185000;
  const CLOUD_DEBOUNCE_MS = 2500;
  const CLOUD_MIN_WRITE_MS = 10000;
  const AD_MIN_GAMEPLAY_MS = 5 * 60 * 1000;
  const AD_MIN_INTERVAL_MS = 5 * 60 * 1000;

  const sdkReady = window.yandexGamesSDKReady || Promise.resolve(null);
  let playerPromise = null;
  let cloudTimer = 0;
  let cloudWriteInFlight = false;
  let cloudWriteQueued = false;
  let lastCloudWriteAt = 0;

  let gameplayActive = false;
  let gameplayStartedAt = 0;
  let gameplayAccumulatedMs = 0;
  let lastAdAt = 0;
  let adOpen = false;
  let pageVisible = !document.hidden;
  let yandexPauseEventActive = false;
  let platformGameplayStarted = false;
  let resumeMusicAfterPause = false;

  function getPlayer() {
    if (!playerPromise) {
      playerPromise = sdkReady.then(async ysdk => {
        if (!ysdk || typeof ysdk.getPlayer !== 'function') return null;
        try {
          return await ysdk.getPlayer();
        } catch (e) {
          console.warn('Yandex player init failed', e);
          return null;
        }
      });
    }
    return playerPromise;
  }
  window.yandexPlayerReady = getPlayer();

  function bytesToBase64(bytes) {
    let out = '';
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      out += String.fromCharCode(...bytes.subarray(i, Math.min(bytes.length, i + chunk)));
    }
    return btoa(out);
  }

  function base64ToBytes(value) {
    const raw = atob(value || '');
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
    return bytes;
  }

  function ensureDir(FS, path) {
    const parts = path.split('/').filter(Boolean);
    let current = '';
    for (const part of parts) {
      current += '/' + part;
      try { FS.mkdir(current); } catch (e) {}
    }
  }

  function statTime(stat) {
    try {
      if (!stat || stat.mtime == null) return 0;
      return Number(stat.mtime) || 0;
    } catch (e) {
      return 0;
    }
  }

  function listFilesRecursive(FS, root, output = []) {
    let entries;
    try { entries = FS.readdir(root); } catch (e) { return output; }
    for (const name of entries) {
      if (name === '.' || name === '..') continue;
      const path = root.replace(/\/$/, '') + '/' + name;
      let stat;
      try { stat = FS.stat(path); } catch (e) { continue; }
      if (FS.isDir(stat.mode)) {
        listFilesRecursive(FS, path, output);
      } else if (FS.isFile(stat.mode)) {
        output.push({ path, stat });
      }
    }
    return output;
  }

  function newestSave(FS, personalDir) {
    const candidates = listFilesRecursive(FS, personalDir)
      .filter(item => /\.sav$/i.test(item.path))
      .sort((a, b) => statTime(b.stat) - statTime(a.stat));
    return candidates.length ? candidates[0] : null;
  }

  function readConfig(FS, personalDir) {
    try {
      return FS.readFile(personalDir + '/openttd.cfg', { encoding: 'utf8' });
    } catch (e) {
      return '';
    }
  }

  function buildCloudPayload(FS, personalDir) {
    const payload = {};
    payload[CLOUD_CONFIG_KEY] = {
      version: CLOUD_VERSION,
      updatedAt: Date.now(),
      config: readConfig(FS, personalDir),
    };

    const save = newestSave(FS, personalDir);
    if (save) {
      try {
        const bytes = FS.readFile(save.path);
        if (bytes.length <= MAX_RAW_SAVE) {
          const cloudSave = {
            version: CLOUD_VERSION,
            updatedAt: Date.now(),
            name: save.path.split('/').pop(),
            mtime: statTime(save.stat) || Date.now(),
            data: bytesToBase64(bytes),
          };
          const saveOnlyPayload = {};
          saveOnlyPayload[CLOUD_SAVE_KEY] = cloudSave;
          if (JSON.stringify(saveOnlyPayload).length <= MAX_CLOUD_JSON) {
            payload[CLOUD_SAVE_KEY] = cloudSave;
          }
        } else {
          console.info(
            'OpenTTD cloud: latest save is larger than the Yandex player-data budget; keeping this newer save locally.',
            bytes.length,
          );
        }
      } catch (e) {
        console.warn('OpenTTD cloud: could not read latest save', e);
      }
    }

    return payload;
  }

  function restoreCloudConfig(FS, personalDir, cloudConfig) {
    if (!cloudConfig || cloudConfig.version !== CLOUD_VERSION || typeof cloudConfig.config !== 'string') return;
    const configPath = personalDir + '/openttd.cfg';
    let local = '';
    try { local = FS.readFile(configPath, { encoding: 'utf8' }); } catch (e) {}

    /* Do not overwrite an established local profile. On a new browser the
       Yandex language bootstrap may already have created a tiny config; keep
       that locale choice and let the user's local settings become authoritative. */
    if (!local.trim()) {
      try { FS.writeFile(configPath, cloudConfig.config); } catch (e) {}
    }
  }

  function restoreCloudSave(FS, personalDir, cloudSave) {
    if (!cloudSave || cloudSave.version !== CLOUD_VERSION || !cloudSave.data || !cloudSave.name) return false;
    try {
      const localSave = newestSave(FS, personalDir);
      const localMtime = localSave ? statTime(localSave.stat) : 0;
      const cloudMtime = Number(cloudSave.mtime || cloudSave.updatedAt || 0);
      if (localSave && localMtime >= cloudMtime) return false;

      const bytes = base64ToBytes(cloudSave.data);
      if (!bytes.length || bytes.length > MAX_RAW_SAVE) return false;

      const saveDir = personalDir + '/save';
      ensureDir(FS, saveDir);
      const safeName = String(cloudSave.name).replace(/[^A-Za-z0-9_. ()\-]/g, '_');
      const savePath = saveDir + '/' + safeName;
      FS.writeFile(savePath, bytes);
      try {
        const date = new Date(cloudMtime || Date.now());
        FS.utime(savePath, date, date);
      } catch (e) {}
      console.info('OpenTTD cloud: restored newer save', safeName);
      return true;
    } catch (e) {
      console.warn('OpenTTD cloud: could not restore save', e);
      return false;
    }
  }

  window.yandexRestoreOpenTTDCloud = async function(FS, personalDir) {
    const player = await Promise.race([
      getPlayer(),
      new Promise(resolve => setTimeout(() => resolve(null), 3000)),
    ]);
    if (!player || typeof player.getData !== 'function') return;

    try {
      const data = await player.getData([CLOUD_CONFIG_KEY, CLOUD_SAVE_KEY]);
      restoreCloudConfig(FS, personalDir, data && data[CLOUD_CONFIG_KEY]);
      const restored = restoreCloudSave(FS, personalDir, data && data[CLOUD_SAVE_KEY]);
      if (restored && typeof FS.syncfs === 'function') {
        await new Promise(resolve => FS.syncfs(false, () => resolve()));
      }
    } catch (e) {
      console.warn('OpenTTD cloud restore failed', e);
    }
  };

  async function flushCloud(FS, personalDir) {
    if (cloudWriteInFlight) {
      cloudWriteQueued = true;
      return;
    }

    const wait = CLOUD_MIN_WRITE_MS - (Date.now() - lastCloudWriteAt);
    if (wait > 0) {
      clearTimeout(cloudTimer);
      cloudTimer = setTimeout(() => flushCloud(FS, personalDir), wait);
      return;
    }

    cloudWriteInFlight = true;
    try {
      const player = await getPlayer();
      if (!player || typeof player.setData !== 'function') return;
      const payload = buildCloudPayload(FS, personalDir);

      /* If the newest save is too large, CLOUD_SAVE_KEY is intentionally
         omitted so the last valid cloud save is not erased. */
      if (JSON.stringify(payload).length > 195000) delete payload[CLOUD_SAVE_KEY];
      await player.setData(payload, true);
      lastCloudWriteAt = Date.now();
    } catch (e) {
      console.warn('OpenTTD cloud backup failed', e);
    } finally {
      cloudWriteInFlight = false;
      if (cloudWriteQueued) {
        cloudWriteQueued = false;
        clearTimeout(cloudTimer);
        cloudTimer = setTimeout(() => flushCloud(FS, personalDir), CLOUD_DEBOUNCE_MS);
      }
    }
  }

  window.yandexBackupOpenTTDCloud = function(FS, personalDir) {
    clearTimeout(cloudTimer);
    cloudTimer = setTimeout(() => flushCloud(FS, personalDir), CLOUD_DEBOUNCE_MS);
  };

  function setGamePlatformPaused(paused) {
    try {
      if (typeof Module !== 'undefined' && typeof Module._em_openttd_set_platform_pause === 'function') {
        Module._em_openttd_set_platform_pause(paused ? 1 : 0);
        return true;
      }
    } catch (e) {
      console.warn('OpenTTD platform pause bridge failed', e);
    }
    return false;
  }

  function shouldPlatformPause() {
    return adOpen || !pageVisible || yandexPauseEventActive;
  }

  function updatePlatformPause() {
    setGamePlatformPaused(shouldPlatformPause());
  }

  function currentMusicAudio() {
    try {
      return (typeof Module !== 'undefined' && Module.openTTDWebMusic) ? Module.openTTDWebMusic.audio : null;
    } catch (e) {
      return null;
    }
  }

  function getSDLContext() {
    try {
      if (typeof SDL2 !== 'undefined' && SDL2.audioContext) return SDL2.audioContext;
      if (typeof Module !== 'undefined' && Module.SDL2 && Module.SDL2.audioContext) return Module.SDL2.audioContext;
    } catch (e) {}
    return null;
  }

  function suspendAudio() {
    try {
      const audio = currentMusicAudio();
      resumeMusicAfterPause = !!(audio && !audio.paused && !audio.ended);
      if (audio) audio.pause();
    } catch (e) {}
    try {
      const ctx = getSDLContext();
      if (ctx && ctx.state === 'running') ctx.suspend().catch(() => {});
    } catch (e) {}
  }

  function resumeAudio() {
    if (shouldPlatformPause()) return;
    try {
      const ctx = getSDLContext();
      if (ctx && ctx.state === 'suspended') ctx.resume().catch(() => {});
    } catch (e) {}
    try {
      const audio = currentMusicAudio();
      if (resumeMusicAfterPause && audio && audio.paused && !audio.ended) audio.play().catch(() => {});
    } catch (e) {}
    resumeMusicAfterPause = false;
  }

  async function setPlatformGameplay(active) {
    const ysdk = await sdkReady;
    const api = ysdk && ysdk.features && ysdk.features.GameplayAPI;
    if (!api) return;
    const shouldStart = !!active && !shouldPlatformPause();
    if (shouldStart === platformGameplayStarted) return;

    try {
      if (shouldStart && typeof api.start === 'function') {
        api.start();
        platformGameplayStarted = true;
      } else if (!shouldStart && typeof api.stop === 'function') {
        api.stop();
        platformGameplayStarted = false;
      }
    } catch (e) {
      console.warn('Yandex GameplayAPI state change failed', e);
    }
  }

  async function maybeShowInterstitial() {
    if (adOpen || gameplayAccumulatedMs < AD_MIN_GAMEPLAY_MS || Date.now() - lastAdAt < AD_MIN_INTERVAL_MS) return;
    const ysdk = await sdkReady;
    if (!ysdk || !ysdk.adv || typeof ysdk.adv.showFullscreenAdv !== 'function') return;

    gameplayAccumulatedMs = 0;
    lastAdAt = Date.now();
    adOpen = true;
    updatePlatformPause();
    await setPlatformGameplay(false);
    suspendAudio();

    let finished = false;
    const finish = () => {
      if (finished) return;
      finished = true;
      adOpen = false;
      updatePlatformPause();
      resumeAudio();
      setPlatformGameplay(gameplayActive);
    };

    try {
      ysdk.adv.showFullscreenAdv({
        callbacks: {
          onOpen: () => {},
          onClose: () => finish(),
          onError: error => {
            console.warn('Yandex fullscreen ad failed', error);
            finish();
          },
        },
      });
    } catch (e) {
      console.warn('Yandex fullscreen ad exception', e);
      finish();
    }
  }

  window.yandexGameSetGameplay = function(active) {
    active = !!active;
    if (active === gameplayActive) {
      setPlatformGameplay(active);
      return;
    }

    const now = Date.now();
    if (gameplayActive && gameplayStartedAt) {
      gameplayAccumulatedMs += Math.max(0, now - gameplayStartedAt);
      gameplayStartedAt = 0;
    }

    gameplayActive = active;
    if (active) {
      gameplayStartedAt = now;
      setPlatformGameplay(true);
    } else {
      setPlatformGameplay(false);
      maybeShowInterstitial();
    }
  };

  function platformPauseEvent() {
    yandexPauseEventActive = true;
    updatePlatformPause();
    setPlatformGameplay(false);
    suspendAudio();
  }

  function platformResumeEvent() {
    yandexPauseEventActive = false;
    pageVisible = !document.hidden;
    updatePlatformPause();
    resumeAudio();
    setPlatformGameplay(gameplayActive);
  }

  sdkReady.then(ysdk => {
    if (!ysdk || typeof ysdk.on !== 'function') return;
    try {
      ysdk.on('game_api_pause', platformPauseEvent);
      ysdk.on('game_api_resume', platformResumeEvent);
    } catch (e) {
      console.warn('Yandex pause/resume event subscription failed', e);
    }
  });

  document.addEventListener('visibilitychange', () => {
    pageVisible = !document.hidden;
    updatePlatformPause();
    if (!pageVisible) {
      setPlatformGameplay(false);
      suspendAudio();
    } else {
      resumeAudio();
      setPlatformGameplay(gameplayActive);
    }
  });

  window.addEventListener('blur', () => {
    pageVisible = false;
    updatePlatformPause();
    setPlatformGameplay(false);
    suspendAudio();
  });

  window.addEventListener('focus', () => {
    pageVisible = !document.hidden;
    updatePlatformPause();
    resumeAudio();
    setPlatformGameplay(gameplayActive);
  });

  /* The Yandex startup ad can pause the page before the WebAssembly export is
     ready. Re-apply the platform state for the first few seconds so OpenTTD
     cannot begin advancing underneath a platform overlay. */
  let startupPausePolls = 0;
  const startupPauseTimer = setInterval(() => {
    updatePlatformPause();
    startupPausePolls++;
    if (startupPausePolls >= 40) clearInterval(startupPauseTimer);
  }, 250);
})();
