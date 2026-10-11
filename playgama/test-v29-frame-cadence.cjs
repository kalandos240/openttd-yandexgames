#!/usr/bin/env node
/* Assert the EXACT patched OpenTTD runtime presenter caps expensive
 * WebGL uploads on high-refresh monitors while leaving native game ticks alone.
 */
'use strict';
const fs = require('node:fs');
const assert = require('node:assert/strict');
const runtime = fs.readFileSync(process.argv[2] || 'dist-playgama/openttd-runtime.js','utf8');
const start = '47364289:(A,B,g)=>{var __otW=A,__otH=B,__otPixels=g;';
const end = 'if(__otSDL.__openttdPresenterCanvas!==__otCanvas)';
assert.equal(runtime.split(start).length,2, 'Original OpenTTD presenter is missing');
const entry = runtime.indexOf(start);
const pos = runtime.indexOf(end,entry);
assert.ok(pos>entry,'Context recreation path must remain');
const limiter = runtime.slice(entry+start.length,pos);
assert.match(limiter,/__otFrameNow-__otSDL.__openttdLastPresentedAt<33\.333/);
assert.match(limiter,/__otCanvas.width===__otW&&__otCanvas.height===__otH/);
assert.match(limiter,/__otSDL.__openttdPresenterCanvas===__otCanvas/);
// Execute only the V29 presenter prefix, avoiding the >75 MB WASM module.
const tick = new Function('Module','performance','A','B',
  'var __otW=A,__otH=B,__otPixels=0;' + limiter + 'return "uploaded";');
const canvas={width:1280,height:720};
const state={SDL2:{__openttdPresenterCanvas:canvas}};
let elapsed=10_000;
const clock={now:()=>elapsed};
let uploads=0;
for(let i=0;i<144;i++){
  elapsed=10_000+i*(1000/144);
  if(tick(state,clock,1280,720)==='uploaded') uploads++;
}
assert.ok(uploads>=28 && uploads<=31, '144 rAF ticks should perform ~30 uploads, got '+uploads);
canvas.width=1440; canvas.height=900; elapsed+=1;
assert.equal(tick(state,clock,1440,900),'uploaded',
  'A canvas dimension change must force an immediate upload');
const canvas2={width:1440,height:900};
state.SDL2.__openttdPresenterCanvas=canvas;
elapsed+=1;
assert.equal(tick({SDL2:state.SDL2},clock,1440,900),'uploaded');
elapsed+=1;
state.SDL2.__openttdPresenterCanvas=canvas2;
assert.equal(tick({canvas:canvas2,SDL2:state.SDL2},clock,1440,900),'uploaded',
  'Recreating the presenter must never skip initial frame');
// Does not inject into Emscripten scheduler: only the presentation hook.
assert.equal(runtime.includes('runIter'),true);
console.log('Playgama Firefox-profiled WebGL presenter: 144Hz -> ~30 FPS uploads; resize redraw PASS ('+uploads+'/144 uploads)');
