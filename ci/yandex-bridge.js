(() => {
  'use strict';

  const CLOUD_KEY = 'openttdCloudV1';
  const CLOUD_VERSION = 1;
  const MAX_RAW_SAVE = 120000;
  const MAX_CLOUD_JSON = 185000;
  const CLOUD_DEBOUNCE_MS = 2500;
  const AD_MIN_GAMEPLAY_MS = 5 * 60 * 1000;
  const AD_MIN_INTERVAL_MS = 5 * 60 * 1000;

  const sdkReady = window.yandexGamesSDKReady || Promise.resolve(null);
  let playerPromise = null;
  let cloudTimer = 0;
  let cloudWriteInFlight = false;
  let cloudWriteQueued = false;
  let gameplayActive = false;
  let gameplayStartedAt = 0;
  let gameplayAccumulatedMs = 0;
  let lastAdAt = 0;
  let adOpen = false;
  let pageVisible = !document.hidden;
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
      .sort((a, b) => Number(b.stat.mtime || 0) - Number(a.stat.mtime || 0));
    return candidates.length ? candidates[0] : null;
  }

  async function buildCloudSnapshot(FS, personalDir) {
    const snapshot = {
      version: CLOUD_VERSION,
      updatedAt: Date.now(),
      config: '',
      save: null,
    };

    try {
      snapshot.config = FS.readFile(personalDir + '/openttd.cfg', { encoding: 'utf8' });
    } catch (e) {}

    const save = newestSave(FS, personalDir);
    if (save) {
      try {
        const bytes = FS.readFile(save.path);
        if (bytes.length <= MAX_RAW_SAVE) {
          snapshot.save = {
            name: save.path.split('/').pop(),
            mtime: Number(save.stat.mtime || Date.now()),
            data: bytesToBase64(bytes),
          };
        } else {
          console.info('OpenTTD cloud: latest save is larger than the Yandex 200 KB player-data limit; keeping it in local storage only.', bytes.length);
        }
      } catch (e) {
        console.warn('OpenTTD cloud: could not read latest save', e);
      }
    }

    if (JSON.stringify(snapshot).length > MAX_CLOUD_JSON) snapshot.save = null;
    return snapshot;
  }

  window.yandexRestoreOpenTTDCloud = async function(FS, personalDir) {
    const player = await getPlayer();
    if (!player || typeof player.getData !== 'function') return;
    try {
      const data = await player.getData([CLOUD_KEY]);
      const snapshot = data && data[CLOUD_KEY];
      if (!snapshot || snapshot.version !== CLOUD_VERSION) return;

      const configPath = personalDir + '/openttd.cfg';
      let hasConfig = true;
      try { FS.stat(configPath); } catch (e) { hasConfig = false; }
      if (!hasConfig && typeof snapshot.config === 'string' && snapshot.config.length) {
        FS.writeFile(configPath, snapshot.config);
      }

      const localSave = newestSave(FS, personalDir);
      if (!localSave && snapshot.save && snapshot.save.data && snapshot.save.name) {
        const saveDir = personalDir + '/save';
        ensureDir(FS, saveDir);
        const safeName = String(snapshot.save.name).replace(/[^A-Za-z0-9_. ()\-]/g, '_');
        const savePath = saveDir + '/' + safeName;
        FS.writeFile(savePath, base64ToBytes(snapshot.save.data));
        console.info('OpenTTD cloud: restored', safeName);
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
    cloudWriteInFlight = true;
    try {
      const player = await getPlayer();
      if (!player || typeof player.setData !== 'function') return;
      const snapshot = await buildCloudSnapshot(FS, personalDir);
      const payload = {};
      payload[CLOUD_KEY] = snapshot;
      if (JSON.stringify(payload).length > 200000) payload[CLOUD_KEY].save = null;
      await player.setData(payload, true);
    } catch (e) {
      console.warn('OpenTTD cloud backup failed', e);
    } finally {
      cloudWriteInFlight = false;
      if (cloudWriteQueued) {
        cloudWriteQueued = false;
        setTimeout(() => flushCloud(FS, personalDir), CLOUD_DEBOUNCE_MS);
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
      }
    } catch (e) {
      console.warn('OpenTTD platform pause bridge failed', e);
    }
  }

  function updatePlatformPause() {
    setGamePlatformPaused(adOpen || !pageVisible);
  }

  function currentMusicAudio() {
    try {
      return (typeof Module !== 'undefined' && Module.openTTDWebMusic) ? Module.openTTDWebMusic.audio : null;
    } catch (e) {
      return null;
    }
  }

  function suspendAudio() {
    try {
      const audio = currentMusicAudio();
      resumeMusicAfterPause = !!(audio && !audio.paused && !audio.ended);
      if (audio) audio.pause();
    } catch (e) {}
    try {
      if (typeof SDL2 !== 'undefined' && SDL2.audioContext && SDL2.audioContext.state === 'running') SDL2.audioContext.suspend();
    } catch (e) {}
  }

  function resumeAudio() {
    if (!pageVisible || adOpen) return;
    try {
      if (typeof SDL2 !== 'undefined' && SDL2.audioContext && SDL2.audioContext.state === 'suspended') SDL2.audioContext.resume().catch(() => {});
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
    const shouldStart = !!active && pageVisible && !adOpen;
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

    const finish = () => {
      adOpen = false;
      updatePlatformPause();
      resumeAudio();
      setPlatformGameplay(gameplayActive);
    };

    try {
      ysdk.adv.showFullscreenAdv({
        callbacks: {
          onOpen: () => {},
          onClose: finish,
          onError: error => {
            console.warn('Yandex fullscreen ad failed', error);
            finish();
          },
        }
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
})();
