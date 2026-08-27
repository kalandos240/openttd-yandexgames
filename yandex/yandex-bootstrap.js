/* Yandex Games SDK bootstrap for the OpenTTD web build.
 *
 * The Yandex-hosted archive uses /sdk.js as recommended by Yandex Games.
 * When the exact same build is opened from another URL/domain, the loader can
 * fall back to the documented absolute SDK URL. SDK loading is asynchronous and
 * must never block the OpenTTD runtime from starting.
 */
(() => {
  'use strict';

  const YANDEX_RELATIVE_SDK = '/sdk.js';
  const YANDEX_ABSOLUTE_SDK = 'https://sdk.games.s3.yandex.net/sdk.js';
  const SCRIPT_TIMEOUT_MS = 6000;

  window.yandexGameLanguage = navigator.language || 'en';

  const loadScript = (src) => new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    const timer = setTimeout(() => {
      script.remove();
      reject(new Error(`Timed out loading ${src}`));
    }, SCRIPT_TIMEOUT_MS);
    script.onload = () => {
      clearTimeout(timer);
      resolve();
    };
    script.onerror = () => {
      clearTimeout(timer);
      reject(new Error(`Could not load ${src}`));
    };
    document.head.appendChild(script);
  });

  const ensureYandexSdk = async () => {
    if (window.YaGames && typeof window.YaGames.init === 'function') return;

    try {
      await loadScript(YANDEX_RELATIVE_SDK);
    } catch (relativeError) {
      console.info('Yandex /sdk.js is unavailable at this URL; trying the documented absolute SDK URL.', relativeError);
      if (!window.YaGames || typeof window.YaGames.init !== 'function') {
        await loadScript(YANDEX_ABSOLUTE_SDK);
      }
    }

    if (!window.YaGames || typeof window.YaGames.init !== 'function') {
      throw new Error('Yandex Games SDK loaded without YaGames.init');
    }
  };

  window.yandexGamesSDKReady = (async () => {
    if (location.protocol === 'file:') return null;
    try {
      await ensureYandexSdk();
      const ysdk = await window.YaGames.init();
      window.ysdk = ysdk;
      window.yandexGameLanguage =
        (ysdk?.environment?.i18n?.lang) || window.yandexGameLanguage;
      return ysdk;
    } catch (error) {
      console.warn('Yandex Games SDK initialization failed; OpenTTD will continue with local persistence.', error);
      return null;
    }
  })();
})();
