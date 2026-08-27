#!/usr/bin/env node
'use strict';

const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const MAX = Number.MAX_SAFE_INTEGER;

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function makeBaseContext() {
  const storage = new Map();
  let snapshot = '';
  const context = {
    console,
    Promise,
    Number,
    String,
    Math,
    Date,
    Array,
    Object,
    Set,
    Map,
    Error,
    JSON,
    setTimeout,
    clearTimeout,
    queueMicrotask,
    localStorage: {
      getItem(key) { return storage.has(key) ? storage.get(key) : null; },
      setItem(key, value) { storage.set(key, String(value)); },
    },
    FS: {
      mkdirTree() {},
      writeFile(path, data) {
        if (String(path).endsWith('/global-ranking.tsv')) snapshot = String(data);
      },
    },
    getSnapshot() { return snapshot; },
  };
  context.window = context;
  return context;
}

async function testPlaygama() {
  const context = makeBaseContext();
  let authCalls = 0;
  let setScoreCalls = 0;
  let lastSubmitted = null;
  let getEntriesCalls = 0;

  const player = {
    id: 'player-me',
    isAuthorizationSupported: true,
    isAuthorized: false,
    async authorize() {
      authCalls++;
      this.isAuthorized = true;
    },
  };
  const bridge = {
    player,
    leaderboards: {
      type: 'in_game',
      async getEntries(name) {
        assert.strictEqual(name, 'companyrating');
        getEntriesCalls++;
        return [{ rank: 0, score: MAX, id: 'player-me', name: 'Playgama Tester' }];
      },
      async setScore(name, score) {
        assert.strictEqual(name, 'companyrating');
        setScoreCalls++;
        lastSubmitted = score;
      },
    },
  };
  context.bridge = bridge;
  context.playgamaBridgeReady = Promise.resolve(bridge);

  vm.createContext(context);
  vm.runInContext(fs.readFileSync('playgama/openttd-global-ranking.js', 'utf8'), context, {
    filename: 'playgama/openttd-global-ranking.js',
  });

  assert.strictEqual(context.OpenTTDGlobalRanking.leaderboardName, 'companyrating');
  assert.strictEqual(context.OpenTTDGlobalRanking.maxScore, MAX);
  await context.OpenTTDGlobalRanking.requestEntries(true);
  const snapshot = context.getSnapshot();
  assert(snapshot.includes(`entry\t1\t${MAX}\t1\tPlaygama Tester`), snapshot);

  context.OpenTTDGlobalRanking.submitScore(String(MAX));
  await sleep(1650);
  assert.strictEqual(authCalls, 0, 'Playgama auth must never auto-open on score submission');
  assert.strictEqual(setScoreCalls, 0, 'unauthorized Playgama score must stay pending');

  const authorized = await context.OpenTTDGlobalRanking.requestAuth();
  assert.strictEqual(authorized, true);
  assert.strictEqual(authCalls, 1, 'Playgama auth should happen only after explicit requestAuth');
  assert.strictEqual(setScoreCalls, 1);
  assert.strictEqual(lastSubmitted, MAX);
  assert(getEntriesCalls >= 1);

  console.log('Playgama ranking provider passed.');
}

async function testYandex() {
  const context = makeBaseContext();
  let authCalls = 0;
  let setScoreCalls = 0;
  let lastSubmitted = null;
  let getEntriesCalls = 0;
  let authorized = false;

  const player = {
    isAuthorized() { return authorized; },
  };
  const sdk = {
    async getPlayer() { return player; },
    async isAvailableMethod(name) {
      return name === 'leaderboards.setScore';
    },
    auth: {
      async openAuthDialog() {
        authCalls++;
        authorized = true;
      },
    },
    leaderboards: {
      async getEntries(name) {
        assert.strictEqual(name, 'companyrating');
        getEntriesCalls++;
        return {
          userRank: authorized ? 0 : -1,
          entries: [{ rank: 0, score: MAX, player: { publicName: 'Yandex Tester' } }],
        };
      },
      async setScore(name, score) {
        assert.strictEqual(name, 'companyrating');
        setScoreCalls++;
        lastSubmitted = score;
      },
    },
  };
  context.ysdk = sdk;
  context.yandexGamesSDKReady = Promise.resolve(sdk);

  vm.createContext(context);
  vm.runInContext(fs.readFileSync('yandex/openttd-global-ranking.js', 'utf8'), context, {
    filename: 'yandex/openttd-global-ranking.js',
  });

  assert.strictEqual(context.OpenTTDGlobalRanking.leaderboardName, 'companyrating');
  assert.strictEqual(context.OpenTTDGlobalRanking.maxScore, MAX);
  await context.OpenTTDGlobalRanking.requestEntries(true);

  context.OpenTTDGlobalRanking.submitScore(String(MAX));
  await sleep(1650);
  assert.strictEqual(authCalls, 0, 'Yandex auth must never auto-open on score submission');
  assert.strictEqual(setScoreCalls, 0, 'unauthorized Yandex score must stay pending');

  const signedIn = await context.OpenTTDGlobalRanking.requestAuth();
  assert.strictEqual(signedIn, true);
  assert.strictEqual(authCalls, 1, 'Yandex auth should happen only after explicit requestAuth');
  assert.strictEqual(setScoreCalls, 1);
  assert.strictEqual(lastSubmitted, MAX);
  assert(getEntriesCalls >= 1);

  const snapshot = context.getSnapshot();
  assert(snapshot.includes(`${MAX}`), snapshot);
  assert(snapshot.includes('Yandex Tester'), snapshot);

  console.log('Yandex ranking provider passed.');
}

(async () => {
  await testPlaygama();
  await testYandex();
  console.log('Dual-platform ranking provider test passed.');
})().catch(error => {
  console.error(error);
  process.exit(1);
});
