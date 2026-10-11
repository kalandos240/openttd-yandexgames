#!/usr/bin/env node
/* Exercise the actual packaged Yandex-V29 bridge with Playgama ad policy. */
'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const source = fs.readFileSync(process.argv[2] || 'dist-playgama/yandex-bridge.js', 'utf8');

async function main() {
  let now = 1_000_000;
  const scheduled = new Map();
  let nextTimer = 1;
  const calls = { shown: 0, started: 0, stopped: 0, paused: [], closes: 0 };
  const elements = new Map();
  const makeElement = (tag) => ({
    tag, id: '', style: {}, textContent: '', innerHTML: '',
    setAttribute() {},
    append(...children) { children.forEach(c => { if (c.id) elements.set(c.id, c); }); },
    querySelector(query) { return elements.get(query.replace('#', '')) || null; },
  });
  const doc = {
    hidden: false,
    body: { append(el) { elements.set(el.id, el); } },
    addEventListener() {}, getElementById(id) { return elements.get(id) || null; },
    createElement: makeElement,
  };
  const SDK = {
    getPlayer: async () => null,
    features: { GameplayAPI: {
      start() { calls.started++; }, stop() { calls.stopped++; },
    } },
    adv: { showFullscreenAdv({ callbacks }) {
      calls.shown++;
      callbacks.onOpen?.();
      callbacks.onClose?.();
      calls.closes++;
    } },
    on() {},
  };
  const FakeDate = class extends Date { static now() { return now; } };
  const ctx = {
    document: doc, navigator: { language: 'en-US' },
    Date: FakeDate, Promise, console,
    clearInterval() {}, setInterval() { return 1; },
    setTimeout(fn, ms) { const id = nextTimer++; scheduled.set(id, { fn, ms }); return id; },
    clearTimeout(id) { scheduled.delete(id); },
    addEventListener() {},
    yandexGamesSDKReady: Promise.resolve(SDK),
    Module: { calledRun: true, _em_openttd_set_platform_pause(pause) { calls.paused.push(pause); } },
  };
  ctx.window = ctx;
  vm.runInNewContext(source, ctx, { filename: 'yandex-bridge.js' });
  assert.equal(typeof ctx.yandexGameSetGameplay, 'function');
  await Promise.resolve();

  ctx.yandexGameSetGameplay(true);
  await Promise.resolve();
  assert.equal([...scheduled.values()].some(timer => timer.ms >= 180_000), false,
    'A gameplay-interrupting ad timer must never be scheduled');
  now += 181_000;
  assert.equal(calls.shown, 0, 'No ad may interrupt active OpenTTD gameplay');

  ctx.yandexGameSetGameplay(false);
  for (let i = 0; i < 15 && !calls.shown; i++) {
    await Promise.resolve();
    for (const [id, timer] of [...scheduled]) {
      if (timer.ms <= 1_000) { scheduled.delete(id); timer.fn(); }
    }
  }
  assert.equal(calls.shown, 1, 'One ad should be offered at the natural pause');
  assert.equal(calls.closes, 1, 'The advertisement lifecycle must finish');
  assert.equal(calls.paused.at(-1), 0, 'The game must be unpaused when the ad closes');
  console.log('Playgama V29 natural-break advertising behavior: PASS');
}
main().catch(err => { console.error(err); process.exitCode = 1; });
