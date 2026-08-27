/* Global ranking bridge for Playgama browser builds.
 *
 * Player-facing text stays completely platform-neutral. Native OpenTTD only
 * renders "Local ranking" / "Global ranking" and a generic sign-in action.
 */
(() => {
  'use strict';
  if (window.OpenTTDGlobalRanking) return;

  const LEADERBOARD_NAME = 'companyrating';
  const MAX_SCORE = Number.MAX_SAFE_INTEGER;
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

  const getBridge = async () => {
    try {
      const ready = await Promise.resolve(window.playgamaBridgeReady);
      return ready || window.bridge || null;
    } catch (_) {
      return window.bridge || null;
    }
  };

  const refreshAuthorized = (bridge) => {
    authorized = bridge?.player?.isAuthorizationSupported === false || !!bridge?.player?.isAuthorized;
    return authorized;
  };

  const snapshotText = () => {
    const lines = ['version\t1', `status\t${status}`, `authorized\t${authorized ? 1 : 0}`];
    for (const row of entries) {
      lines.push(`entry\t${Math.max(1, Math.trunc(row.rank || 1))}\t${clampScore(row.score)}\t${row.isUser ? 1 : 0}\t${cleanName(row.name)}`);
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
      console.warn('[OpenTTD ranking] Could not publish global ranking snapshot', error);
      return false;
    }
  };
  const publishSoon = () => {
    if (!writeSnapshot()) setTimeout(writeSnapshot, 100);
  };

  const requestEntries = async () => {
    status = 'loading';
    publishSoon();
    const bridge = await getBridge();
    refreshAuthorized(bridge);
    const type = bridge?.leaderboards?.type || 'not_available';
    if (type !== 'in_game' || typeof bridge?.leaderboards?.getEntries !== 'function') {
      status = type === 'not_available' ? 'offline' : 'error';
      entries = [];
      publishSoon();
      return false;
    }

    try {
      const result = await bridge.leaderboards.getEntries(LEADERBOARD_NAME);
      const rows = Array.isArray(result) ? result : [];
      const ownId = bridge?.player?.id == null ? null : String(bridge.player.id);
      const zeroBasedRanks = rows.some((entry) => Number(entry?.rank) === 0);
      entries = rows.slice(0, 10).map((entry, index) => {
        const rawRank = Number(entry?.rank);
        const rank = Number.isFinite(rawRank)
          ? Math.max(1, Math.trunc(rawRank) + (zeroBasedRanks ? 1 : 0))
          : index + 1;
        return {
          rank,
          score: clampScore(entry?.score),
          isUser: ownId !== null && entry?.id != null && String(entry.id) === ownId,
          name: cleanName(entry?.name),
        };
      });
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
    if (inFlightSubmit) return false;
    const pending = storageGetNumber(PENDING_KEY);
    const submitted = storageGetNumber(SUBMITTED_KEY);
    if (pending <= submitted) return true;

    const bridge = await getBridge();
    refreshAuthorized(bridge);
    if (!bridge?.leaderboards || typeof bridge.leaderboards.setScore !== 'function' || bridge.leaderboards.type === 'not_available') {
      status = 'offline';
      publishSoon();
      return false;
    }
    if (bridge?.player?.isAuthorizationSupported && !authorized) {
      status = 'auth-required';
      publishSoon();
      return false;
    }

    inFlightSubmit = true;
    try {
      await bridge.leaderboards.setScore(LEADERBOARD_NAME, pending);
      storageSetNumber(SUBMITTED_KEY, pending);
      status = 'ready';
      publishSoon();
      return true;
    } catch (error) {
      console.warn('[OpenTTD ranking] Score submission failed', error);
      status = authorized ? 'error' : 'auth-required';
      publishSoon();
      return false;
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
    const bridge = await getBridge();
    if (!bridge) {
      status = 'offline';
      publishSoon();
      return false;
    }
    refreshAuthorized(bridge);
    if (!authorized && bridge?.player?.isAuthorizationSupported && typeof bridge?.player?.authorize === 'function') {
      try {
        await bridge.player.authorize({});
      } catch (error) {
        console.warn('[OpenTTD ranking] Authorization was not completed', error);
      }
      refreshAuthorized(bridge);
    }
    if (authorized) {
      await doSubmit();
      await requestEntries();
    } else {
      status = 'auth-required';
      publishSoon();
    }
    return authorized;
  };

  window.OpenTTDGlobalRanking = {
    maxScore: MAX_SCORE,
    leaderboardName: LEADERBOARD_NAME,
    submitScore,
    requestEntries,
    requestAuth,
    refresh: requestEntries,
  };

  publishSoon();
  Promise.resolve(window.playgamaBridgeReady).then(() => requestEntries()).catch(() => {
    status = 'offline';
    publishSoon();
  });
})();
