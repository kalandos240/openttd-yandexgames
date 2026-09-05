#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(process.argv[2] || '.');
const viewportPath = path.join(root, 'openttd-full-viewport.js');
const indexPath = path.join(root, 'index.html');

const fail = message => {
  console.error(`V28_SYSTEM_CURSOR_REGRESSION=FAIL: ${message}`);
  process.exit(1);
};

if (!fs.existsSync(viewportPath)) fail('openttd-full-viewport.js missing');
if (!fs.existsSync(indexPath)) fail('index.html missing');

const viewport = fs.readFileSync(viewportPath, 'utf8');
const index = fs.readFileSync(indexPath, 'utf8');

const legacy = "canvas.style.setProperty('cursor', box.touchUi ? 'none' : 'auto', 'important');";
const expected = "canvas.style.setProperty('cursor', 'none', 'important');";

if (viewport.includes(legacy)) fail('V27 desktop cursor:auto override is still present');
if (!viewport.includes(expected)) fail('canvas cursor:none runtime override is missing');
if (!viewport.includes('V28: OpenTTD renders its own cursor; suppress the host OS cursor.')) {
  fail('V28 marker missing');
}

const cursorCalls = [...viewport.matchAll(/canvas\.style\.setProperty\('cursor',\s*([^,]+),\s*'important'\);/g)];
if (cursorCalls.length < 1) fail('no adaptive canvas cursor assignment found');
for (const match of cursorCalls) {
  if (match[1].trim() !== "'none'") {
    fail(`unexpected adaptive cursor value: ${match[1].trim()}`);
  }
}

const compactIndex = index.replace(/\s+/g, '');
if (!compactIndex.includes('canvas.emscripten{') || !compactIndex.includes('cursor:none!important')) {
  fail('startup canvas cursor:none CSS missing');
}

console.log('V28_SYSTEM_CURSOR_REGRESSION=PASS');
console.log(`adaptive_cursor_assignments=${cursorCalls.length}`);
console.log('desktop_system_cursor=hidden');
console.log('openttd_software_cursor=preserved');
console.log('touch_cursor=hidden');
