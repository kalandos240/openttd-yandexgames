#!/usr/bin/env node
'use strict';
/* Unit/integration tests for the EXACT cloud script shipped with the V29 port.
   Fake storage strictly enforces the documented Playgama Bridge v2 array API. */
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('playgama/openttd-playgama-cloud-saves.js', 'utf8');

function bytes(size, seed=7) {
  const result = new Uint8Array(size);
  for (let i=0; i<size; i++) result[i] = (i * 37 + (i >> 7) + seed) & 255;
  return result;
}

function storage() {
  const map = new Map(), writes=[];
  let failKey = null, available = true;
  return {
    map, writes,
    get failKey() { return failKey; }, set failKey(v) { failKey=v; },
    get available() { return available; }, set available(v) { available=v; },
    impl: {
      isSupported(type) { return type === 'platform_internal'; },
      isAvailable(type) { return type === 'platform_internal' && available; },
      async get(keys, type) {
        assert.equal(type, 'platform_internal');
        assert.equal(Array.isArray(keys), true, 'Bridge.get requires key arrays');
        return keys.map(k => map.has(k) ? map.get(k) : null);
      },
      async set(keys, values, type) {
        assert.equal(type, 'platform_internal');
        assert.equal(Array.isArray(keys), true, 'Bridge.set requires key arrays');
        assert.equal(Array.isArray(values), true, 'Bridge.set requires value arrays');
        assert.equal(keys.length, values.length);
        if (keys.some(k => k.includes(failKey) && failKey)) throw new Error('simulated interrupted write');
        for(let i=0; i<keys.length; i++) { map.set(keys[i], values[i]); writes.push(keys[i]); }
      },
    },
  };
}

