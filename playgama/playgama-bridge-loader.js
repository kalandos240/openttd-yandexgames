/* Load Playgama Bridge asynchronously without parser-blocking external script.
 * The game runtime must start even if this CDN request hangs or is blocked.
 */
(() => {
  'use strict';
  if (window.playgamaBridgeScriptReady) return;
  window.__openttdPlatformStartupIndependent = true;
  window.playgamaBridgeScriptReady = new Promise((resolve) => {
    const script = document.createElement('script');
    script.src = 'https://bridge.playgama.com/v2/stable/playgama-bridge.js';
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => {
      console.warn('[Playgama/OpenTTD] Bridge CDN unavailable; continuing with local game startup.');
      resolve(false);
    };
    (document.head || document.documentElement).appendChild(script);
  });
})();
