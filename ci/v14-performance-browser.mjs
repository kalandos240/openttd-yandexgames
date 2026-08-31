import puppeteer from 'puppeteer-core';
import fs from 'node:fs';

const [platform, url, output, profile = 'optimized'] = process.argv.slice(2);
if (!platform || !url || !output || !['baseline', 'optimized'].includes(profile)) {
  throw new Error('usage: v14-performance-browser.mjs <yandex|playgama> <url> <output.json> [baseline|optimized]');
}
const executablePath = process.env.CHROME_BIN;
if (!executablePath) throw new Error('CHROME_BIN is not set');

const browser = await puppeteer.launch({
  executablePath,
  headless: true,
  args: [
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--autoplay-policy=no-user-gesture-required',
    '--disable-background-networking',
    '--enable-unsafe-swiftshader',
    '--use-angle=swiftshader-webgl',
    '--js-flags=--expose-gc',
  ],
});

const page = await browser.newPage();
await page.setViewport({ width: 1600, height: 900, deviceScaleFactor: 1 });
page.setDefaultTimeout(120000);

const responses = new Map();
const pageErrors = [];
const requestFailures = [];
const blockedExternal = [];
const consoleLines = [];

page.on('response', response => {
  try {
    const u = new URL(response.url());
    responses.set(u.pathname, response.status());
  } catch (_) {}
});
page.on('pageerror', error => pageErrors.push(String(error?.stack || error)));
page.on('requestfailed', request => requestFailures.push(`${request.url()} :: ${request.failure()?.errorText || 'failed'}`));
page.on('console', message => consoleLines.push(`[${message.type()}] ${message.text()}`));

await page.setRequestInterception(true);
page.on('request', request => {
  const requestUrl = request.url();
  try {
    const u = new URL(requestUrl);
    if ((u.protocol === 'http:' || u.protocol === 'https:') && u.hostname !== '127.0.0.1' && u.hostname !== 'localhost') {
      blockedExternal.push(requestUrl);
      request.abort('blockedbyclient');
      return;
    }
  } catch (_) {}
  request.continue();
});

