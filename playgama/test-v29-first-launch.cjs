#!/usr/bin/env node
'use strict';
/* Cold-visit regression: Playgama CDN must not block HTML parsing or OpenTTD
 * startup; late SDK arrival must still send GAME_READY. Cloud metadata must
 * be fetched in one Bridge request rather than three sequential requests. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const loader=fs.readFileSync('playgama/playgama-bridge-loader.js','utf8');
const adapter=fs.readFileSync('playgama/playgama-yandex-compat.js','utf8');
const cloud=fs.readFileSync('playgama/openttd-playgama-cloud-saves.js','utf8');

function makeEnv() {
  let sdkScript=null, messages=[],getCalls=[];
  const doc={
    hidden:false,
    head:{appendChild(el){sdkScript=el;}},
    createElement(tag){assert.equal(tag,'script');return {tag,async:false};},
    documentElement:{dataset:{}},
    querySelectorAll(){return [];},
    addEventListener(){}
  };
  const ctx={
    document:doc,console,Promise,Uint8Array,btoa,atob,
    Date,setTimeout,clearTimeout,navigator:{language:'en-US'},
    Module:{calledRun:true,postRun:[]}
  };
  ctx.window=ctx;
  const bridge={
    version:'2.3.1',engine:null,
    initialize:async()=>{},
    STORAGE_TYPE:{PLATFORM_INTERNAL:'platform_internal'},
    EVENT_NAME:{PAUSE_STATE_CHANGED:'pause_state_changed',AUDIO_STATE_CHANGED:'audio_state_changed'},
    platform:{language:'ru',id:'playgama_sandbox',on(){},sendMessage:async message=>messages.push(message)},
    storage:{
      isAvailable(){return true;},isSupported(){return true;},
      async get(keys){getCalls.push(Array.from(keys));return keys.map(()=>null)},
      async set(){}
    },
    player:{id:'example'},
    advertisement:{isInterstitialSupported:false,setMinimumDelayBetweenInterstitial(){}}
  };
  return {ctx,doc,bridge,script:()=>sdkScript,messages,getCalls};
}
async function settle() {for(let i=0;i<10;i++)await Promise.resolve();}
async function main() {
  const env=makeEnv();
  vm.runInNewContext(loader,env.ctx,{filename:'playgama-bridge-loader.js'});
  assert.equal(env.ctx.__openttdPlatformStartupIndependent,true);
  assert.ok(env.script(),'A nonblocking SDK script should be appended');
  assert.equal(env.script().async,true,'SDK script must be async');
  assert.match(env.script().src,/^https:\/\/bridge\.playgama\.com\/v2\/stable\//);
  vm.runInNewContext(adapter,env.ctx,{filename:'playgama-yandex-compat.js'});

  let settled=false;
  env.ctx.yandexGamesSDKReady.then(()=>{settled=true;});
  await settle();
  assert.equal(settled,false,'SDK must not pretend to be ready while CDN is stalled');

  // OpenTTD calledRun already true when the SDK eventually loads.
  // Game-ready MUST be emitted even though native startup didn't wait.
  env.ctx.bridge=env.bridge;
  env.script().onload();
  const sdk=await env.ctx.yandexGamesSDKReady;
  assert.ok(sdk);
  assert.deepEqual(env.messages,['game_ready'],'late SDK should deliver game_ready exactly once');
  assert.equal(env.bridge.engine,'javascript');

  const FS={
    mkdir(){},readdir(){return ['.','..']},
    stat(){throw new Error('not found')},
    isDir(){return false},isFile(){return false},
    readFile(){throw new Error('not found')},
    writeFile(){}, syncfs(populate,callback){callback(null)}
  };
  vm.runInNewContext(cloud,env.ctx,{filename:'openttd-playgama-cloud-saves.js'});
  await env.ctx.yandexRestoreOpenTTDCloud(FS,'/home/openttd');
  assert.equal(env.getCalls.length,1,'cold start must read cloud keys in a single network request');
  assert.equal(env.getCalls[0].length,6,'read config + 2 cloud metas + legacy save together');
  assert.equal(env.ctx.__openttdPlaygamaCloudStatus.restored,false);

  const failed=makeEnv();
  vm.runInNewContext(loader,failed.ctx);
  vm.runInNewContext(adapter,failed.ctx);
  failed.script().onerror();
  assert.equal(await failed.ctx.yandexGamesSDKReady,null,
    'failed SDK CDN must not create a blocking unhandled rejection');

  console.log('Playgama first-launch nonblocking SDK, late GAME_READY, cloud batch and CDN error: PASS');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
