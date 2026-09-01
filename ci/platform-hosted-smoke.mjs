import puppeteer from 'puppeteer-core';
import fs from 'node:fs';

const [platform, url, output] = process.argv.slice(2);
if (!platform || !url || !output) throw new Error('usage: platform-hosted-smoke.mjs <yandex|playgama> <url> <output.json>');
const executablePath = process.env.CHROME_BIN;
if (!executablePath) throw new Error('CHROME_BIN is not set');

const browser = await puppeteer.launch({
  executablePath,
  headless: true,
  args: [
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--autoplay-policy=no-user-gesture-required',
    '--disable-background-networking',
  ],
});

const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 720, deviceScaleFactor: 1 });
const responses = new Map();
const pageErrors = [];
const failedRequests = [];
const blockedExternal = [];
const externalWebSockets = [];
const consoleLines = [];

const isExternalNetworkUrl = raw => {
  try {
    const u = new URL(raw);
    if (!['http:', 'https:', 'ws:', 'wss:'].includes(u.protocol)) return false;
    return u.hostname !== '127.0.0.1' && u.hostname !== 'localhost';
  } catch (_) {
    return false;
  }
};

page.on('response', response => {
  try {
    const u = new URL(response.url());
    responses.set(u.pathname, response.status());
  } catch (_) {}
});
page.on('pageerror', error => pageErrors.push(String(error?.stack || error)));
page.on('requestfailed', request => failedRequests.push(`${request.url()} :: ${request.failure()?.errorText || 'failed'}`));
page.on('console', message => consoleLines.push(`[${message.type()}] ${message.text()}`));

/* Request interception catches HTTP(S) dependencies. CDP is also enabled so a
   WebSocket attempt cannot bypass the autonomy gate. */
const cdp = await page.createCDPSession();
await cdp.send('Network.enable');
cdp.on('Network.webSocketCreated', event => {
  if (isExternalNetworkUrl(event.url) && !externalWebSockets.includes(event.url)) externalWebSockets.push(event.url);
});

await page.setRequestInterception(true);
page.on('request', request => {
  const requestUrl = request.url();
  try {
    const u = new URL(requestUrl);
    if ((u.protocol === 'http:' || u.protocol === 'https:') && isExternalNetworkUrl(requestUrl)) {
      if (!blockedExternal.includes(requestUrl)) blockedExternal.push(requestUrl);
      request.abort('blockedbyclient');
      return;
    }
  } catch (_) {}
  request.continue();
});

