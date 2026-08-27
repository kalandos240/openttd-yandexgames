/* Keep the OpenTTD SDL surface pixel-for-pixel aligned with the browser viewport.
 *
 * CSS alone can remove the old 16:9 letterbox, but stretching a fixed-size
 * canvas would distort the game. Emscripten exposes Module.setCanvasSize(),
 * which updates the backing canvas and notifies SDL's resize listeners. Use
 * CSS-pixel dimensions so OpenTTD UI scale remains stable across DPR values.
 */
(() => {
  'use strict';
  if (window.__openttdFullViewportInstalled) return;
  window.__openttdFullViewportInstalled = true;

  const size = () => ({
    width: Math.max(64, Math.round(window.visualViewport?.width || window.innerWidth || document.documentElement.clientWidth || 1280)),
    height: Math.max(64, Math.round(window.visualViewport?.height || window.innerHeight || document.documentElement.clientHeight || 720)),
  });

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
