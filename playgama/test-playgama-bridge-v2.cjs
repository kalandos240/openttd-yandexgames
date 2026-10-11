#!/usr/bin/env node
/* Offline Playgama Bridge v2 contract test for the Yandex V29 adapter. */
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('playgama/playgama-yandex-compat.js', 'utf8');

function makeEnvironment(options = {}) {
  const values = new Map([
    ['settings', { sound: false }],
    ['empty', null],
    ['zero', 0],
  ]);
  const calls = { get: [], set: [], messages: [], ads: 0, initialize: 0 };
  const adListeners = new Map();
  const bridge = {
    version: '2.0.0',
    engine: null,
    initialize: async () => { calls.initialize++; },
    EVENT_NAME: {
      INTERSTITIAL_STATE_CHANGED: 'interstitial_state_changed',
      PAUSE_STATE_CHANGED: 'pause_state_changed',
      AUDIO_STATE_CHANGED: 'audio_state_changed',
    },
    INTERSTITIAL_STATE: { OPENED: 'opened', CLOSED: 'closed', FAILED: 'failed' },
    PLATFORM_MESSAGE: {
      GAME_READY: 'game_ready',
      GAMEPLAY_STARTED: 'gameplay_started',
      GAMEPLAY_STOPPED: 'gameplay_stopped',
    },
    platform: {
      language: 'ru-RU',
      id: 'playgama',
      isAudioEnabled: true,
      on() {},
      async sendMessage(message) { calls.messages.push(message); },
    },
    player: {
      id: 'player-1',
      name: 'Test player',
      isAuthorized: true,
      isAuthorizationSupported: true,
      async authorize() {},
    },
    storage: {
      async get(keys) {
        assert.equal(Array.isArray(keys), true, 'Bridge v2 storage.get needs a key array');
        calls.get.push(Array.from(keys));
        if (options.failRead) throw new Error('cloud read rejected');
        return keys.map((key) => values.has(key) ? values.get(key) : null);
      },
      async set(keys, contents) {
        assert.equal(Array.isArray(keys), true, 'Bridge v2 storage.set needs a key array');
        assert.equal(Array.isArray(contents), true, 'Bridge v2 storage.set needs a value array');
        calls.set.push({ keys: Array.from(keys), contents: Array.from(contents) });
        if (options.failWrite) throw new Error('cloud write rejected');
        keys.forEach((key, index) => values.set(key, contents[index]));
      },
    },
    advertisement: {
      isInterstitialSupported: options.adsSupported !== false,
      setMinimumDelayBetweenInterstitial(seconds) { calls.minimumAdDelay = seconds; },
      on(name, listener) { adListeners.set(name, listener); },
      off(name) { adListeners.delete(name); },
      showInterstitial() {
        calls.ads++;
        const listener = adListeners.get('interstitial_state_changed');
        if (listener) {
          listener('opened');
          listener('closed');
        }
      },
    },
    leaderboards: {
      type: options.leaderboardType || 'in_game',
      async setScore(id, score) { calls.score = [id, score]; },
      async getEntries() {
        return [{ id: 'player-1', name: 'Alice', score: 42, rank: 1, photo: '' }];
      },
    },
  };
  const document = {
    hidden: false,
    documentElement: { dataset: {} },
    querySelectorAll: () => [],
    addEventListener: () => {},
  };
  const env = {
    bridge, document, navigator: { language: 'en-US' }, console,
    Promise, setTimeout, clearTimeout,
  };
  env.window = env;
  vm.runInNewContext(source, env, { filename: 'playgama-yandex-compat.js' });
  return { env, calls, values };
}

async function main() {
  const { env, calls } = makeEnvironment();
  const sdk = await env.yandexGamesSDKReady;
  assert.ok(sdk, 'Playgama bridge must initialize and create SDK adapter');
  assert.equal(calls.initialize, 1);
  assert.equal(env.bridge.engine, 'javascript');
  assert.equal(env.document.documentElement.dataset.playgamaBridge, 'ready');
  assert.equal(sdk.environment.i18n.lang, 'ru');
  assert.equal(env.yandexGameLanguage, 'ru');

  const player = await sdk.getPlayer();
  assert.deepEqual(await player.getData([]), {});
  const loaded = await player.getData(['settings', 'empty', 'zero']);
  assert.equal(loaded.settings.sound, false);
  assert.equal('empty' in loaded, false);
  assert.equal(loaded.zero, 0);
  assert.deepEqual(calls.get.map((keys) => keys.join(',')), ['settings,empty,zero'],
    'Bridge must not use an undocumented single-key or startup marker call');

  await player.setData({ settings: { sound: true }, progress: 'saved' });
  assert.deepEqual(calls.set.map((write) => write.keys.join(',')), ['settings,progress']);
  assert.equal(calls.set[0].contents[1], 'saved');
  assert.equal((await player.getData(['settings'])).settings.sound, true);

  await sdk.features.LoadingAPI.ready();
  await sdk.features.LoadingAPI.ready();
  await sdk.features.GameplayAPI.start();
  await sdk.features.GameplayAPI.stop();
  assert.deepEqual(calls.messages, ['game_ready', 'gameplay_started', 'gameplay_stopped']);

  let opened = 0;
  let closed = 0;
  sdk.adv.showFullscreenAdv({ callbacks: {
    onOpen() { opened++; },
    onClose() { closed++; },
  } });
  assert.equal(calls.ads, 1);
  assert.equal(opened, 1);
  assert.equal(closed, 1);
  assert.equal(calls.minimumAdDelay, 150);

  assert.equal(await sdk.isAvailableMethod('leaderboards.getEntries'), true);
  assert.equal(await sdk.isAvailableMethod('leaderboards.setScore'), true);
  const rows = await sdk.leaderboards.getEntries('companyrating');
  assert.equal(rows.userRank, 1);
  assert.equal(rows.entries[0].player.publicName, 'Alice');
  assert.equal(await sdk.isAvailableMethod('auth.openAuthDialog'), true);

  const unavailable = await makeEnvironment({ leaderboardType: 'not_available', adsSupported: false })
    .env.yandexGamesSDKReady;
  assert.equal(await unavailable.isAvailableMethod('leaderboards.getEntries'), false);
  assert.equal(await unavailable.isAvailableMethod('leaderboards.setScore'), false);
  assert.equal(await unavailable.isAvailableMethod('adv.showFullscreenAdv'), false);

  const failedRead = await makeEnvironment({ failRead: true }).env.yandexGamesSDKReady;
  await assert.rejects(
    (await failedRead.getPlayer()).getData(['progress']),
    /cloud read rejected/,
    'Do not interpret cloud read failure as an empty save'
  );

  const failedWrite = await makeEnvironment({ failWrite: true }).env.yandexGamesSDKReady;
  await assert.rejects(
    (await failedWrite.getPlayer()).setData({ progress: 'important' }),
    /cloud write rejected/,
    'Do not report a failed cloud write as a successful save'
  );

  console.log('Playgama Bridge v2 adapter contract checks: PASS');
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