function filesystem(original={}) {
  const files = new Map(), directories = new Set(['/','/home','/home/openttd','/home/openttd/save']);
  let clock = Date.now();
  function write(path, content) {
    const contentBytes = typeof content === 'string' ? content : Uint8Array.from(content);
    files.set(path,{content:contentBytes,mtime:++clock});
  }
  for(const [p,v] of Object.entries(original)) write(p,v);
  return {
    files,
    mkdir(path) { directories.add(path); },
    readdir(path) {
      if(!directories.has(path)) throw new Error('missing directory: '+path);
      const children = new Set(['.','..']);
      for(const p of [...files.keys(), ...directories]) {
        if(p.startsWith(path+'/')) {
          const rest = p.substring(path.length+1);
          if(rest && !rest.includes('/')) children.add(rest);
        }
      }
      return [...children];
    },
    stat(path) {
      if(directories.has(path)) return {mode:0x4000,mtime:new Date(clock)};
      const f=files.get(path);
      if(!f) throw new Error('missing file: '+path);
      return {mode:0x8000,size:typeof f.content === 'string' ? f.content.length : f.content.length,mtime:new Date(f.mtime)};
    },
    isDir(mode) {return mode===0x4000;},
    isFile(mode) {return mode===0x8000;},
    readFile(path, options) {
      const f=files.get(path);
      if(!f) throw new Error('missing: '+path);
      return options?.encoding === 'utf8' ? String(f.content) : f.content;
    },
    writeFile(path, data) {write(path,data);},
    utime(path, date) {
      const f=files.get(path); if(f) f.mtime=date.getTime();
    },
    syncfs(populate, callback) {callback(null);},
  };
}
function boot(storageBackend, fsApi) {
  const logs = { errors:[],warnings:[] };
  const env={
    bridge: {storage:storageBackend.impl, STORAGE_TYPE:{PLATFORM_INTERNAL:'platform_internal'}},
    Module:{calledRun:true,postRun:[]}, console:{
      info() {}, warn(...args){logs.warnings.push(args);},error(...args){logs.errors.push(args);}
    },
    Uint8Array, Date, Promise, btoa, atob, setTimeout, clearTimeout,
    requestIdleCallback(callback) {setTimeout(callback,0);},
  };
  env.window=env;env.playgamaBridgeReady=Promise.resolve(env.bridge);
  vm.runInNewContext(source, env, {filename:'openttd-playgama-cloud-saves.js'});
  const dir='/home/openttd';
  return {
    env,logs,fs:fsApi,
    save: () => env.__openttdPlaygamaCloudDebug.forceBackup(fsApi,dir),
    restore: () => env.yandexRestoreOpenTTDCloud(fsApi,dir),
    status: () => env.__openttdPlaygamaCloudStatus,
  };
}
function same(actual, expected) {
  assert.deepEqual(Buffer.from(actual), Buffer.from(expected));
}
async function main() {
  const backend=storage();
  const dir='/home/openttd/save/';
  const first = bytes(512*1024 + 17);
  const second = bytes(600*1024 + 7, 13);
  const third = bytes(513*1024 + 11, 23);
  const fs1=filesystem({[dir+'transport.sav']:first, '/home/openttd/openttd.cfg':'[misc]\nlanguage = russian.lng'});
  let app=boot(backend,fs1);
  assert.equal(app.env.__openttdPlaygamaCloudDebug.maxSaveBytes > 120000,true);
  await app.save();
  assert.equal(app.status()?.backup?.state,'uploaded', JSON.stringify(app.status()));
  assert.equal(app.status().backup.slot,'a');
  assert.equal(backend.map.get('openttdSaveMetaV2A').chunks>4,true);
  assert.equal(backend.writes.at(-1),'openttdSaveMetaV2A','commit metadata last');

  const fs2=filesystem();
  app=boot(backend,fs2);
  await app.restore();
  same(fs2.readFile(dir+'transport.sav'),first);
  assert.equal(app.status().restored,true);

  // After a newer B-generation is stored, an interrupted A-generation
  // cannot make users lose the previously committed B snapshot.
  fs2.writeFile(dir+'transport.sav',second);
  await app.save();
  assert.equal(app.status().backup.slot,'b');
  backend.failKey='openttdSaveChunkV2A_';
  fs2.writeFile(dir+'transport.sav',third);
  await app.save();
  assert.equal(app.status().backup?.state,'uploaded',false);
  assert.match(app.status().error,/simulated interrupted write/);
  assert.equal(backend.map.get('openttdSaveMetaV2A').slot,'a');
  backend.failKey=null;
  const fs3=filesystem();
  app=boot(backend,fs3);
  await app.restore();
  same(fs3.readFile(dir+'transport.sav'),second);

  // A successful new A generation takes priority. If its chunks are corrupt,
  // the older committed B slot must still be recoverable.
  fs2.writeFile(dir+'transport.sav',third);
  await boot(backend,fs2).save();
  backend.map.set('openttdSaveChunkV2A_0001', 'tampered');
  const fs4=filesystem();
  app=boot(backend,fs4);
  await app.restore();
  same(fs4.readFile(dir+'transport.sav'),second);

  // Legacy Yandex data must migrate without needing an existing local save.
  const old=storage(), legacy=bytes(151000,99);
  old.map.set('openttdSaveV1', {
    version:1,name:'legacy.sav',mtime:Date.now()+50_000,data:Buffer.from(legacy).toString('base64')
  });
  old.map.set('openttdMobileConfigV1',{version:1,config:'[misc]\nlanguage = english.lng'});
  const fs5=filesystem();
  app=boot(old,fs5);
  await app.restore();
  same(fs5.readFile(dir+'legacy.sav'),legacy);
  assert.equal(fs5.readFile('/home/openttd/openttd.cfg',{encoding:'utf8'}).includes('english.lng'),true);

  // Storage may be absent entirely: no deletion or corruption of local data.
  const off=storage();off.available=false;
  const existing=bytes(230000,42), fs6=filesystem({[dir+'local.sav']:existing});
  app=boot(off,fs6);
  await app.restore();
  await app.save();
  same(fs6.readFile(dir+'local.sav'),existing);
  assert.equal(app.status().available,false);

  console.log('Playgama cloud saves: >120 KB, A/B commits, corruption, legacy migration, offline fallback: PASS');
}
main().catch(e => {console.error(e);process.exitCode=1;});
