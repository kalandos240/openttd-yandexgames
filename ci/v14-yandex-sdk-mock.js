(() => {
  const data = Object.create(null);
  const scores = [];
  const player = {
    async getData(keys) { const out = {}; for (const key of (keys || [])) if (Object.prototype.hasOwnProperty.call(data, key)) out[key] = data[key]; return out; },
    async setData(value) { Object.assign(data, value || {}); return true; },
    getMode() { return 'full'; },
    getUniqueID() { return 'v14-final-smoke-user'; },
    getName() { return 'V14 Final Smoke'; },
    isAuthorized() { return true; }
  };
  const ysdk = {
    environment: { i18n: { lang: 'en' }, app: { id: 'v14-final-smoke' } },
    features: {
      LoadingAPI: { ready() { document.documentElement.dataset.yandexLoadingReady = 'ready'; return Promise.resolve(true); } },
      GameplayAPI: {
        start() { document.documentElement.dataset.yandexGameplay = 'started'; return Promise.resolve(true); },
        stop() { document.documentElement.dataset.yandexGameplay = 'stopped'; return Promise.resolve(true); }
      }
    },
    adv: { showFullscreenAdv({ callbacks } = {}) { callbacks?.onOpen?.(); callbacks?.onClose?.(true); } },
    leaderboards: {
      async getEntries() { return { entries: scores }; },
      async setScore(name, score) { scores.push({ name, score }); return true; }
    },
    async getPlayer() { return player; },
    isAvailableMethod() { return Promise.resolve(true); },
    on() {}, off() {}
  };
  window.YaGames = { async init() { document.documentElement.dataset.yandexSdk = 'ready'; return ysdk; } };
})();