let result = {};
let failure = null;
try {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForFunction(() => window.Module?.calledRun === true, { timeout: 60000, polling: 100 });
  await new Promise(resolve => setTimeout(resolve, 5000));

  result = await page.evaluate((platformName) => {
    const canvas = document.getElementById('canvas');
    const box = document.getElementById('box');
    const sdl = window.Module?.SDL2 || null;
    return {
      calledRun: Boolean(window.Module?.calledRun),
      canvasWidth: canvas?.width || 0,
      canvasHeight: canvas?.height || 0,
      canvasDisplay: canvas ? getComputedStyle(canvas).display : 'missing',
      boxError: Boolean(box?.classList.contains('error')),
      title: document.getElementById('title')?.textContent || '',
      message: document.getElementById('message')?.textContent || '',
      yandexSdk: document.documentElement.dataset.yandexSdk || '',
      yandexLoadingReady: document.documentElement.dataset.yandexLoadingReady || '',
      yandexGameplay: document.documentElement.dataset.yandexGameplay || '',
      playgamaSdk: document.documentElement.dataset.playgamaSdk || '',
      playgamaBridge: document.documentElement.dataset.playgamaBridge || '',
      playgamaMessage: document.documentElement.dataset.playgamaMessage || '',
      yandexRankingNetworkStats: window.OpenTTDGlobalRanking?.networkStats ? { ...window.OpenTTDGlobalRanking.networkStats } : null,
      yandexCloudNetworkStats: window.__openttdYandexCloudNetworkStats ? { ...window.__openttdYandexCloudNetworkStats } : null,
      webglPresenter: Boolean(sdl?.__openttdWebGLPresenter),
      webgl2ZeroCopy: Boolean(sdl?.__openttdWebGL2ZeroCopy),
      framebufferFullUploads: Number(sdl?.__openttdFramebufferFullUploads || 0),
      framebufferPartialUploads: Number(sdl?.__openttdFramebufferPartialUploads || 0),
      framebufferUploadedPixels: Number(sdl?.__openttdFramebufferUploadedPixels || 0),
      framebufferLastDirtyArea: Number(sdl?.__openttdFramebufferLastDirtyArea || 0),
      platformName,
    };
  }, platform);

  if (responses.get('/openttd-runtime.js') !== 200) {
    throw new Error(`required resource /openttd-runtime.js did not return HTTP 200; got ${responses.get('/openttd-runtime.js')}`);
  }

  // OpenTTD Web supports both split Emscripten packages and SINGLE_FILE builds.
  // If either external binary is requested, require both to load successfully.
  // If neither is requested, wasm/data are embedded in openttd-runtime.js.
  const splitBinaryObserved = responses.has('/openttd.wasm') || responses.has('/openttd.data');
  if (splitBinaryObserved) {
    for (const path of ['/openttd.wasm', '/openttd.data']) {
      if (responses.get(path) !== 200) throw new Error(`required split resource ${path} did not return HTTP 200; got ${responses.get(path)}`);
    }
  }

  if (!result.calledRun) throw new Error('Emscripten Module.calledRun is false');
  if (result.canvasWidth <= 0 || result.canvasHeight <= 0 || result.canvasDisplay === 'none') throw new Error(`canvas is not running: ${JSON.stringify(result)}`);
  if (result.boxError) throw new Error(`OpenTTD crash box is visible: ${JSON.stringify(result)}`);
  if (platform === 'yandex' && result.yandexSdk !== 'ready') throw new Error(`Yandex SDK path did not initialize: ${JSON.stringify(result)}`);
  if (platform === 'playgama' && result.playgamaBridge !== 'ready') throw new Error(`Playgama Bridge path did not initialize: ${JSON.stringify(result)}`);
  if (pageErrors.length) throw new Error(`page errors: ${pageErrors.join('\n')}`);

  /* Network efficiency gates for the Yandex build. Global leaderboard traffic
     must be zero during cold startup; it is allowed only after the player asks
     for the Global tab. Cloud writes must carry the unchanged-payload deduper. */
  if (platform === 'yandex') {
    const rankingStats = result.yandexRankingNetworkStats;
    if (!rankingStats || rankingStats.startupEntryRequestsDeferred !== true || Number(rankingStats.entryRequests || 0) !== 0) {
      throw new Error(`Yandex leaderboard made eager startup traffic: ${JSON.stringify(rankingStats)}`);
    }
    if (!result.yandexCloudNetworkStats?.dedupEnabled) {
      throw new Error(`Yandex cloud unchanged-payload dedup is not enabled: ${JSON.stringify(result.yandexCloudNetworkStats)}`);
    }

    /* Exercise the on-demand path once. This proves the optimization did not
       disable rankings; it only moves the request behind explicit use. */
    const rankingProbe = await page.evaluate(async () => {
      const ranking = window.OpenTTDGlobalRanking;
      if (!ranking || typeof ranking.requestEntries !== 'function') return null;
      const before = { ...ranking.networkStats };
      await ranking.requestEntries();
      const after = { ...ranking.networkStats };
      return { before, after };
    });
    result.yandexRankingOnDemandProbe = rankingProbe;
    if (!rankingProbe || Number(rankingProbe.before.entryRequests || 0) !== 0 || Number(rankingProbe.after.entryRequests || 0) !== 1) {
      throw new Error(`Yandex on-demand leaderboard probe failed: ${JSON.stringify(rankingProbe)}`);
    }
  }

  /* For the Yandex build, merely aborting an external request is not enough:
     attempting one is a release failure. The package must be autonomous apart
     from the same-origin /sdk.js supplied by Yandex Games. */
  if (platform === 'yandex' && blockedExternal.length) {
    throw new Error(`Yandex package attempted external HTTP(S) requests:\n${blockedExternal.join('\n')}`);
  }
  if (platform === 'yandex' && externalWebSockets.length) {
    throw new Error(`Yandex package attempted external WebSocket connections:\n${externalWebSockets.join('\n')}`);
  }
} catch (error) {
  failure = String(error?.stack || error);
  try { await page.screenshot({ path: output.replace(/\.json$/i, '.png'), fullPage: true }); } catch (_) {}
}

const report = {
  platform,
  url,
  passed: !failure,
  failure,
  result,
  responses: Object.fromEntries(responses),
  pageErrors,
  failedRequests,
  blockedExternal,
  externalWebSockets,
  consoleTail: consoleLines.slice(-160),
};
fs.writeFileSync(output, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
await browser.close();
if (failure) process.exit(1);

// v14 platform-verified release trigger: 2026-08-30
// Yandex autonomy gate hardened: HTTP(S) attempts and WebSockets are fatal.
// Renderer telemetry reports full/partial WebGL2 framebuffer upload counts.
// Yandex network gate: no eager leaderboard fetch; unchanged cloud payloads are deduplicated.
