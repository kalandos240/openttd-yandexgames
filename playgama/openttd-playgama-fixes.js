/* OpenTTD-specific Playgama QA/runtime fixes.
 * Loaded after yandex-bridge.js and before openttd-runtime.js.
 */
(() => {
  'use strict';
  if (window.__openttdPlaygamaFixesInstalled) return;
  window.__openttdPlaygamaFixesInstalled = true;

  /* OpenTTD 15.3 AI compatibility chain for bundled SimpleAI 14 (API 1.2).
   * Derived from OpenTTD 15.3 bin/ai/compat_*.nut, GPL-2.0.
   * OpenTTD loads every intermediate API downgrade, so the complete 15 -> 1.2
   * chain must exist in AI_DIR before AIInstance::Initialize(). */
  const AI_COMPAT_SCRIPTS = Object.freeze({
  "compat_14.nut": `/* OpenTTD 15.3: downgrade API 15 -> 14. GPL-2.0. */
AIBridge.GetBridgeID <- AIBridge.GetBridgeType;

class AICompat14 {
\tfunction Text(text)
\t{
\t\tif (typeof text == "string") return text;
\t\treturn null;
\t}
}

AIBaseStation.SetNameCompat14 <- AIBaseStation.SetName;
AIBaseStation.SetName <- function(id, name) { return AIBaseStation.SetNameCompat14(id, AICompat14.Text(name)); }

AICompany.SetNameCompat14 <- AICompany.SetName;
AICompany.SetName <- function(name) { return AICompany.SetNameCompat14(AICompat14.Text(name)); }
AICompany.SetPresidentNameCompat14 <- AICompany.SetPresidentName;
AICompany.SetPresidentName <- function(name) { return AICompany.SetPresidentNameCompat14(AICompat14.Text(name)); }

AIGroup.SetNameCompat14 <- AIGroup.SetName;
AIGroup.SetName <- function(id, name) { return AIGroup.SetNameCompat14(id, AICompat14.Text(name)); }

AISign.BuildSignCompat14 <- AISign.BuildSign;
AISign.BuildSign <- function(id, name) { return AISign.BuildSignCompat14(id, AICompat14.Text(name)); }

AITown.FoundTownCompat14 <- AITown.FoundTown;
AITown.FoundTown <- function(tile, size, city, layout, name) { return AITown.FoundTownCompat14(tile, size, city, layout, AICompat14.Text(name)); }

AIVehicle.SetNameCompat14 <- AIVehicle.SetName;
AIVehicle.SetName <- function(id, name) { return AIVehicle.SetNameCompat14(id, AICompat14.Text(name)); }

AIObject.constructorCompat14 <- AIObject.constructor;
foreach(name, object in CompatScriptRootTable) {
\tif (type(object) != "class") continue;
\tif (!object.rawin("constructor")) continue;
\tif (object.constructor != AIObject.constructorCompat14) continue;
\tobject.constructor <- function() : (name) { AILog.Error("'" + name + "' is not instantiable"); }
}
`,
  "compat_13.nut": `/* OpenTTD 15.3: downgrade API 14 -> 13. GPL-2.0. */\n`,
  "compat_12.nut": `/* OpenTTD 15.3: downgrade API 13 -> 12. GPL-2.0. */
AIRoad.HasRoadTypeCompat12 <- AIRoad.HasRoadType;
AIRoad.HasRoadType <- function(tile, road_type)
{
\tlocal list = AIRoadTypeList(AIRoad.GetRoadTramType(road_type));
\tforeach (rt, _ in list) {
\t\tif (AIRoad.HasRoadTypeCompat12(tile, rt)) {
\t\t\treturn true;
\t\t}
\t}
\treturn false;
}
`,
  "compat_1.11.nut": `/* OpenTTD 15.3: downgrade API 12 -> 1.11. GPL-2.0. */\n`,
  "compat_1.10.nut": `/* OpenTTD 15.3: downgrade API 1.11 -> 1.10. GPL-2.0. */\n`,
  "compat_1.9.nut": `/* OpenTTD 15.3: downgrade API 1.10 -> 1.9. GPL-2.0. */\n`,
  "compat_1.8.nut": `/* OpenTTD 15.3: downgrade API 1.9 -> 1.8. GPL-2.0. */
AIBridge.GetNameCompat1_8 <- AIBridge.GetName;
AIBridge.GetName <- function(bridge_id)
{
\treturn AIBridge.GetNameCompat1_8(bridge_id, AIVehicle.VT_RAIL);
}

AIGroup.CreateGroupCompat1_8 <- AIGroup.CreateGroup;
AIGroup.CreateGroup <- function(vehicle_type)
{
\treturn AIGroup.CreateGroupCompat1_8(vehicle_type, AIGroup.GROUP_INVALID);
}
`,
  "compat_1.7.nut": `/* OpenTTD 15.3: downgrade API 1.8 -> 1.7. GPL-2.0. */\n`,
  "compat_1.6.nut": `/* OpenTTD 15.3: downgrade API 1.7 -> 1.6. GPL-2.0. */\n`,
  "compat_1.5.nut": `/* OpenTTD 15.3: downgrade API 1.6 -> 1.5. GPL-2.0. */\n`,
  "compat_1.4.nut": `/* OpenTTD 15.3: downgrade API 1.5 -> 1.4. GPL-2.0. */\n`,
  "compat_1.3.nut": `/* OpenTTD 15.3: downgrade API 1.4 -> 1.3. GPL-2.0. */\n`,
  "compat_1.2.nut": `/* OpenTTD 15.3: downgrade API 1.3 -> 1.2. GPL-2.0. */\n`
});

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

  const installAICompatibility = (FS, personalDir) => {
    const scripts = AI_COMPAT_SCRIPTS;

    const aiDir = personalDir + '/ai';
    ensureDir(FS, aiDir);
    let installed = 0;
    for (const [filename, source] of Object.entries(scripts)) {
      const fullPath = aiDir + '/' + filename;
      try {
        let same = false;
        try { same = FS.readFile(fullPath, { encoding: 'utf8' }) === source; } catch (_) {}
        if (!same) FS.writeFile(fullPath, source);
        installed++;
      } catch (error) {
        console.error('[Playgama/OpenTTD] Could not install AI API compatibility script', filename, error);
      }
    }

    window.__openttdAICompatInstalled = installed;
    if (installed !== 13) {
      console.error('[Playgama/OpenTTD] Incomplete AI compatibility chain:', installed, '/ 13');
    } else {
      console.info('[Playgama/OpenTTD] AI compatibility chain 15 -> 1.2 installed (13 scripts)');
    }
    return installed;
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
     before OpenTTD main() starts. That is the safe point to install AI tar files,
     the native API compatibility chain, and platform settings. */
  const originalRestore = window.yandexRestoreOpenTTDCloud;
  window.yandexRestoreOpenTTDCloud = async function(FS, personalDir) {
    /* Install before restore so even an empty/first-launch profile is complete.
       Install again after restore because cloud data may replace the local AI dir. */
    installClassicAI(FS, personalDir);
    installAICompatibility(FS, personalDir);
    if (typeof originalRestore === 'function') await originalRestore(FS, personalDir);
    installClassicAI(FS, personalDir);
    installAICompatibility(FS, personalDir);
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
