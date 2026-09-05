(() => {
  'use strict';
  if (window.__openttdCrazyGamesBootstrapInstalled) return;
  window.__openttdCrazyGamesBootstrapInstalled = true;

  const language = navigator.language || 'en';
  window.crazyGamesGameLanguage = language;
  /* Compatibility aliases used by the existing OpenTTD WebAssembly glue. */
  window.yandexGameLanguage = language;

  const applySettings = settings => {
    const muteAudio = !!(settings && settings.muteAudio);
    window.__crazyGamesMuteAudio = muteAudio;
    if (typeof window.openttdSetPlatformAudioEnabled === 'function') {
      window.openttdSetPlatformAudioEnabled(!muteAudio);
    }
  };

  window.crazyGamesSDKReady = (async () => {
    try {
      const sdk = window.CrazyGames && window.CrazyGames.SDK;
      if (!sdk || typeof sdk.init !== 'function') throw new Error('CrazyGames SDK v3 is unavailable');
      await sdk.init();
      window.crazyGamesSDK = sdk;

      try {
        if (sdk.game && typeof sdk.game.loadingStart === 'function') sdk.game.loadingStart();
      } catch (error) {
        console.warn('[CrazyGames/OpenTTD] loadingStart failed', error);
      }

      try {
        applySettings(sdk.game && sdk.game.settings);
        if (sdk.game && typeof sdk.game.addSettingsChangeListener === 'function') {
          sdk.game.addSettingsChangeListener(applySettings);
        }
      } catch (error) {
        console.warn('[CrazyGames/OpenTTD] settings integration failed', error);
      }

      window.dispatchEvent(new CustomEvent('openttd-crazygames-language-ready'));
      return sdk;
    } catch (error) {
      console.warn('[CrazyGames/OpenTTD] SDK initialization failed; continuing without platform services', error);
      return null;
    }
  })();

  /* The native runtime in the verified V28 binary still looks up this promise. */
  window.yandexGamesSDKReady = window.crazyGamesSDKReady;
})();
