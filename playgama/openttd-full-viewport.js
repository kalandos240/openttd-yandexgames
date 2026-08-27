/* Keep the OpenTTD SDL surface pixel-for-pixel aligned with the browser viewport.
 *
 * CSS alone can remove the old 16:9 letterbox, but stretching a fixed-size
 * canvas would distort the game. Emscripten exposes Module.setCanvasSize(),
 * which updates the backing canvas and notifies SDL's resize listeners. Use
 * CSS-pixel dimensions so OpenTTD UI scale remains stable across DPR values.
 *
 * This helper is also deliberately loaded between the platform runtime fixes
 * and cloud-save provider. That lets it preserve/compose both restore hooks and
 * normalize browser-only GUI settings before OpenTTD main() reads openttd.cfg.
 */
(() => {
  'use strict';
  if (window.__openttdFullViewportInstalled) return;
  window.__openttdFullViewportInstalled = true;

  const size = () => ({
    width: Math.max(64, Math.round(window.visualViewport?.width || window.innerWidth || document.documentElement.clientWidth || 1280)),
    height: Math.max(64, Math.round(window.visualViewport?.height || window.innerHeight || document.documentElement.clientHeight || 720)),
  });

  const normalizeBrowserConfig = (FS, personalDir) => {
    if (!FS || !personalDir) return;
    const path = String(personalDir).replace(/\/$/, '') + '/openttd.cfg';
    let config = '';
    try { config = FS.readFile(path, { encoding: 'utf8' }); } catch (_) {}

    if (/^pause_on_newgame\s*=.*$/m.test(config)) {
      config = config.replace(/^pause_on_newgame\s*=.*$/m, 'pause_on_newgame = false');
    } else if (/^\[gui\]\s*$/m.test(config)) {
      config = config.replace(/^\[gui\]\s*$/m, '[gui]\npause_on_newgame = false');
    } else {
      config += (config && !config.endsWith('\n') ? '\n' : '') + '[gui]\npause_on_newgame = false\n';
    }

    try {
      FS.writeFile(path, config);
      window.__openttdBrowserConfigNormalized = true;
    } catch (error) {
      console.warn('[OpenTTD] Could not normalize browser startup config', error);
    }
  };

  /* Runtime fixes historically install a restore wrapper before the Playgama
     cloud provider is loaded. Preserve that inherited wrapper and intercept the
     later provider assignment instead of letting one silently overwrite the
     other. The composed hook finishes by forcing browser-safe startup settings. */
  const inheritedRestore = typeof window.yandexRestoreOpenTTDCloud === 'function'
    ? window.yandexRestoreOpenTTDCloud
    : null;

  let activeRestore = async (FS, personalDir) => {
    if (inheritedRestore) await inheritedRestore(FS, personalDir);
    normalizeBrowserConfig(FS, personalDir);
  };

  try {
    Object.defineProperty(window, 'yandexRestoreOpenTTDCloud', {
      configurable: true,
      enumerable: true,
      get() { return activeRestore; },
      set(providerRestore) {
        const provider = typeof providerRestore === 'function' ? providerRestore : null;
        activeRestore = async (FS, personalDir) => {
          if (provider) await provider(FS, personalDir);
          if (inheritedRestore && inheritedRestore !== provider) await inheritedRestore(FS, personalDir);
          normalizeBrowserConfig(FS, personalDir);
        };
      },
    });
  } catch (error) {
    console.warn('[OpenTTD] Could not compose browser cloud restore hooks', error);
  }

  let raf = 0;
  let lastWidth = 0;
  let lastHeight = 0;

  const apply = () => {
    raf = 0;
    try {
      if (typeof Module === 'undefined' || Module.calledRun !== true || typeof Module.setCanvasSize !== 'function') return false;
      const { width, height } = size();
      if (width === lastWidth && height === lastHeight && Module.canvas?.width === width && Module.canvas?.height === height) return true;
      Module.setCanvasSize(width, height);
      lastWidth = width;
      lastHeight = height;
      return true;
    } catch (error) {
      console.warn('[OpenTTD] Full-viewport resize failed', error);
      return false;
    }
  };

  const schedule = () => {
    if (raf) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => {
      if (!apply()) setTimeout(apply, 50);
    });
  };

  window.addEventListener('resize', schedule, { passive: true });
  window.visualViewport?.addEventListener('resize', schedule, { passive: true });
  document.addEventListener('fullscreenchange', schedule, { passive: true });

  /* The helper is loaded before/around runtime startup in historical packages.
     Poll only until Emscripten has entered main(), then rely on resize events. */
  let attempts = 0;
  const startup = setInterval(() => {
    attempts += 1;
    if (apply() || attempts >= 120) clearInterval(startup);
  }, 100);
})();
