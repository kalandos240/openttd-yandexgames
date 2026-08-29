#!/usr/bin/env node
'use strict';

// This smoke test is also a release trigger: changes to native/package gates must
// be validated through the combined Playgama + Yandex v14 workflow.
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require('playwright-core');

function readText(file) {
  return fs.readFileSync(file, 'utf8');
}

function countLiteral(text, needle) {
  if (!needle) return 0;
  return text.split(needle).length - 1;
}

function preflightPackage(dist, label) {
  const failures = [];
  const indexPath = path.join(dist, 'index.html');
  const commonRequired = [
    'index.html',
    'openttd-runtime.js',
    'openttd-classic-ai.js',
    'openttd-ai-prerun.js',
    'openttd-full-viewport.js',
    'openttd-ranking-core.js',
    'openttd-global-ranking.js',
  ];

  for (const name of commonRequired) {
    if (!fs.existsSync(path.join(dist, name))) failures.push(`missing required file: ${name}`);
  }
  if (failures.length) return failures;

  const indexHtml = readText(indexPath);
  for (const name of [
    'openttd-ai-prerun.js',
    'openttd-full-viewport.js',
    'openttd-ranking-core.js',
    'openttd-global-ranking.js',
    'openttd-runtime.js',
  ]) {
    const count = countLiteral(indexHtml, name);
    if (count !== 1) failures.push(`index.html must reference ${name} exactly once (found ${count})`);
  }

  const prerun = readText(path.join(dist, 'openttd-ai-prerun.js'));
  if (!/preRun/.test(prerun)) failures.push('AI preRun installer marker is missing');
  if (/max_no_competitors\s*=|competitors_interval\s*=/.test(prerun)) {
    failures.push('AI preRun must not override max_no_competitors/competitors_interval');
  }

  const viewport = readText(path.join(dist, 'openttd-full-viewport.js'));
  if (!/Module\.setCanvasSize\s*\(/.test(viewport)) failures.push('full viewport helper does not resize the SDL backing canvas');
  if (!/(?:resize|ResizeObserver)/.test(viewport)) failures.push('full viewport helper has no resize handling');

  const ranking = readText(path.join(dist, 'openttd-ranking-core.js'));
  if (!/openttd\.localRanking\.v4/.test(ranking)) failures.push('local ranking storage is not the expected v4 implementation');

  const isYandex = /yandex/i.test(label);
  if (isYandex) {
    for (const name of ['yandex-bootstrap.js', 'yandex-bridge.js', 'openttd-yandex-fixes.js']) {
      if (!fs.existsSync(path.join(dist, name))) failures.push(`Yandex package missing ${name}`);
    }
    for (const name of ['platform-bridge-loader.js', 'openttd-playgama-fixes.js', 'playgama-yandex-compat.js']) {
      if (fs.existsSync(path.join(dist, name))) failures.push(`Yandex package contains Playgama-only file: ${name}`);
    }
    if (/bridge\.playgama\.com/i.test(indexHtml)) failures.push('Yandex index still references Playgama Bridge');
    if (fs.existsSync(path.join(dist, 'openttd-yandex-fixes.js'))) {
      const fixes = readText(path.join(dist, 'openttd-yandex-fixes.js'));
      if (/aspect-ratio\s*:\s*16\s*\/\s*9/i.test(fixes)) failures.push('Yandex fixes reintroduced the legacy 16:9 letterbox');
      if (!/width:\s*100vw\s*!important/i.test(fixes) || !/height:\s*100vh\s*!important/i.test(fixes)) {
        failures.push('Yandex full-viewport CSS is missing');
      }
    }
  } else {
    for (const name of ['platform-bridge-loader.js', 'openttd-playgama-fixes.js', 'playgama-bridge-config.json']) {
      if (!fs.existsSync(path.join(dist, name))) failures.push(`Playgama package missing ${name}`);
    }
    if (/\/sdk\.js/i.test(indexHtml)) failures.push('Playgama index unexpectedly references Yandex /sdk.js');
    if (fs.existsSync(path.join(dist, 'openttd-playgama-fixes.js'))) {
      const fixes = readText(path.join(dist, 'openttd-playgama-fixes.js'));
      if (/aspect-ratio\s*:\s*16\s*\/\s*9/i.test(fixes)) failures.push('Playgama fixes reintroduced the legacy 16:9 letterbox');
      if (!/width:\s*100vw\s*!important/i.test(fixes) || !/height:\s*100vh\s*!important/i.test(fixes)) {
        failures.push('Playgama full-viewport CSS is missing');
      }
    }
  }

  return failures;
}

async function main() {
  const [distArg, labelArg, screenshotArg] = process.argv.slice(2);
  if (!distArg) throw new Error('usage: smoke-direct-file.cjs <dist-dir> [label] [screenshot.png]');

  const dist = path.resolve(distArg);
  const index = path.join(dist, 'index.html');
  const label = labelArg || path.basename(dist);
  const screenshot = screenshotArg ? path.resolve(screenshotArg) : null;
  if (!fs.existsSync(index)) throw new Error(`${label}: missing ${index}`);

  const preflightFailures = preflightPackage(dist, label);
  if (preflightFailures.length) {
    throw new Error(`${label} package preflight failed:\n- ${preflightFailures.join('\n- ')}`);
  }

  const candidates = [
    process.env.CHROME_BIN,
    '/usr/bin/google-chrome-stable',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ].filter(Boolean);
  const executablePath = candidates.find((candidate) => fs.existsSync(candidate));
  if (!executablePath) throw new Error(`${label}: no Chrome/Chromium executable found`);

  const browser = await chromium.launch({
    headless: true,
    executablePath,
    args: [
      '--no-sandbox',
      '--disable-dev-shm-usage',
      '--allow-file-access-from-files',
      '--autoplay-policy=no-user-gesture-required',
    ],
  });

  const externalRequests = [];
  const sdkRequests = [];
  const pageErrors = [];
  const fatalConsole = [];
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });

  page.on('request', (request) => {
    const url = request.url();
    if (/^https?:\/\//i.test(url)) externalRequests.push(url);
    if (/(?:^|\/)sdk\.js(?:$|[?#])/i.test(url)) sdkRequests.push(url);
  });
  page.on('pageerror', (error) => pageErrors.push(String(error && error.stack || error)));
  page.on('console', (message) => {
    if (message.type() !== 'error') return;
    const text = message.text();
    if (/abort|uncaught|runtimeerror|out of memory|memory access out of bounds/i.test(text)) {
      fatalConsole.push(text);
    }
  });

  const target = pathToFileURL(index).href;
  await page.goto(target, { waitUntil: 'load', timeout: 30000 });

  await page.waitForFunction(() => {
    const canvas = document.querySelector('canvas');
    const moduleReady = typeof window.Module !== 'undefined' && window.Module && window.Module.calledRun === true;
    return Boolean(moduleReady && canvas && canvas.width > 0 && canvas.height > 0);
  }, null, { timeout: 45000 });

  // A called Emscripten main() is not enough: keep the page alive for several
  // seconds so immediate post-start aborts are caught as well.
  await page.waitForTimeout(5000);

  const readState = () => page.evaluate(() => {
    const canvas = document.querySelector('canvas');
    const bodyText = document.body ? document.body.innerText : '';
    const rect = canvas ? canvas.getBoundingClientRect() : { width: 0, height: 0 };
    return {
      calledRun: Boolean(window.Module && window.Module.calledRun === true),
      aborted: Boolean(window.Module && window.Module.ABORT === true),
      canvasWidth: canvas ? canvas.width : 0,
      canvasHeight: canvas ? canvas.height : 0,
      canvasClientWidth: canvas ? canvas.clientWidth : 0,
      canvasClientHeight: canvas ? canvas.clientHeight : 0,
      rectWidth: rect.width,
      rectHeight: rect.height,
      innerWidth: window.innerWidth,
      innerHeight: window.innerHeight,
      visible: Boolean(canvas && rect.width > 0 && rect.height > 0),
      bodyHasAbort: /Aborted\(|RuntimeError|memory access out of bounds/i.test(bodyText),
      directFileFlag: Boolean(window.__openttdDirectFileLaunch),
    };
  });

  const state = await readState();

  // Regression check for the old 16:9/letterbox bug. Resize to a 4:3 viewport
  // and require both CSS and SDL backing surface to follow the new dimensions.
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.waitForTimeout(750);
  const resizedState = await readState();

  if (screenshot) await page.screenshot({ path: screenshot, fullPage: true });
  await browser.close();

  const failures = [];
  if (!state.calledRun) failures.push('Emscripten Module.calledRun is false');
  if (state.aborted || state.bodyHasAbort) failures.push('runtime reported an abort');
  if (!state.visible || state.canvasWidth <= 0 || state.canvasHeight <= 0) failures.push('game canvas is not visible/initialized');
  if (externalRequests.length) failures.push(`external HTTP(S) requests during file:// launch: ${externalRequests.join(', ')}`);
  if (sdkRequests.length) failures.push(`SDK request attempted during file:// launch: ${sdkRequests.join(', ')}`);
  if (pageErrors.length) failures.push(`page errors: ${pageErrors.join(' | ')}`);
  if (fatalConsole.length) failures.push(`fatal console errors: ${fatalConsole.join(' | ')}`);

  const cssWidthDelta = Math.abs(resizedState.rectWidth - resizedState.innerWidth);
  const cssHeightDelta = Math.abs(resizedState.rectHeight - resizedState.innerHeight);
  if (cssWidthDelta > 2 || cssHeightDelta > 2) {
    failures.push(`canvas does not fill resized viewport: canvas=${resizedState.rectWidth}x${resizedState.rectHeight}, viewport=${resizedState.innerWidth}x${resizedState.innerHeight}`);
  }
  if (resizedState.canvasWidth < 1000 || resizedState.canvasHeight < 740) {
    failures.push(`SDL backing canvas did not follow resized viewport: ${resizedState.canvasWidth}x${resizedState.canvasHeight}`);
  }

  console.log(`[smoke:${label}] initial=${JSON.stringify(state)}`);
  console.log(`[smoke:${label}] resized=${JSON.stringify(resizedState)}`);
  console.log(`[smoke:${label}] external_requests=${externalRequests.length} sdk_requests=${sdkRequests.length} page_errors=${pageErrors.length}`);
  if (failures.length) throw new Error(`${label} direct-file smoke failed:\n- ${failures.join('\n- ')}`);
  console.log(`[smoke:${label}] PASS: full-feature runtime started from file://, filled the viewport, and made no external HTTP(S) or SDK requests`);
}

main().catch((error) => {
  console.error(error && error.stack || error);
  process.exit(1);
});
