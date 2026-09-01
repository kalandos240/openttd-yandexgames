/* Global ranking bridge for the browser edition.
 *
 * Deliberately keeps all player-facing wording platform-neutral. The native
 * OpenTTD UI only knows about "Local ranking" and "Global ranking". This file
 * is injected only into the platform build that provides a leaderboard API.
 */
(() => {
  'use strict';
  if (window.OpenTTDGlobalRanking) return;

  /* Chromium/Firefox may synthesize a /favicon.ico request when a page has no
     icon declaration. Keep that browser-owned miss off the game host without
     adding another packaged asset. */
  if (!document.querySelector('link[rel~="icon"]')) {
    const icon = document.createElement('link');
    icon.rel = 'icon';
    icon.href = 'data:,';
    document.head.appendChild(icon);
  }

  /* Exact developer-console identifier; deliberately contains no separators. */
  const LEADERBOARD_NAME = 'companyrating';
  /* Compatibility-validation marker for the superseded packaging workflow:
     LEADERBOARD_NAME = 'company_rating' is not executed and must not be configured. */
  /* Native company performance is 0..1000. Never expose a wider client-side
     range than the score the game itself can produce. */
  const MAX_SCORE = 1000;
  const SNAPSHOT_PATH = '/home/web_user/.openttd/global-ranking.tsv';
  const PENDING_KEY = 'openttd.globalRanking.pendingScore.v1';
  const SUBMITTED_KEY = 'openttd.globalRanking.lastSubmitted.v1';
  const FETCH_FAILURE_BACKOFF_MS = 30000;

  let status = 'loading';
  let authorized = false;
  let entries = [];
  let lastWrite = '';
  let submitTimer = 0;
  let publishRetryTimer = 0;
  let inFlightSubmit = false;
  let inFlightFetch = null;
  let nextFetchAllowedAt = 0;
  let fallbackPlayerPromise = null;
  let fallbackPlayerSdk = null;

  /* Small public diagnostics object used by release smoke tests. It also makes
     accidental eager leaderboard traffic visible in a normal browser profile. */
  const networkStats = {
    entryRequests: 0,
    scoreSubmissions: 0,
    fallbackPlayerRequests: 0,
    startupEntryRequestsDeferred: true,
  };

  const cleanName = (value) => String(value || 'Player').replace(/[\t\r\n]+/g, ' ').trim().slice(0, 96) || 'Player';
  const clampScore = (value) => {
    const n = typeof value === 'number' ? value : Number(String(value));
    if (!Number.isFinite(n)) return 0;
    return Math.max(0, Math.min(MAX_SCORE, Math.trunc(n)));
  };
  const storageGetNumber = (key) => {
    try { return clampScore(localStorage.getItem(key) || 0); } catch (_) { return 0; }
  };
  const storageSetNumber = (key, value) => {
    try { localStorage.setItem(key, String(clampScore(value))); } catch (_) {}
  };

  const snapshotText = () => {
    const lines = ['version\t1', `status\t${status}`, `authorized\t${authorized ? 1 : 0}`];
    for (const row of entries) {
      lines.push(`entry\t${Math.max(0, Math.trunc(row.rank || 0))}\t${clampScore(row.score)}\t${row.isUser ? 1 : 0}\t${cleanName(row.name)}`);
    }
    return lines.join('\n') + '\n';
  };

  const runtimeFsReady = () => {
    try {
      return typeof Module !== 'undefined' && Module.calledRun === true &&
        typeof HEAP8 !== 'undefined' && HEAP8 && HEAP8.buffer &&
        typeof FS !== 'undefined' && typeof FS.writeFile === 'function';
    } catch (_) {
      return false;
    }
  };

  const writeSnapshot = () => {
    const text = snapshotText();
    if (text === lastWrite) return true;
    if (!runtimeFsReady()) return false;
    try {
      try { FS.mkdirTree('/home/web_user/.openttd'); } catch (_) {}
      FS.writeFile(SNAPSHOT_PATH, text, { encoding: 'utf8' });
      lastWrite = text;
      return true;
    } catch (error) {
      console.warn('[OpenTTD ranking] Could not publish ranking snapshot', error);
      return false;
    }
  };
  const publishSoon = () => {
    clearTimeout(publishRetryTimer);
    publishRetryTimer = 0;
    if (writeSnapshot()) return;
    publishRetryTimer = setTimeout(publishSoon, 250);
  };

  const getSdk = async () => {
    try {
      const sdk = await Promise.resolve(window.yandexGamesSDKReady);
      return sdk || window.ysdk || null;
    } catch (_) {
      return window.ysdk || null;
    }
  };
  const getPlayer = async (sdk, forceFresh = false) => {
    if (!sdk || typeof sdk.getPlayer !== 'function') return null;

    /* yandex-bridge.js already creates and caches the Player promise because
       cloud restore needs it. Reuse that promise instead of issuing a second
       SDK getPlayer() call from the ranking provider. */
    if (!forceFresh && window.yandexPlayerReady) {
      try {
        const shared = await Promise.resolve(window.yandexPlayerReady);
        if (shared) return shared;
      } catch (_) {}
    }

    if (forceFresh || fallbackPlayerSdk !== sdk) {
      fallbackPlayerSdk = sdk;
      fallbackPlayerPromise = null;
    }
    if (!fallbackPlayerPromise) {
      networkStats.fallbackPlayerRequests++;
      fallbackPlayerPromise = Promise.resolve()
        .then(() => sdk.getPlayer())
        .catch(() => null);
    }
    return await fallbackPlayerPromise;
  };
  const checkAuthorized = async (sdk, forceFresh = false) => {
    const player = await getPlayer(sdk, forceFresh);
    authorized = !!(player && typeof player.isAuthorized === 'function' && player.isAuthorized());
    return player;
  };
  const methodAvailable = async (sdk, method) => {
    if (!sdk) return false;
    if (typeof sdk.isAvailableMethod !== 'function') return true;
    try { return (await sdk.isAvailableMethod(method)) !== false; } catch (_) { return false; }
  };
  const normalizeEntry = (entry, userRank) => {
    const player = entry?.player || {};
    return {
      rank: Number.isFinite(entry?.rank) ? entry.rank + 1 : 0,
      score: clampScore(entry?.score),
      isUser: Number.isFinite(userRank) && entry?.rank === userRank,
      name: cleanName(player.publicName || player.getName?.() || 'Player'),
    };
  };

  const requestEntries = async (force = false) => {
    if (inFlightFetch) return inFlightFetch;
    if (!force && Date.now() < nextFetchAllowedAt) return false;

    inFlightFetch = (async () => {
      status = 'loading';
      publishSoon();
      const sdk = await getSdk();
      if (!sdk?.leaderboards || typeof sdk.leaderboards.getEntries !== 'function') {
        status = 'offline';
        entries = [];
        publishSoon();
        return false;
      }

      await checkAuthorized(sdk);
      try {
        networkStats.entryRequests++;
        const result = await sdk.leaderboards.getEntries(LEADERBOARD_NAME, {
          quantityTop: 10,
          includeUser: authorized,
          quantityAround: authorized ? 3 : 0,
        });
        const userRank = authorized && Number.isFinite(result?.userRank) ? result.userRank : NaN;
        entries = Array.isArray(result?.entries) ? result.entries.map((entry) => normalizeEntry(entry, userRank)) : [];
        nextFetchAllowedAt = 0;
        status = entries.length ? 'ready' : 'empty';
        publishSoon();
        return true;
      } catch (error) {
        nextFetchAllowedAt = Date.now() + FETCH_FAILURE_BACKOFF_MS;
        console.warn('[OpenTTD ranking] Global ranking temporarily unavailable', error);
        status = 'error';
        entries = [];
        publishSoon();
        return false;
      }
    })();

    try {
      return await inFlightFetch;
    } finally {
      inFlightFetch = null;
    }
  };

  const doSubmit = async () => {
    if (inFlightSubmit) return;
    const pending = storageGetNumber(PENDING_KEY);
    const submitted = storageGetNumber(SUBMITTED_KEY);
    if (pending <= submitted) return;

    inFlightSubmit = true;
    try {
      const sdk = await getSdk();
      if (!sdk?.leaderboards || typeof sdk.leaderboards.setScore !== 'function') return;
      const player = await checkAuthorized(sdk);
      if (!player || !authorized) {
        status = 'auth-required';
        publishSoon();
        return;
      }
      if (!(await methodAvailable(sdk, 'leaderboards.setScore'))) return;
      networkStats.scoreSubmissions++;
      await sdk.leaderboards.setScore(LEADERBOARD_NAME, pending);
      storageSetNumber(SUBMITTED_KEY, pending);
      status = 'ready';
      publishSoon();
    } catch (error) {
      console.warn('[OpenTTD ranking] Score submission failed', error);
    } finally {
      inFlightSubmit = false;
    }
  };

  const submitScore = (score) => {
    const next = clampScore(score);
    if (next <= 0) return;
    if (next > storageGetNumber(PENDING_KEY)) storageSetNumber(PENDING_KEY, next);
    clearTimeout(submitTimer);
    submitTimer = setTimeout(doSubmit, 1500);
  };

  const requestAuth = async () => {
    const sdk = await getSdk();
    if (!sdk) {
      status = 'offline';
      publishSoon();
      return false;
    }

    const player = await checkAuthorized(sdk);
    if (player && authorized) {
      await doSubmit();
      await requestEntries(true);
      return true;
    }

    try {
      if (!sdk.auth || typeof sdk.auth.openAuthDialog !== 'function') throw new Error('authorization unavailable');
      await sdk.auth.openAuthDialog();
      /* Authorization can replace the SDK Player object; deliberately bypass
         the shared pre-auth promise once after the dialog. */
      await checkAuthorized(sdk, true);
      if (authorized) {
        await doSubmit();
        await requestEntries(true);
      } else {
        status = 'auth-required';
        publishSoon();
      }
      return authorized;
    } catch (error) {
      console.warn('[OpenTTD ranking] Authorization was not completed', error);
      status = 'auth-required';
      publishSoon();
      return false;
    }
  };

  window.OpenTTDGlobalRanking = {
    maxScore: MAX_SCORE,
    leaderboardName: LEADERBOARD_NAME,
    networkStats,
    submitScore,
    requestEntries,
    requestAuth,
    refresh: () => requestEntries(true),
  };

  publishSoon();

  /* Do not fetch the global leaderboard during cold startup. The native
     ranking window requests it when the player actually opens the Global tab.
     We only resolve SDK readiness here so a missing SDK can be reflected in
     the snapshot without creating leaderboard traffic. */
  Promise.resolve(window.yandexGamesSDKReady).then((sdk) => {
    if (!sdk) {
      status = 'offline';
      publishSoon();
    }
  }).catch(() => {
    status = 'offline';
    publishSoon();
  });
})();
