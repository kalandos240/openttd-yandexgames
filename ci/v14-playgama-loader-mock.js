(() => {
  const storageData = new Map();
  window.__openttdPlatformStartupIndependent = true;
  window.bridge = {
    version: 'v14-final-smoke', engine: 'javascript',
    PLATFORM_MESSAGE: { GAME_READY: 'game_ready', GAMEPLAY_STARTED: 'gameplay_started', GAMEPLAY_STOPPED: 'gameplay_stopped' },
    EVENT_NAME: { PAUSE_STATE_CHANGED: 'pause_state_changed', AUDIO_STATE_CHANGED: 'audio_state_changed', INTERSTITIAL_STATE_CHANGED: 'interstitial_state_changed' },
    INTERSTITIAL_STATE: { OPENED: 'opened', CLOSED: 'closed', FAILED: 'failed' },
    STORAGE_TYPE: { PLATFORM_INTERNAL: 'platform_internal' },
    async initialize() { return true; },
    platform: {
      language: 'en', id: 'playgama-v14-final-smoke', isAudioEnabled: true,
      on() {}, off() {}, async sendMessage() { return true; }
    },
    storage: {
      async isSupported() { return true; }, async isAvailable() { return true; },
      async get(key) { return Array.isArray(key) ? key.map(k => storageData.get(String(k)) ?? null) : (storageData.get(String(key)) ?? null); },
      async set(key, value) {
        if (Array.isArray(key)) key.forEach((k, i) => storageData.set(String(k), Array.isArray(value) ? value[i] : value));
        else storageData.set(String(key), value);
        return true;
      }
    },
    advertisement: { isInterstitialSupported: false, setMinimumDelayBetweenInterstitial() {}, on() {}, off() {}, showInterstitial() {} },
    player: { id: 'v14-final-player', isAuthorizationSupported: false, isAuthorized: true, async authorize() { return true; } },
    leaderboards: { type: 'not_available', async getEntries() { return []; }, async setScore() { return true; } }
  };
  document.documentElement.dataset.playgamaBridge = 'ready';
  window.playgamaBridgeScriptReady = Promise.resolve(window.bridge);
})();