await page.evaluateOnNewDocument(() => {
  window.__otPerfProbe = {
    longTasks: [],
    frames: 0,
    frameGaps: [],
    maxFrameGap: 0,
    lastFrame: 0,
    startedAt: 0,
  };

  try {
    new PerformanceObserver(list => {
      for (const e of list.getEntries()) {
        window.__otPerfProbe.longTasks.push({ startTime: e.startTime, duration: e.duration, name: e.name });
      }
    }).observe({ entryTypes: ['longtask'] });
  } catch (_) {}

  const frame = ts => {
    const p = window.__otPerfProbe;
    if (!p.startedAt) p.startedAt = ts;
    if (p.lastFrame) {
      const gap = ts - p.lastFrame;
      p.frameGaps.push(gap);
      if (p.frameGaps.length > 20000) p.frameGaps.shift();
      if (gap > p.maxFrameGap) p.maxFrameGap = gap;
    }
    p.lastFrame = ts;
    p.frames++;
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
});

const result = {
  platform,
  profile,
  url,
  startedAt: new Date().toISOString(),
  startup: {},
  generation4096: {},
  ai14: {},
  renderer: {},
  memory: {},
  network: {},
  console: {},
};
let failure = null;

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

async function resetFrameProbe() {
  await page.evaluate(() => {
    const p = window.__otPerfProbe;
    p.longTasks.length = 0;
    p.frames = 0;
    p.frameGaps.length = 0;
    p.maxFrameGap = 0;
    p.lastFrame = 0;
    p.startedAt = 0;
    if (window.Module?.__openttdUploadStats) {
      const s = window.Module.__openttdUploadStats;
      s.fullUploads = 0;
      s.partialUploads = 0;
      s.bytesUploaded = 0;
      s.lastRect = null;
    }
  });
}

async function snapshot(label) {
  const metrics = await page.metrics();
  return await page.evaluate((labelArg, metricsArg) => {
    const p = window.__otPerfProbe || {};
    const gaps = Array.isArray(p.frameGaps) ? [...p.frameGaps].sort((a, b) => a - b) : [];
    const pct = q => gaps.length ? gaps[Math.min(gaps.length - 1, Math.floor((gaps.length - 1) * q))] : 0;
    const elapsed = p.startedAt && p.lastFrame ? Math.max(0, p.lastFrame - p.startedAt) : 0;
    const upload = window.Module?.__openttdUploadStats ? { ...window.Module.__openttdUploadStats } : null;
    const aiStats = window.Module?.__openttdAIStats ? { ...window.Module.__openttdAIStats } : null;
    let wasmHeapBytes = 0;
    try {
      if (typeof HEAPU8 !== 'undefined') wasmHeapBytes = HEAPU8.byteLength;
      else if (window.Module?.HEAPU8) wasmHeapBytes = window.Module.HEAPU8.byteLength;
    } catch (_) {}
    const memory = performance.memory ? {
      jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
      totalJSHeapSize: performance.memory.totalJSHeapSize,
      usedJSHeapSize: performance.memory.usedJSHeapSize,
    } : null;
    return {
      label: labelArg,
      frames: p.frames || 0,
      elapsedMs: elapsed,
      estimatedFps: elapsed > 0 ? (p.frames * 1000 / elapsed) : 0,
      maxFrameGapMs: p.maxFrameGap || 0,
      p50FrameGapMs: pct(0.50),
      p95FrameGapMs: pct(0.95),
      p99FrameGapMs: pct(0.99),
      longTaskCount: Array.isArray(p.longTasks) ? p.longTasks.length : 0,
      longTaskTotalMs: Array.isArray(p.longTasks) ? p.longTasks.reduce((a, e) => a + e.duration, 0) : 0,
      longestLongTaskMs: Array.isArray(p.longTasks) ? p.longTasks.reduce((a, e) => Math.max(a, e.duration), 0) : 0,
      longTasksTop10: Array.isArray(p.longTasks) ? [...p.longTasks].sort((a, b) => b.duration - a.duration).slice(0, 10) : [],
      upload,
      aiStats,
      rendererActive: Boolean(window.Module?.SDL2?.__openttdWebGLPresenter),
      dirtyRect: window.Module?.__openttdDirtyRect || null,
      wasmHeapBytes,
      browserMemory: memory,
      puppeteerMetrics: metricsArg,
      canvas: (() => {
        const c = document.getElementById('canvas');
        return c ? { width: c.width, height: c.height, clientWidth: c.clientWidth, clientHeight: c.clientHeight } : null;
      })(),
    };
  }, label, metrics);
}

async function openConsole() {
  await page.click('#canvas');
  await page.keyboard.press('Backquote');
  await sleep(150);
}

async function consoleCommand(command, postDelay = 150) {
  await page.keyboard.type(command, { delay: 1 });
  await page.keyboard.press('Enter');
  if (postDelay) await sleep(postDelay);
}

try {
  const navigationStart = Date.now();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });
  const domContentLoadedMs = Date.now() - navigationStart;
  await page.waitForFunction(() => window.Module?.calledRun === true, { timeout: 120000, polling: 100 });
  const calledRunMs = Date.now() - navigationStart;
  await sleep(3000);

  result.startup = {
    domContentLoadedMs,
    calledRunMs,
    snapshot: await snapshot('startup-settled'),
  };

  if (!result.startup.snapshot.canvas?.width || !result.startup.snapshot.canvas?.height) {
    throw new Error('OpenTTD canvas is not active after calledRun');
  }
  if (pageErrors.length) throw new Error(`page errors before benchmark: ${pageErrors.join('\n')}`);

  // Use OpenTTD's own console and setting system. 4096 == 2^12.
  await openConsole();
  await consoleCommand('setting_newgame game_creation.map_x 12');
  await consoleCommand('setting_newgame game_creation.map_y 12');
  await consoleCommand('setting_newgame difficulty.max_no_competitors 14');
  await consoleCommand('setting_newgame difficulty.competitors_interval 0');

  await resetFrameProbe();
  const generationWallStart = Date.now();
  await consoleCommand('newgame 42424242', 0);

  // World generation is synchronous in this production Emscripten port. The
  // rAF probe stops during the blocking generator and resumes when the game
  // returns to the browser. Require a real >=1s stall followed by live frames.
  await page.waitForFunction(() => {
    const p = window.__otPerfProbe;
    return p && p.maxFrameGap >= 1000 && p.frames >= 8 && performance.now() - p.lastFrame < 1000;
  }, { timeout: 720000, polling: 250 });
  const generationWallMs = Date.now() - generationWallStart;
  await sleep(3000);
  result.generation4096 = {
    wallMsUntilResponsive: generationWallMs,
    snapshot: await snapshot('4096-generated'),
  };

  // Let all zero-interval competitors initialize and run. On optimized builds
  // native telemetry proves the exact active-AI count and scheduler budget.
  await resetFrameProbe();
  const aiSampleStart = Date.now();
  await sleep(30000);
  result.ai14 = {
    sampleWallMs: Date.now() - aiSampleStart,
    snapshot: await snapshot('14-ai-30s'),
  };

  result.renderer = {
    active: result.ai14.snapshot.rendererActive,
    upload: result.ai14.snapshot.upload,
    partialUploadRatio: (() => {
      const s = result.ai14.snapshot.upload;
      if (!s) return null;
      const n = (s.partialUploads || 0) + (s.fullUploads || 0);
      return n ? (s.partialUploads || 0) / n : 0;
    })(),
  };
  result.aiScheduler = result.ai14.snapshot.aiStats;
  result.memory = {
    wasmHeapBytes: result.ai14.snapshot.wasmHeapBytes,
    browserMemory: result.ai14.snapshot.browserMemory,
    puppeteerMetrics: result.ai14.snapshot.puppeteerMetrics,
  };

  result.network = {
    responses: Object.fromEntries(responses),
    failedRequests: requestFailures,
    blockedExternal,
  };
  result.console = {
    pageErrors,
    tail: consoleLines.slice(-250),
  };

  // Common hard pass criteria are intentionally the same for baseline and
  // optimized packages. Extra optimized-only gates verify the new mechanisms.
  if (!result.renderer.active) throw new Error('WebGL framebuffer presenter did not activate');
  if (pageErrors.length) throw new Error(`page errors during benchmark: ${pageErrors.join('\n')}`);
  if (profile === 'optimized') {
    if (!result.renderer.upload) throw new Error('WebGL upload telemetry is missing');
    if ((result.renderer.upload.partialUploads || 0) < 1) throw new Error('No dirty-rect partial uploads were observed');
    if (!result.aiScheduler) throw new Error('AI scheduler telemetry is missing');
    if (result.aiScheduler.activeAI !== 14) throw new Error(`Expected 14 active AI, got ${result.aiScheduler.activeAI}`);
    if (!(result.aiScheduler.effectiveOpcodeBudget > 0 && result.aiScheduler.effectiveOpcodeBudget < result.aiScheduler.configuredOpcodeBudget)) {
      throw new Error(`AI opcode budget did not scale down: ${JSON.stringify(result.aiScheduler)}`);
    }
  }

  await page.screenshot({ path: output.replace(/\.json$/i, '-final.png'), fullPage: true });
} catch (error) {
  failure = String(error?.stack || error);
  try { await page.screenshot({ path: output.replace(/\.json$/i, '-failure.png'), fullPage: true }); } catch (_) {}
}

result.finishedAt = new Date().toISOString();
result.passed = !failure;
result.failure = failure;
result.network.responses = result.network.responses || Object.fromEntries(responses);
result.network.failedRequests = result.network.failedRequests || requestFailures;
result.network.blockedExternal = result.network.blockedExternal || blockedExternal;
result.console.pageErrors = result.console.pageErrors || pageErrors;
result.console.tail = result.console.tail || consoleLines.slice(-250);
fs.writeFileSync(output, JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
await browser.close();
if (failure) process.exit(1);
