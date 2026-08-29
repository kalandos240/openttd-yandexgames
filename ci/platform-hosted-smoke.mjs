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
const consoleLines = [];

page.on('response', response => {
  try {
    const u = new URL(response.url());
    responses.set(u.pathname, response.status());
  } catch (_) {}
});
page.on('pageerror', error => pageErrors.push(String(error?.stack || error)));
page.on('requestfailed', request => failedRequests.push(`${request.url()} :: ${request.failure()?.errorText || 'failed'}`));
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

let result = {};
let failure = null;
try {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForFunction(() => window.Module?.calledRun === true, { timeout: 60000, polling: 100 });
  await new Promise(resolve => setTimeout(resolve, 5000));

  result = await page.evaluate((platformName) => {
    const canvas = document.getElementById('canvas');
    const box = document.getElementById('box');
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
      platformName,
    };
  }, platform);

  for (const path of ['/openttd-runtime.js', '/openttd.wasm', '/openttd.data']) {
    if (responses.get(path) !== 200) throw new Error(`required resource ${path} did not return HTTP 200; got ${responses.get(path)}`);
  }
  if (!result.calledRun) throw new Error('Emscripten Module.calledRun is false');
  if (result.canvasWidth <= 0 || result.canvasHeight <= 0 || result.canvasDisplay === 'none') throw new Error(`canvas is not running: ${JSON.stringify(result)}`);
  if (result.boxError) throw new Error(`OpenTTD crash box is visible: ${JSON.stringify(result)}`);
  if (platform === 'yandex' && result.yandexSdk !== 'ready') throw new Error(`Yandex SDK path did not initialize: ${JSON.stringify(result)}`);
  if (platform === 'playgama' && result.playgamaBridge !== 'ready') throw new Error(`Playgama Bridge path did not initialize: ${JSON.stringify(result)}`);
  if (pageErrors.length) throw new Error(`page errors: ${pageErrors.join('\n')}`);
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
  consoleTail: consoleLines.slice(-160),
};
fs.writeFileSync(output, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
await browser.close();
if (failure) process.exit(1);
