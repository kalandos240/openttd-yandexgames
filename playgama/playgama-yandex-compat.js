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
      if (context?.state === 'suspended' && (navigator.userActivation?.hasBeenActive ?? true)) context.resume?.().catch?.(() => {});
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

    // Do not hard-code a major Bridge version here. The public JS Core uses the
    // stable v1 CDN and Playgama can update the stable implementation without a
    // game rebuild. A previous v2-only assertion caused startup failure.
    document.documentElement.dataset.playgamaBridge = 'ready';
    document.documentElement.dataset.playgamaBridgeVersion = String(bridge.version || 'stable');

    try { bridge.advertisement?.setMinimumDelayBetweenInterstitial?.(120); } catch (_) {}

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
      getMode() { return 'full'; },
      getUniqueID() { return ''; },
      getName() { return ''; }
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
        return Promise.resolve(new Set([
          'getPlayer',
          'adv.showFullscreenAdv',
          'features.LoadingAPI.ready',
          'features.GameplayAPI.start',
          'features.GameplayAPI.stop'
        ]).has(String(methodName || '')));
      }
    };

    window.ysdk = pseudoSdk;
    window.playgamaYandexCompatSdk = pseudoSdk;
    return pseudoSdk;
  };

  window.YaGames = {
    init() {
      return window.playgamaBridgeReady.then((bridge) => {
        if (!bridge) {
          console.warn('[Playgama] Bridge unavailable; starting OpenTTD with offline platform fallback.');
          return createSdk({});
        }
        return createSdk(bridge);
      });
    }
  };

  document.addEventListener('visibilitychange', () => {
    setPauseReason('document-hidden', document.hidden);
  });
})();
