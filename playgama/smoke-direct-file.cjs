#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require('playwright-core');

async function main() {
  const [distArg, labelArg, screenshotArg] = process.argv.slice(2);
  if (!distArg) throw new Error('usage: smoke-direct-file.cjs <dist-dir> [label] [screenshot.png]');

  const dist = path.resolve(distArg);
  const index = path.join(dist, 'index.html');
  const label = labelArg || path.basename(dist);
  const screenshot = screenshotArg ? path.resolve(screenshotArg) : null;
  if (!fs.existsSync(index)) throw new Error(`${label}: missing ${index}`);

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

  const state = await page.evaluate(() => {
    const canvas = document.querySelector('canvas');
    const bodyText = document.body ? document.body.innerText : '';
    return {
      calledRun: Boolean(window.Module && window.Module.calledRun === true),
      aborted: Boolean(window.Module && window.Module.ABORT === true),
      canvasWidth: canvas ? canvas.width : 0,
      canvasHeight: canvas ? canvas.height : 0,
      canvasClientWidth: canvas ? canvas.clientWidth : 0,
      canvasClientHeight: canvas ? canvas.clientHeight : 0,
      visible: Boolean(canvas && canvas.getBoundingClientRect().width > 0 && canvas.getBoundingClientRect().height > 0),
      bodyHasAbort: /Aborted\(|RuntimeError|memory access out of bounds/i.test(bodyText),
      directFileFlag: Boolean(window.__openttdDirectFileLaunch),
    };
  });

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

  console.log(`[smoke:${label}] ${JSON.stringify(state)}`);
  console.log(`[smoke:${label}] external_requests=${externalRequests.length} sdk_requests=${sdkRequests.length} page_errors=${pageErrors.length}`);
  if (failures.length) throw new Error(`${label} direct-file smoke failed:\n- ${failures.join('\n- ')}`);
  console.log(`[smoke:${label}] PASS: game runtime started from file:// with no external HTTP(S) or SDK requests`);
}

main().catch((error) => {
  console.error(error && error.stack || error);
  process.exit(1);
});
