/* Playgama Bridge compatibility layer for the OpenTTD Yandex-style browser integration. */
(() => {
  'use strict';
  if (window.__playgamaYandexCompatInstalled) return;
  window.__playgamaYandexCompatInstalled = true;

  const pauseListeners = new Set();
  const resumeListeners = new Set();
  const pauseReasons = new Set();
  const trackedAudioContexts = new Set();
  const pausedMedia = new Set();
  let pseudoSdk = null;
  let pseudoPlayer = null;
  let gameReadySent = false;
  let gameplayStarted = false;
  let platformAudioEnabled = true;

  const safeCall = (callback, ...args) => {
    try { callback?.(...args); } catch (error) { console.warn('[Playgama] callback failed:', error); }
  };

  const normalizeLanguage = (value) => {
    const code = String(value || navigator.language || 'en').trim().toLowerCase().split(/[-_]/)[0];
    return code || 'en';
  };

  const wrapAudioContext = () => {
    const NativeAudioContext = window.AudioContext || window.webkitAudioContext;
    if (!NativeAudioContext || NativeAudioContext.__playgamaCompatWrapped) return;
    const WrappedAudioContext = new Proxy(NativeAudioContext, {
      construct(target, args, newTarget) {
        const context = Reflect.construct(target, args, newTarget === WrappedAudioContext ? target : newTarget);
        trackedAudioContexts.add(context);
        return context;
      }
    });
    WrappedAudioContext.__playgamaCompatWrapped = true;
    window.AudioContext = WrappedAudioContext;
    if (window.webkitAudioContext === NativeAudioContext) window.webkitAudioContext = WrappedAudioContext;
  };

  const pauseTrackedAudio = () => {
    trackedAudioContexts.forEach((context) => {
      if (context?.state === 'running') context.suspend?.().catch?.(() => {});
    });
    document.querySelectorAll('audio,video').forEach((media) => {
      if (!media.paused) {
        pausedMedia.add(media);
        try { media.pause(); } catch (_) {}
      }
    });
  };

  const resumeTrackedAudio = () => {
    if (pauseReasons.size || !platformAudioEnabled || document.hidden) return;
    trackedAudioContexts.forEach((context) => {
      if (context?.state === 'suspended') context.resume?.().catch?.(() => {});
    });
    Array.from(pausedMedia).forEach((media) => {
      pausedMedia.delete(media);
      try { media.play?.().catch?.(() => {}); } catch (_) {}
    });
  };

  const emitPauseState = () => {
    const paused = pauseReasons.size > 0;
    (paused ? pauseListeners : resumeListeners).forEach((listener) => safeCall(listener));
    if (paused) pauseTrackedAudio(); else resumeTrackedAudio();
  };

  const setPauseReason = (reason, active) => {
    const wasPaused = pauseReasons.size > 0;
    if (active) pauseReasons.add(reason); else pauseReasons.delete(reason);
    if (wasPaused !== (pauseReasons.size > 0)) emitPauseState();
  };

  wrapAudioContext();

  const initializeBridge = async () => {
    if (!window.bridge || typeof window.bridge.initialize !== 'function') {
      throw new Error('Playgama Bridge script is unavailable');
    }

    window.bridge.engine = 'javascript';
    await window.bridge.initialize({ configFilePath: './playgama-bridge-config.json' });
    const bridge = window.bridge;

    const major = Number.parseInt(String(bridge.version || '2').split('.')[0], 10);
    if (Number.isFinite(major) && major < 2) {
      throw new Error(`Playgama Bridge v2+ required, got ${bridge.version}`);
    }
    document.documentElement.dataset.playgamaBridge = 'ready';
    document.documentElement.dataset.playgamaBridgeVersion = String(bridge.version || 'v2');

    try { bridge.advertisement?.setMinimumDelayBetweenInterstitial?.(150); } catch (_) {}

    platformAudioEnabled = bridge.platform?.isAudioEnabled !== false;
    if (!platformAudioEnabled) pauseTrackedAudio();

    try {
      bridge.platform?.on?.(bridge.EVENT_NAME?.PAUSE_STATE_CHANGED || 'pause_state_changed', (paused) => {
        setPauseReason('platform', Boolean(paused));
      });
    } catch (error) {
      console.warn('[Playgama] pause event subscription failed:', error);
    }

    try {
      bridge.platform?.on?.(bridge.EVENT_NAME?.AUDIO_STATE_CHANGED || 'audio_state_changed', (enabled) => {
        platformAudioEnabled = enabled !== false;
        if (platformAudioEnabled) resumeTrackedAudio(); else pauseTrackedAudio();
      });
    } catch (error) {
      console.warn('[Playgama] audio event subscription failed:', error);
    }

    // Storage availability must never be a startup gate.
    try {
      const markerKey = '__openttd_playgama_bridge';
      await Promise.race([
        (async () => {
          await bridge.storage?.get?.(markerKey);
          await bridge.storage?.set?.(markerKey, { updatedAt: Date.now() });
        })(),
        new Promise((resolve) => setTimeout(resolve, 1000)),
      ]);
    } catch (error) {
      console.info('[Playgama] storage marker unavailable; local persistence will still work.', error);
    }

    return bridge;
  };

  window.playgamaBridgeReady = initializeBridge().catch((error) => {
    document.documentElement.dataset.playgamaBridge = 'failed';
    console.warn('[Playgama] Bridge initialization failed:', error);
    return null;
  });

  const createPlayer = (bridge) => {
    if (pseudoPlayer) return pseudoPlayer;
    pseudoPlayer = {
      async getData(keys) {
        const requested = Array.isArray(keys) ? keys : (keys == null ? [] : [keys]);
        const result = {};
        for (const key of requested) {
          try {
            const value = await bridge.storage?.get?.(String(key));
            if (value !== undefined && value !== null) result[key] = value;
          } catch (_) {}
        }
        return result;
      },
      async setData(data) {
        for (const [key, value] of Object.entries(data || {})) {
          try { await bridge.storage?.set?.(String(key), value); } catch (_) {}
        }
      },
      isAuthorized() {
        return bridge.player?.isAuthorized === true || bridge.player?.isAuthorizationSupported === false;
      },
      getMode() { return 'full'; },
      getUniqueID() { return String(bridge.player?.id || ''); },
      getName() { return String(bridge.player?.name || ''); }
    };
    return pseudoPlayer;
  };

  const createFullscreenAd = (bridge) => (options = {}) => {
    const callbacks = options.callbacks || {};
    const advertisement = bridge.advertisement;
    if (!advertisement?.isInterstitialSupported) {
      safeCall(callbacks.onError, new Error('Interstitial advertising is not supported'));
      return;
    }

    const eventName = bridge.EVENT_NAME?.INTERSTITIAL_STATE_CHANGED || 'interstitial_state_changed';
    const openedState = bridge.INTERSTITIAL_STATE?.OPENED || 'opened';
    const closedState = bridge.INTERSTITIAL_STATE?.CLOSED || 'closed';
    const failedState = bridge.INTERSTITIAL_STATE?.FAILED || 'failed';
    let opened = false;
    let finished = false;

    const cleanup = () => advertisement.off?.(eventName, listener);
    const listener = (state) => {
      if (finished) return;
      if (state === openedState) {
        opened = true;
        setPauseReason('interstitial', true);
        safeCall(callbacks.onOpen);
      } else if (state === closedState) {
        finished = true;
        setPauseReason('interstitial', false);
        cleanup();
        safeCall(callbacks.onClose, opened);
      } else if (state === failedState) {
        finished = true;
        setPauseReason('interstitial', false);
        cleanup();
        safeCall(callbacks.onError, new Error('Playgama interstitial failed'));
      }
    };

    advertisement.on?.(eventName, listener);
    try { advertisement.showInterstitial(options.placement || null); }
    catch (error) {
      finished = true;
      cleanup();
      setPauseReason('interstitial', false);
      safeCall(callbacks.onError, error);
    }
  };

  const sendPlatformMessage = async (bridge, message) => {
    try { await bridge.platform?.sendMessage?.(message); }
    catch (error) { console.info(`[Playgama] platform message ${message} was not accepted.`, error); }
  };

  const createLeaderboards = (bridge) => ({
    async setScore(id, score) {
      if (!bridge.leaderboards?.setScore) throw new Error('Leaderboards are unavailable');
      return bridge.leaderboards.setScore(String(id), Number(score));
    },
    async getEntries(id) {
      if (!bridge.leaderboards?.getEntries) throw new Error('Leaderboards are unavailable');
      const rows = await bridge.leaderboards.getEntries(String(id));
      const list = Array.isArray(rows) ? rows : [];
      const ownId = bridge.player?.id == null ? null : String(bridge.player.id);
      let userRank = null;
      const entries = list.map((row) => {
        const rank = Number.isFinite(Number(row?.rank)) ? Number(row.rank) : 0;
        if (ownId !== null && row?.id != null && String(row.id) === ownId) userRank = rank;
        const name = String(row?.name || 'Player');
        return {
          rank,
          score: Number(row?.score || 0),
          player: {
            uniqueID: String(row?.id || ''),
            publicName: name,
            getName() { return name; },
            getAvatarSrc() { return String(row?.photo || ''); }
          }
        };
      });
      return { entries, userRank };
    }
  });

  const createSdk = (bridge) => {
    if (pseudoSdk) return pseudoSdk;
    const player = createPlayer(bridge);

    pseudoSdk = {
      environment: {
        i18n: { lang: normalizeLanguage(bridge.platform?.language) },
        app: { id: bridge.platform?.id || 'playgama' }
      },
      features: {
        LoadingAPI: {
          ready() {
            if (gameReadySent) return Promise.resolve(false);
            gameReadySent = true;
            return sendPlatformMessage(bridge, bridge.PLATFORM_MESSAGE?.GAME_READY || 'game_ready').then(() => true);
          }
        },
        GameplayAPI: {
          start() {
            if (gameplayStarted) return Promise.resolve(false);
            gameplayStarted = true;
            return sendPlatformMessage(bridge, bridge.PLATFORM_MESSAGE?.GAMEPLAY_STARTED || 'gameplay_started').then(() => true);
          },
          stop() {
            if (!gameplayStarted) return Promise.resolve(false);
            gameplayStarted = false;
            return sendPlatformMessage(bridge, bridge.PLATFORM_MESSAGE?.GAMEPLAY_STOPPED || 'gameplay_stopped').then(() => true);
          }
        }
      },
      adv: { showFullscreenAdv: createFullscreenAd(bridge) },
      leaderboards: createLeaderboards(bridge),
      auth: {
        async openAuthDialog() {
          if (!bridge.player?.authorize) throw new Error('Authorization is unavailable');
          return bridge.player.authorize({});
        }
      },
      async getPlayer() { return player; },
      on(eventName, listener) {
        if (eventName === 'game_api_pause') pauseListeners.add(listener);
        else if (eventName === 'game_api_resume') resumeListeners.add(listener);
      },
      off(eventName, listener) {
        if (eventName === 'game_api_pause') pauseListeners.delete(listener);
        else if (eventName === 'game_api_resume') resumeListeners.delete(listener);
      },
      isAvailableMethod(methodName) {
        const method = String(methodName || '');
        if (method === 'leaderboards.setScore') {
          return Promise.resolve(typeof bridge.leaderboards?.setScore === 'function');
        }
        if (method === 'leaderboards.getEntries') {
          return Promise.resolve(typeof bridge.leaderboards?.getEntries === 'function');
        }
        return Promise.resolve(new Set([
          'getPlayer',
          'adv.showFullscreenAdv',
          'features.LoadingAPI.ready',
          'features.GameplayAPI.start',
          'features.GameplayAPI.stop'
        ]).has(method));
      }
    };

    window.ysdk = pseudoSdk;
    window.playgamaYandexCompatSdk = pseudoSdk;
    window.yandexGameLanguage = pseudoSdk.environment.i18n.lang;
    return pseudoSdk;
  };

  window.yandexGamesSDKReady = window.playgamaBridgeReady.then((bridge) => {
    if (!bridge) return null;
    return createSdk(bridge);
  });

  window.YaGames = {
    init() {
      return window.yandexGamesSDKReady;
    }
  };

  document.addEventListener('visibilitychange', () => {
    setPauseReason('document-hidden', document.hidden);
  });
})();
