/* Global ranking bridge for the browser edition.
 *
 * Deliberately keeps all player-facing wording platform-neutral. The native
 * OpenTTD UI only knows about "Local ranking" and "Global ranking". This file
 * is injected only into the platform build that provides a leaderboard API.
 */
(() => {
  'use strict';
  if (window.OpenTTDGlobalRanking) return;

  const LEADERBOARD_NAME = 'company_rating';
  const MAX_SCORE = Number.MAX_SAFE_INTEGER; // 2^53 - 1; exact JS integer range.
  const SNAPSHOT_PATH = '/home/web_user/.openttd/global-ranking.tsv';
  const PENDING_KEY = 'openttd.globalRanking.pendingScore.v1';
  const SUBMITTED_KEY = 'openttd.globalRanking.lastSubmitted.v1';

  let status = 'loading';
  let authorized = false;
  let entries = [];
  let lastWrite = '';
  let submitTimer = 0;
  let inFlightSubmit = false;

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
    const lines = [
      'version\t1',
      `status\t${status}`,
      `authorized\t${authorized ? 1 : 0}`,
    ];
    for (const row of entries) {
      lines.push(`entry\t${Math.max(0, Math.trunc(row.rank || 0))}\t${clampScore(row.score)}\t${row.isUser ? 1 : 0}\t${cleanName(row.name)}`);
    }
    return lines.join('\n') + '\n';
  };

  const writeSnapshot = () => {
    const text = snapshotText();
    if (text === lastWrite) return true;
    try {
      if (typeof FS === 'undefined' || typeof FS.writeFile !== 'function') return false;
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
    if (writeSnapshot()) return;
    setTimeout(writeSnapshot, 100);
  };

  const getSdk = async () => {
    try {
      const sdk = await Promise.resolve(window.yandexGamesSDKReady);
      return sdk || window.ysdk || null;
    } catch (_) {
      return window.ysdk || null;
    }
  };

  const getPlayer = async (sdk) => {
    if (!sdk || typeof sdk.getPlayer !== 'function') return null;
    try { return await sdk.getPlayer(); } catch (_) { return null; }
  };

  const checkAuthorized = async (sdk) => {
    const player = await getPlayer(sdk);
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

  const requestEntries = async () => {
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
      const result = await sdk.leaderboards.getEntries(LEADERBOARD_NAME, {
        quantityTop: 10,
        includeUser: authorized,
        quantityAround: authorized ? 3 : 0,
      });
      const userRank = Number.isFinite(result?.userRank) ? result.userRank : NaN;
      entries = Array.isArray(result?.entries) ? result.entries.map((entry) => normalizeEntry(entry, userRank)) : [];
      status = entries.length ? 'ready' : 'empty';
      publishSoon();
      return true;
    } catch (error) {
      console.warn('[OpenTTD ranking] Global ranking request failed', error);
      status = 'error';
      entries = [];
      publishSoon();
      return false;
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
    const pending = storageGetNumber(PENDING_KEY);
    if (next > pending) storageSetNumber(PENDING_KEY, next);

    /* The SDK permits at most one setScore request per second. Coalesce native
       score updates and leave extra margin for retries/focus transitions. */
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
      await requestEntries();
      return true;
    }

    try {
      if (!sdk.auth || typeof sdk.auth.openAuthDialog !== 'function') throw new Error('authorization unavailable');
      await sdk.auth.openAuthDialog();
      await checkAuthorized(sdk);
      if (authorized) {
        await doSubmit();
        await requestEntries();
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
    submitScore,
    requestEntries,
    requestAuth,
    refresh: requestEntries,
  };

  /* Publish a neutral initial state once the virtual filesystem exists, then
     warm the public top list without opening any authorization dialog. */
  publishSoon();
  Promise.resolve(window.yandexGamesSDKReady).then(() => requestEntries()).catch(() => {
    status = 'offline';
    publishSoon();
  });
})();
