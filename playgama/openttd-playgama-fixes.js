/* OpenTTD-specific Playgama QA/runtime fixes.
 * Loaded after yandex-bridge.js and before openttd-runtime.js.
 */
(() => {
  'use strict';
  if (window.__openttdPlaygamaFixesInstalled) return;
  window.__openttdPlaygamaFixesInstalled = true;

  const COMPETITORS = 3;
  let platformPaused = false;
  let platformAudioEnabled = true;
  let visibilityPaused = document.hidden;
  let mainLoopPaused = false;
  let musicWasPlatformPaused = false;

  /* Keep the native 16:9 OpenTTD surface intact on square/tall QA viewports.
     The original OpenTTD background remains full-bleed behind the game. */
  const style = document.createElement('style');
  style.id = 'openttd-playgama-scale-fix';
  style.textContent = `
    html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; background: #1f2f22; }
    body { position: relative; }
    div.background { position: fixed !important; inset: 0 !important; width: 100vw !important; height: 100vh !important; background-size: cover !important; background-position: center !important; }
    canvas.emscripten {
      position: absolute !important;
      left: 50% !important;
      top: 50% !important;
      transform: translate(-50%, -50%) !important;
      width: min(100vw, calc(100vh * 16 / 9)) !important;
      height: min(100vh, calc(100vw * 9 / 16)) !important;
      max-width: 100vw !important;
      max-height: 100vh !important;
      aspect-ratio: 16 / 9 !important;
    }
  `;
  document.head.appendChild(style);

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

  const installClassicAI = (FS, personalDir) => {
    const bundle = window.__openttdClassicAIArchives;
    if (!bundle || typeof bundle !== 'object') return;
    for (const [relativePath, encoded] of Object.entries(bundle)) {
      const fullPath = personalDir + '/' + relativePath;
      ensureDir(FS, fullPath.slice(0, fullPath.lastIndexOf('/')));
      try {
        const bytes = base64ToBytes(encoded);
        let same = false;
        try { same = FS.stat(fullPath).size === bytes.length; } catch (_) {}
        if (!same) FS.writeFile(fullPath, bytes);
      } catch (error) {
        console.warn('[Playgama/OpenTTD] Could not install bundled AI file', relativePath, error);
      }
    }
  };

  const forcePlatformConfig = (FS, personalDir) => {
    const path = personalDir + '/openttd.cfg';
    let config = '';
    try { config = FS.readFile(path, { encoding: 'utf8' }); } catch (_) {}

    const locale = String(window.yandexGameLanguage || navigator.language || 'en').toLowerCase();
    const language = locale.startsWith('ru') ? 'russian.lng' : 'english.lng';
    if (/^language\s*=.*$/m.test(config)) {
      config = config.replace(/^language\s*=.*$/m, 'language = ' + language);
    } else if (/^\[misc\]\s*$/m.test(config)) {
      config = config.replace(/^\[misc\]\s*$/m, '[misc]\nlanguage = ' + language);
    } else {
      config = '[misc]\nlanguage = ' + language + '\n\n' + config;
    }

    if (/^max_no_competitors\s*=.*$/m.test(config)) {
      config = config.replace(/^max_no_competitors\s*=.*$/m, 'max_no_competitors = ' + COMPETITORS);
    } else if (/^\[difficulty\]\s*$/m.test(config)) {
      config = config.replace(/^\[difficulty\]\s*$/m, '[difficulty]\nmax_no_competitors = ' + COMPETITORS);
    } else {
      config += (config && !config.endsWith('\n') ? '\n' : '') + '[difficulty]\nmax_no_competitors = ' + COMPETITORS + '\n';
    }

    try { FS.writeFile(path, config); } catch (error) {
      console.warn('[Playgama/OpenTTD] Could not apply platform language/AI config', error);
    }
  };

  /* The cloud restore hook runs after IDBFS has been mounted and loaded, but
     before OpenTTD main() starts. That is the safe point to install AI tar files
     and to make platform language authoritative for the current launch. */
  const originalRestore = window.yandexRestoreOpenTTDCloud;
  window.yandexRestoreOpenTTDCloud = async function(FS, personalDir) {
    installClassicAI(FS, personalDir);
    if (typeof originalRestore === 'function') await originalRestore(FS, personalDir);
    installClassicAI(FS, personalDir);
    forcePlatformConfig(FS, personalDir);
  };

  const currentMusic = () => {
    try { return Module?.openTTDWebMusic?.audio || null; } catch (_) { return null; }
  };

  const audioContext = () => {
    try {
      if (typeof SDL2 !== 'undefined' && SDL2.audioContext) return SDL2.audioContext;
      if (Module?.SDL2?.audioContext) return Module.SDL2.audioContext;
    } catch (_) {}
    return null;
  };

  const shouldHardPause = () => platformPaused || visibilityPaused;

  const suspendAudio = () => {
    try {
      const audio = currentMusic();
      if (audio && !audio.paused && !audio.ended) {
        musicWasPlatformPaused = true;
        audio.pause();
      }
    } catch (_) {}
    try {
      const ctx = audioContext();
      if (ctx?.state === 'running') ctx.suspend().catch(() => {});
    } catch (_) {}
  };

  const resumeAudio = () => {
    if (shouldHardPause() || !platformAudioEnabled || document.hidden) return;
    try {
      const ctx = audioContext();
      if (ctx?.state === 'suspended') ctx.resume().catch(() => {});
    } catch (_) {}
    try {
      const audio = currentMusic();
      if (audio && audio.paused && !audio.ended && (musicWasPlatformPaused || !audio.error)) {
        audio.play().then(() => { musicWasPlatformPaused = false; }).catch(() => {});
      }
    } catch (_) {}
  };

  const applyHardPause = () => {
    const paused = shouldHardPause();
    try {
      if (Module?._em_openttd_set_platform_pause) Module._em_openttd_set_platform_pause(paused ? 1 : 0);
    } catch (error) {
      console.warn('[Playgama/OpenTTD] Native platform pause failed', error);
    }

    /* The native pause flag is kept, but also pause Emscripten's main loop.
       This makes the QA pause test deterministic even while a modal platform
       overlay is active. */
    try {
      if (typeof Browser !== 'undefined' && Browser.mainLoop) {
        if (paused && !mainLoopPaused) {
          Browser.mainLoop.pause();
          mainLoopPaused = true;
        } else if (!paused && mainLoopPaused) {
          Browser.mainLoop.resume();
          mainLoopPaused = false;
        }
      }
    } catch (error) {
      console.warn('[Playgama/OpenTTD] Emscripten main-loop pause failed', error);
    }

    if (paused) suspendAudio(); else resumeAudio();
  };

  const bindBridge = (bridge) => {
    if (!bridge) return;
    platformAudioEnabled = bridge.platform?.isAudioEnabled !== false;
    try {
      bridge.platform?.on?.(bridge.EVENT_NAME.PAUSE_STATE_CHANGED, (paused) => {
        platformPaused = paused === true;
        applyHardPause();
      });
    } catch (error) {
      console.warn('[Playgama/OpenTTD] Direct pause subscription failed', error);
    }
    try {
      bridge.platform?.on?.(bridge.EVENT_NAME.AUDIO_STATE_CHANGED, (enabled) => {
        platformAudioEnabled = enabled !== false;
        if (platformAudioEnabled) resumeAudio(); else suspendAudio();
      });
    } catch (error) {
      console.warn('[Playgama/OpenTTD] Direct audio subscription failed', error);
    }
  };

  Promise.resolve(window.playgamaBridgeReady).then(bindBridge).catch(() => {});

  document.addEventListener('visibilitychange', () => {
    visibilityPaused = document.hidden;
    applyHardPause();
  });

  /* Browser autoplay/focus transitions can occasionally leave the HTML music
     element paused without telling OpenTTD. If a live track object still exists,
     retry it; an intentional in-game Stop destroys that object, so this does not
     restart music the player explicitly stopped. */
  const retryMusic = () => {
    if (shouldHardPause() || !platformAudioEnabled || document.hidden) return;
    try {
      const audio = currentMusic();
      if (audio && audio.paused && !audio.ended && !audio.error) {
        audio.play().catch(() => {});
      }
    } catch (_) {}
  };
  setInterval(retryMusic, 1500);
  ['pointerdown', 'keydown', 'touchstart'].forEach((eventName) => {
    document.addEventListener(eventName, retryMusic, { capture: true, passive: true });
  });
})();
