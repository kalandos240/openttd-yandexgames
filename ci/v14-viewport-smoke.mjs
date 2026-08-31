import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import path from 'node:path';

const [platform, url, outputDir] = process.argv.slice(2);
if (!platform || !url || !outputDir) {
  throw new Error('usage: v14-viewport-smoke.mjs <yandex|playgama> <url> <output-dir>');
}
const executablePath = process.env.CHROME_BIN;
if (!executablePath) throw new Error('CHROME_BIN is not set');
fs.mkdirSync(outputDir, { recursive: true });

const sizes = [
  { width: 640, height: 360, name: '640x360' },
  { width: 1280, height: 720, name: '1280x720' },
  { width: 1920, height: 1080, name: '1920x1080' },
];

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
  ],
});

const report = { platform, url, passed: true, cases: [] };
for (const size of sizes) {
  const page = await browser.newPage();
  await page.setViewport({ width: size.width, height: size.height, deviceScaleFactor: 1 });
  const errors = [];
  const blockedExternal = [];
  page.on('pageerror', error => errors.push(String(error?.stack || error)));
  await page.setRequestInterception(true);
  page.on('request', request => {
    try {
      const u = new URL(request.url());
      if ((u.protocol === 'http:' || u.protocol === 'https:') && u.hostname !== '127.0.0.1' && u.hostname !== 'localhost') {
        blockedExternal.push(request.url());
        request.abort('blockedbyclient');
        return;
      }
    } catch (_) {}
    request.continue();
  });

  let failure = null;
  let metrics = {};
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await page.waitForFunction(() => window.Module?.calledRun === true, { timeout: 120000, polling: 100 });
    await new Promise(resolve => setTimeout(resolve, 2500));
    metrics = await page.evaluate(() => {
      const canvas = document.getElementById('canvas');
      const box = document.getElementById('box');
      const rect = canvas?.getBoundingClientRect();
      const boxRect = box?.getBoundingClientRect();
      return {
        innerWidth: window.innerWidth,
        innerHeight: window.innerHeight,
        documentWidth: document.documentElement.scrollWidth,
        documentHeight: document.documentElement.scrollHeight,
        canvas: rect ? {
          left: rect.left,
          top: rect.top,
          right: rect.right,
          bottom: rect.bottom,
          width: rect.width,
          height: rect.height,
          backingWidth: canvas.width,
          backingHeight: canvas.height,
          display: getComputedStyle(canvas).display,
        } : null,
        box: boxRect ? {
          left: boxRect.left,
          top: boxRect.top,
          right: boxRect.right,
          bottom: boxRect.bottom,
          width: boxRect.width,
          height: boxRect.height,
          error: box.classList.contains('error'),
        } : null,
      };
    });

    const c = metrics.canvas;
    if (!c || c.width <= 0 || c.height <= 0 || c.display === 'none') throw new Error('canvas is missing or hidden');
    const eps = 1.5;
    if (c.left < -eps || c.top < -eps || c.right > metrics.innerWidth + eps || c.bottom > metrics.innerHeight + eps) {
      throw new Error(`canvas exceeds viewport: ${JSON.stringify(c)} vs ${metrics.innerWidth}x${metrics.innerHeight}`);
    }
    if (metrics.box?.error) throw new Error('runtime crash/error box is visible');
    if (metrics.documentWidth > metrics.innerWidth + eps || metrics.documentHeight > metrics.innerHeight + eps) {
      throw new Error(`document overflows viewport: ${metrics.documentWidth}x${metrics.documentHeight}`);
    }
    if (errors.length) throw new Error(`page errors: ${errors.join('\n')}`);
  } catch (error) {
    failure = String(error?.stack || error);
    report.passed = false;
  }

  const screenshot = path.join(outputDir, `${platform}-${size.name}.png`);
  try { await page.screenshot({ path: screenshot, fullPage: true }); } catch (_) {}
  report.cases.push({ ...size, passed: !failure, failure, metrics, errors, blockedExternal, screenshot });
  await page.close();
}

fs.writeFileSync(path.join(outputDir, `${platform}-viewport.json`), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
await browser.close();
if (!report.passed) process.exit(1);
