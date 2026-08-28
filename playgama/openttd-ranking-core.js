/* Platform-neutral ranking core shared by browser builds.
 * Local ranking uses OpenTTD's native company performance rating (0..1000).
 * Every previous experimental storage/snapshot format is deliberately discarded
 * instead of being clamped into plausible-looking scores.
 */
(() => {
  'use strict';
  if (window.OpenTTDRankingCore) return;

  const MAX_SCORE = 1000;
  const LOCAL_KEY = 'openttd.localRanking.v4';
  const LEGACY_LOCAL_KEYS = [
    'openttd.localRanking.v1',
    'openttd.localRanking.v2',
    'openttd.localRanking.v3',
  ];
  const SNAPSHOT_PATH = '/home/web_user/.openttd/local-ranking.tsv';
  const LIMIT = 10;
  let lastSnapshot = '';

  const cleanName = (value) => String(value || 'Company').replace(/[\t\r\n]+/g, ' ').trim().slice(0, 96) || 'Company';
  const normalizeScore = (value) => {
    const n = Number(String(value));
    if (!Number.isFinite(n)) return 0;
    const score = Math.trunc(n);
    if (score <= 0 || score > MAX_SCORE) return 0;
    return score;
  };

  /* v1-v3 belong to older score/snapshot contracts. Never reinterpret them. */
  try {
    if (typeof localStorage.removeItem === 'function') {
      LEGACY_LOCAL_KEYS.forEach((key) => localStorage.removeItem(key));
    }
  } catch (_) {}

  const load = () => {
    try {
      const parsed = JSON.parse(localStorage.getItem(LOCAL_KEY) || '[]');
      if (!Array.isArray(parsed)) return [];
      return parsed.map((row) => ({
        name: cleanName(row?.name),
        score: normalizeScore(row?.score),
        stamp: Number.isFinite(row?.stamp) ? row.stamp : 0,
      })).filter((row) => row.score > 0).sort((a, b) => b.score - a.score || b.stamp - a.stamp).slice(0, LIMIT);
    } catch (_) {
      return [];
    }
  };

  const save = (rows) => {
    try { localStorage.setItem(LOCAL_KEY, JSON.stringify(rows.slice(0, LIMIT))); } catch (_) {}
  };

  const writeSnapshot = () => {
    const rows = load();
    const lines = ['version\t3'];
    rows.forEach((row, index) => lines.push(`entry\t${index + 1}\t${row.score}\t${row.name}`));
    const text = lines.join('\n') + '\n';
    if (text === lastSnapshot) return true;
    try {
      if (typeof FS === 'undefined' || typeof FS.writeFile !== 'function') return false;
      try { FS.mkdirTree('/home/web_user/.openttd'); } catch (_) {}
      FS.writeFile(SNAPSHOT_PATH, text, { encoding: 'utf8' });
      lastSnapshot = text;
      return true;
    } catch (error) {
      console.warn('[OpenTTD ranking] Could not publish local ranking snapshot', error);
      return false;
    }
  };

  const publishSoon = () => {
    if (!writeSnapshot()) setTimeout(writeSnapshot, 100);
  };

  const submit = (scoreValue, companyName, eligible = true) => {
    const score = normalizeScore(scoreValue);
    if (!eligible || score <= 0) return false;
    const name = cleanName(companyName);
    const rows = load();

    const existing = rows.find((row) => row.name === name);
    if (existing) {
      if (score <= existing.score) {
        window.OpenTTDGlobalRanking?.submitScore?.(score);
        return false;
      }
      existing.score = score;
      existing.stamp = Date.now();
    } else {
      rows.push({ name, score, stamp: Date.now() });
    }
    rows.sort((a, b) => b.score - a.score || b.stamp - a.stamp);
    save(rows.slice(0, LIMIT));
    publishSoon();

    window.OpenTTDGlobalRanking?.submitScore?.(score);
    return true;
  };

  const requestLocalSnapshot = () => {
    publishSoon();
    return load();
  };

  window.OpenTTDRankingCore = {
    maxScore: MAX_SCORE,
    submit,
    requestLocalSnapshot,
    refreshLocal: publishSoon,
  };

  publishSoon();
})();
