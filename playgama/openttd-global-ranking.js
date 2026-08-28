/* Global ranking bridge for Playgama browser builds.
 *
 * Player-facing text stays completely platform-neutral. Native OpenTTD only
 * renders "Local ranking" / "Global ranking" and a generic sign-in action.
 */
(() => {
  'use strict';
  if (window.OpenTTDGlobalRanking) return;

  const LEADERBOARD_NAME = 'companyrating';
  const MAX_SCORE = 1000;
  const SNAPSHOT_PATH = '/home/web_user/.openttd/global-ranking.tsv';
  /* v2 intentionally discards pending/submitted values from the obsolete
     53-bit scoring scheme. */
  const PENDING_KEY = 'openttd.globalRanking.pendingScore.v2';
  const SUBMITTED_KEY = 'openttd.globalRanking.lastSubmitted.v2';
  const FETCH_FAILURE_BACKOFF_MS = 30000;

  let status = 'loading';
  let authorized = false;
  let entries = [];
  let lastWrite = '';
  let submitTimer = 0;
  let inFlightSubmit = false;
  let inFlightFetch = null;
  let nextFetchAllowedAt = 0;

  const cleanName = (value) => String(value || 'Player').replace(/[\t\r\n]+/g, ' ').trim().slice(0, 96) || 'Player';
  const clampScore = (value) => {
    const n = typeof value === 'number' ? value : Number(String(value));
    if (!Number.isFinite(n)) return 0;
    return Math.max(0, Math.min(MAX_SCORE, Math.trunc(n)));
  };
  const readLeaderboardScore = (value) => {
    const n = typeof value === 'number' ? value : Number(String(value));
    if (!Number.isFinite(n)) return null;
    const score = Math.trunc(n);
    /* Do not clamp old trillion-point entries to 1000. They belong to the
       retired v1 formula and must disappear from the new readable table. */
    return score >= 0 && score <= MAX_SCORE ? score : null;
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
    const player = bridge?.player;
    if (!player) {
      authorized = false;
      return false;
    }
    /* Platforms without an authorization flow may still provide a usable
       leaderboard identity, so do not force an impossible sign-in step. */
    authorized = player.isAuthorizationSupported === false || player.isAuthorized === true;
    return authorized;
  };

  const snapshotText = () => {
    const lines = ['version\t2', 'scale\t0-1000', `status\t${status}`, `authorized\t${authorized ? 1 : 0}`];
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

  const requestEntries = async (force = false) => {
    if (inFlightFetch) return inFlightFetch;
    if (!force && Date.now() < nextFetchAllowedAt) return false;

    inFlightFetch = (async () => {
      status = 'loading';
      publishSoon();

      const bridge = await getBridge();
      refreshAuthorized(bridge);
      const leaderboards = bridge?.leaderboards;
      const type = leaderboards?.type || 'not_available';

      /* Playgama only exposes entry data for in-game leaderboards. Native and
         native-popup leaderboards cannot be rendered inside the OpenTTD window,
         and we must never auto-open a platform popup during startup polling. */
      if (type !== 'in_game' || typeof leaderboards?.getEntries !== 'function') {
        status = 'offline';
        entries = [];
        publishSoon();
        return false;
      }

      try {
        const result = await leaderboards.getEntries(LEADERBOARD_NAME);
        const rows = Array.isArray(result) ? result : [];
        const ownId = bridge?.player?.id == null ? null : String(bridge.player.id);
        entries = rows.map((entry) => {
          const score = readLeaderboardScore(entry?.score);
          if (score === null) return null;
          return {
            score,
            isUser: ownId !== null && entry?.id != null && String(entry.id) === ownId,
            name: cleanName(entry?.name),
          };
        }).filter(Boolean).slice(0, 10).map((row, index) => ({ ...row, rank: index + 1 }));
        nextFetchAllowedAt = 0;
        status = entries.length ? 'ready' : 'empty';
        publishSoon();
        return true;
      } catch (error) {
        nextFetchAllowedAt = Date.now() + FETCH_FAILURE_BACKOFF_MS;
        console.warn('[OpenTTD ranking] Global ranking request failed', error);
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
    if (inFlightSubmit) return false;
    const pending = storageGetNumber(PENDING_KEY);
    const submitted = storageGetNumber(SUBMITTED_KEY);
    if (pending <= submitted) return true;

    const bridge = await getBridge();
    const leaderboards = bridge?.leaderboards;
    refreshAuthorized(bridge);
    if (!leaderboards || typeof leaderboards.setScore !== 'function' || leaderboards.type === 'not_available') {
      status = 'offline';
      publishSoon();
      return false;
    }
    if (bridge?.player?.isAuthorizationSupported === true && !authorized) {
      status = 'auth-required';
      publishSoon();
      return false;
    }

    inFlightSubmit = true;
    try {
      await leaderboards.setScore(LEADERBOARD_NAME, pending);
      storageSetNumber(SUBMITTED_KEY, pending);
      status = 'ready';
      publishSoon();
      return true;
    } catch (error) {
      console.warn('[OpenTTD ranking] Score submission failed', error);
      status = bridge?.player?.isAuthorizationSupported === true && !authorized ? 'auth-required' : 'error';
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
    if (!authorized && bridge?.player?.isAuthorizationSupported === true && typeof bridge?.player?.authorize === 'function') {
      try {
        await bridge.player.authorize({});
      } catch (error) {
        console.warn('[OpenTTD ranking] Authorization was not completed', error);
      }
      refreshAuthorized(bridge);
    }

    if (authorized) {
      await doSubmit();
      await requestEntries(true);
    } else if (bridge?.player?.isAuthorizationSupported === true) {
      status = 'auth-required';
      publishSoon();
    } else {
      /* No supported authorization flow: retry the leaderboard directly rather
         than showing a sign-in action the player cannot complete. */
      await requestEntries(true);
    }
    return authorized;
  };

  window.OpenTTDGlobalRanking = {
    maxScore: MAX_SCORE,
    leaderboardName: LEADERBOARD_NAME,
    submitScore,
    requestEntries,
    requestAuth,
    refresh: () => requestEntries(true),
  };

  publishSoon();
  Promise.resolve(window.playgamaBridgeReady).then(() => requestEntries()).catch(() => {
    status = 'offline';
    publishSoon();
  });
})();
