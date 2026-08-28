#!/usr/bin/env node
'use strict';

const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

(async () => {
  let visibilityListener = null;
  let resumeCalls = 0;

  class FakeAudioContext {
    constructor() {
      this.state = 'suspended';
    }
    resume() {
      resumeCalls++;
      this.state = 'running';
      return Promise.resolve();
    }
    suspend() {
      this.state = 'suspended';
      return Promise.resolve();
    }
  }

  const document = {
    hidden: false,
    documentElement: { dataset: {} },
    querySelectorAll() { return []; },
    addEventListener(name, listener) {
      if (name === 'visibilitychange') visibilityListener = listener;
    },
  };

  const context = {
    console,
    Promise,
    Set,
    Map,
    Array,
    Object,
    String,
    Number,
    Boolean,
    Date,
    Error,
    Proxy,
    Reflect,
    setTimeout,
    clearTimeout,
    document,
    navigator: {
      language: 'en-US',
      userActivation: { hasBeenActive: false },
    },
    AudioContext: FakeAudioContext,
  };
  context.window = context;

  vm.createContext(context);
  vm.runInContext(fs.readFileSync('playgama/playgama-yandex-compat.js', 'utf8'), context, {
    filename: 'playgama/playgama-yandex-compat.js',
  });

  const bridgeResult = await context.playgamaBridgeReady;
  assert.strictEqual(bridgeResult, null, 'missing Bridge must resolve to offline mode');
  assert.strictEqual(document.documentElement.dataset.playgamaBridge, 'failed');

  const sdk = await context.YaGames.init();
  assert(sdk, 'offline pseudo SDK must be returned');
  assert.strictEqual(context.ysdk, sdk, 'offline SDK must be published as ysdk');
  assert.strictEqual(sdk.environment.app.id, 'playgama');
  assert.strictEqual(await sdk.isAvailableMethod('features.LoadingAPI.ready'), true);
  assert.strictEqual(await sdk.features.LoadingAPI.ready(), true);

  let adError = 0;
  sdk.adv.showFullscreenAdv({ callbacks: { onError() { adError++; } } });
  assert.strictEqual(adError, 1, 'unsupported offline ad must fail via callback instead of throwing');

  assert(visibilityListener, 'visibilitychange handler was not installed');
  const audio = new context.AudioContext();
  assert(audio, 'wrapped AudioContext was not constructible');

  document.hidden = true;
  visibilityListener();
  document.hidden = false;
  visibilityListener();
  await Promise.resolve();
  assert.strictEqual(resumeCalls, 0, 'AudioContext resumed without user activation');

  context.navigator.userActivation.hasBeenActive = true;
  document.hidden = true;
  visibilityListener();
  document.hidden = false;
  visibilityListener();
  await Promise.resolve();
  assert.strictEqual(resumeCalls, 1, 'AudioContext did not resume after user activation');

  console.log('Playgama offline startup fallback passed.');
})().catch(error => {
  console.error(error);
  process.exit(1);
});
