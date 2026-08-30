#!/usr/bin/env python3
"""Apply deterministic performance/runtime hardening to verified OpenTTD v14 packages.

This patch deliberately works on already-built packages so the native tutorial,
AI, ranking and viewport feature set stays unchanged. It removes the measured
browser bottlenecks without changing OpenTTD simulation semantics.
"""
from __future__ import annotations

import argparse
from pathlib import Path

PLAYGAMA_BRIDGE_URL = "https://bridge.playgama.com/v1.31.0/playgama-bridge.js"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one occurrence, found {count}")
    return text.replace(old, new, 1)


def patch_renderer(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "__openttdWebGLPresenter" in text:
        return

    start_marker = 'var w=$0;var h=$1;var pixels=$2;if(!Module["SDL2"])Module["SDL2"]={};var SDL2=Module["SDL2"];'
    start = text.find(start_marker)
    end = text.find('},1302158:', start)
    if start < 0 or end < 0:
        raise SystemExit("Could not locate the SDL2 software framebuffer presenter")

    replacement = r'''var w=$0;var h=$1;var pixels=$2;if(!Module["SDL2"])Module["SDL2"]={};var SDL2=Module["SDL2"];var canvas=Module["canvas"];if(SDL2.__openttdPresenterCanvas!==canvas){SDL2.__openttdPresenterCanvas=canvas;SDL2.__openttdWebGLPresenter=null;SDL2.ctx=null;try{var attrs={alpha:false,antialias:false,depth:false,stencil:false,preserveDrawingBuffer:false,premultipliedAlpha:false};var gl=canvas.getContext("webgl",attrs)||canvas.getContext("experimental-webgl",attrs);if(gl){var compile=function(type,source){var shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(shader)||"shader compile failed");return shader};var vs=compile(gl.VERTEX_SHADER,"attribute vec2 a;varying vec2 v;void main(){gl_Position=vec4(a,0.0,1.0);v=vec2((a.x+1.0)*0.5,(1.0-a.y)*0.5);}");var fs=compile(gl.FRAGMENT_SHADER,"precision mediump float;varying vec2 v;uniform sampler2D t;void main(){vec3 c=texture2D(t,v).rgb;gl_FragColor=vec4(c,1.0);}");var program=gl.createProgram();gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program)||"program link failed");gl.useProgram(program);var buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW);var loc=gl.getAttribLocation(program,"a");gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);var texture=gl.createTexture();gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,texture);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.uniform1i(gl.getUniformLocation(program,"t"),0);gl.pixelStorei(gl.UNPACK_ALIGNMENT,4);SDL2.__openttdWebGLPresenter={gl:gl,program:program,buffer:buffer,texture:texture,w:0,h:0};}}catch(e){console.warn("[OpenTTD perf] WebGL framebuffer presenter unavailable; using Canvas2D fallback.",e)}if(!SDL2.__openttdWebGLPresenter){SDL2.ctx=canvas.getContext("2d",{alpha:false})||Module["createContext"](canvas,false,true);}}var presenter=SDL2.__openttdWebGLPresenter;if(presenter){var gl=presenter.gl;gl.viewport(0,0,canvas.width,canvas.height);gl.useProgram(presenter.program);gl.bindBuffer(gl.ARRAY_BUFFER,presenter.buffer);gl.bindTexture(gl.TEXTURE_2D,presenter.texture);var src8=HEAPU8.subarray(pixels,pixels+w*h*4);if(presenter.w!==w||presenter.h!==h){gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,w,h,0,gl.RGBA,gl.UNSIGNED_BYTE,src8);presenter.w=w;presenter.h=h}else{gl.texSubImage2D(gl.TEXTURE_2D,0,0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,src8)}gl.drawArrays(gl.TRIANGLE_STRIP,0,4);return}if(SDL2.w!==w||SDL2.h!==h||SDL2.imageCtx!==SDL2.ctx){SDL2.image=SDL2.ctx.createImageData(w,h);SDL2.w=w;SDL2.h=h;SDL2.imageCtx=SDL2.ctx}var data=SDL2.image.data;var src=pixels>>2;var dst=0;var num;if(typeof CanvasPixelArray!=="undefined"&&data instanceof CanvasPixelArray){num=data.length;while(dst<num){var val=HEAP32[src];data[dst]=val&255;data[dst+1]=val>>8&255;data[dst+2]=val>>16&255;data[dst+3]=255;src++;dst+=4}}else{if(SDL2.data32Data!==data){SDL2.data32=new Int32Array(data.buffer);SDL2.data8=new Uint8Array(data.buffer);SDL2.data32Data=data}var data32=SDL2.data32;num=data32.length;data32.set(HEAP32.subarray(src,src+num));var data8=SDL2.data8;var i=3;var j=i+4*num;if(num%8==0){while(i<j){data8[i]=255;i=i+4|0;data8[i]=255;i=i+4|0;data8[i]=255;i=i+4|0;data8[i]=255;i=i+4|0;data8[i]=255;i=i+4|0;data8[i]=255;i=i+4|0;data8[i]=255;i=i+4|0;data8[i]=255;i=i+4|0}}else{while(i<j){data8[i]=255;i=i+4|0}}}SDL2.ctx.putImageData(SDL2.image,0,0)'''

    text = text[:start] + replacement + text[end:]
    if "__openttdWebGLPresenter" not in text or "texSubImage2D" not in text:
        raise SystemExit("WebGL presenter patch failed")
    path.write_text(text, encoding="utf-8")


def patch_ranking(path: Path, global_ranking: bool) -> None:
    text = path.read_text(encoding="utf-8")
    if global_ranking:
        text = text.replace(
            "const MAX_SCORE = Number.MAX_SAFE_INTEGER; // 2^53 - 1; exact JS integer range.",
            "const MAX_SCORE = 1000; // OpenTTD company performance rating range.",
        )
        text = text.replace(
            "const MAX_SCORE = Number.MAX_SAFE_INTEGER;",
            "const MAX_SCORE = 1000; // OpenTTD company performance rating range.",
        )

    if "const runtimeFsReady = () =>" not in text:
        anchor = "  const writeSnapshot = () => {\n"
        helper = """  const runtimeFsReady = () => {\n    try {\n      return typeof Module !== 'undefined' && Module.calledRun === true &&\n        typeof HEAP8 !== 'undefined' && HEAP8 && HEAP8.buffer &&\n        typeof FS !== 'undefined' && typeof FS.writeFile === 'function';\n    } catch (_) {\n      return false;\n    }\n  };\n\n"""
        text = replace_once(text, anchor, helper + anchor, "ranking runtime-ready helper")

    old = "    try {\n      if (typeof FS === 'undefined' || typeof FS.writeFile !== 'function') return false;\n"
    if old in text:
        text = replace_once(text, old, "    if (!runtimeFsReady()) return false;\n    try {\n", "ranking FS guard")

    if "let publishTimer = 0;" not in text:
        anchor = "  let lastWrite = '';\n" if "  let lastWrite = '';\n" in text else "  let lastSnapshot = '';\n"
        text = replace_once(text, anchor, anchor + "  let publishTimer = 0;\n", "ranking timer state")

    old_publish = "  const publishSoon = () => {\n    if (!writeSnapshot()) setTimeout(writeSnapshot, 100);\n  };\n"
    old_publish_alt = "  const publishSoon = () => {\n    if (writeSnapshot()) return;\n    setTimeout(writeSnapshot, 100);\n  };\n"
    new_publish = """  const publishSoon = () => {\n    if (writeSnapshot() || publishTimer) return;\n    const retry = () => {\n      publishTimer = 0;\n      if (!writeSnapshot()) publishTimer = setTimeout(retry, 250);\n    };\n    publishTimer = setTimeout(retry, 250);\n  };\n"""
    if old_publish in text:
        text = text.replace(old_publish, new_publish, 1)
    elif old_publish_alt in text:
        text = text.replace(old_publish_alt, new_publish, 1)
    elif "const retry = () =>" not in text:
        raise SystemExit(f"Unknown ranking publishSoon form: {path}")

    if global_ranking and "const MAX_SCORE = 1000" not in text:
        raise SystemExit(f"Global ranking score bound missing after patch: {path}")
    if "Module.calledRun === true" not in text or "typeof HEAP8 !== 'undefined'" not in text:
        raise SystemExit(f"Ranking runtime-ready guard missing: {path}")
    path.write_text(text, encoding="utf-8")


def patch_yandex_cloud(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "__openttdCloudDedupV2" in text:
        return

    anchor = "  let lastCloudWriteAt = 0;\n"
    text = replace_once(
        text,
        anchor,
        anchor + "  let lastCloudConfigText = null;\n  let lastCloudSaveSignature = null;\n  const __openttdCloudDedupV2 = true;\n",
        "Yandex cloud cache state",
    )

    start = text.find("  function buildCloudPayload(FS, personalDir) {")
    end = text.find("\n  function restoreCloudConfig", start)
    if start < 0 or end < 0:
        raise SystemExit("Could not locate Yandex cloud payload builder")

    builder = r'''  function cloudSaveSignature(save) {
    if (!save) return '';
    const name = save.path.split('/').pop();
    const mtime = statTime(save.stat);
    const size = Number(save.stat && save.stat.size) || 0;
    return `${name}\t${mtime}\t${size}`;
  }

  function decodedBase64Length(value) {
    const s = String(value || '');
    if (!s) return 0;
    let padding = 0;
    if (s.endsWith('==')) padding = 2;
    else if (s.endsWith('=')) padding = 1;
    return Math.max(0, Math.floor(s.length * 3 / 4) - padding);
  }

  function buildCloudPayload(FS, personalDir) {
    const payload = {};
    const state = { configText: null, saveSignature: null, saveIncluded: false };
    const configText = readConfig(FS, personalDir);
    state.configText = configText;
    if (configText !== lastCloudConfigText) {
      payload[CLOUD_CONFIG_KEY] = {
        version: CLOUD_VERSION,
        updatedAt: Date.now(),
        config: configText,
      };
    }

    const save = newestSave(FS, personalDir);
    const signature = cloudSaveSignature(save);
    state.saveSignature = signature;
    if (save && signature !== lastCloudSaveSignature) {
      try {
        const bytes = FS.readFile(save.path);
        if (bytes.length <= MAX_RAW_SAVE) {
          const cloudSave = {
            version: CLOUD_VERSION,
            updatedAt: Date.now(),
            name: save.path.split('/').pop(),
            mtime: statTime(save.stat) || Date.now(),
            data: bytesToBase64(bytes),
          };
          const saveOnlyPayload = {};
          saveOnlyPayload[CLOUD_SAVE_KEY] = cloudSave;
          if (JSON.stringify(saveOnlyPayload).length <= MAX_CLOUD_JSON) {
            payload[CLOUD_SAVE_KEY] = cloudSave;
            state.saveIncluded = true;
          }
        }
      } catch (error) {
        console.warn('OpenTTD cloud: could not read latest save', error);
      }
    }
    return { payload, state };
  }
'''
    text = text[:start] + builder + text[end:]

    restore_anchor = "      const data = await player.getData([CLOUD_CONFIG_KEY, CLOUD_SAVE_KEY]);\n"
    restore_seed = restore_anchor + r'''      const remoteConfig = data && data[CLOUD_CONFIG_KEY];
      const remoteSave = data && data[CLOUD_SAVE_KEY];
      if (remoteConfig && remoteConfig.version === CLOUD_VERSION && typeof remoteConfig.config === 'string') {
        lastCloudConfigText = remoteConfig.config;
      }
      if (remoteSave && remoteSave.version === CLOUD_VERSION && remoteSave.name && remoteSave.data) {
        lastCloudSaveSignature = `${remoteSave.name}\t${Number(remoteSave.mtime || remoteSave.updatedAt || 0)}\t${decodedBase64Length(remoteSave.data)}`;
      }
'''
    text = replace_once(text, restore_anchor, restore_seed, "Yandex remote-cache seed")

    old_flush = r'''      const payload = buildCloudPayload(FS, personalDir);

      /* If the newest save is too large, CLOUD_SAVE_KEY is intentionally
         omitted so the last valid cloud save is not erased. */
      if (JSON.stringify(payload).length > 195000) delete payload[CLOUD_SAVE_KEY];
      await player.setData(payload, true);
      lastCloudWriteAt = Date.now();'''
    new_flush = r'''      const built = buildCloudPayload(FS, personalDir);
      const payload = built.payload;
      if (JSON.stringify(payload).length > 195000) {
        delete payload[CLOUD_SAVE_KEY];
        built.state.saveIncluded = false;
      }
      if (Object.keys(payload).length) {
        await player.setData(payload, true);
        if (Object.prototype.hasOwnProperty.call(payload, CLOUD_CONFIG_KEY)) lastCloudConfigText = built.state.configText;
        if (built.state.saveIncluded && Object.prototype.hasOwnProperty.call(payload, CLOUD_SAVE_KEY)) {
          lastCloudSaveSignature = built.state.saveSignature;
        }
      }
      lastCloudWriteAt = Date.now();'''
    text = replace_once(text, old_flush, new_flush, "Yandex deduplicated cloud flush")

    if "__openttdCloudDedupV2" not in text or "Object.keys(payload)" not in text:
        raise SystemExit("Yandex cloud dedup patch failed")
    path.write_text(text, encoding="utf-8")


def patch_playgama(dist: Path) -> None:
    index = dist / "index.html"
    html = index.read_text(encoding="utf-8")
    stable = '<script src="https://bridge.playgama.com/v1/stable/playgama-bridge.js"></script>'
    loader_tag = '<script src="platform-bridge-loader.js"></script>'
    if stable in html:
        html = html.replace(stable, loader_tag, 1)
    elif loader_tag not in html:
        raise SystemExit("Playgama parser-active Bridge tag was not found")
    index.write_text(html, encoding="utf-8")

    loader = f'''/* Optional non-blocking Playgama Bridge loader. OpenTTD core is fully local. */
(() => {{
  'use strict';
  window.__openttdPlatformStartupIndependent = true;
  if (window.playgamaBridgeScriptReady) return;
  if (location.protocol === 'file:') {{
    window.__openttdDirectFileLaunch = true;
    window.playgamaBridgeScriptReady = Promise.resolve(null);
    return;
  }}
  window.playgamaBridgeScriptReady = new Promise((resolve) => {{
    const script = document.createElement('script');
    script.src = '{PLAYGAMA_BRIDGE_URL}';
    script.async = true;
    script.crossOrigin = 'anonymous';
    let done = false;
    const finish = (value) => {{ if (done) return; done = true; clearTimeout(timer); resolve(value); }};
    script.onload = () => finish(window.bridge || null);
    script.onerror = () => {{ console.warn('[Playgama/OpenTTD] Optional Bridge failed to load; the game remains available.'); finish(null); }};
    const timer = setTimeout(() => {{ console.warn('[Playgama/OpenTTD] Optional Bridge timed out; game startup is not blocked.'); finish(null); }}, 5000);
    document.head.appendChild(script);
  }});
}})();
'''
    (dist / "platform-bridge-loader.js").write_text(loader, encoding="utf-8")

    adapter = dist / "playgama-yandex-compat.js"
    text = adapter.read_text(encoding="utf-8")
    anchor = "  const initializeBridge = async () => {\n    if (!window.bridge || typeof window.bridge.initialize !== 'function') {\n"
    if "await window.playgamaBridgeScriptReady" not in text:
        text = replace_once(
            text,
            anchor,
            "  const initializeBridge = async () => {\n    if (window.playgamaBridgeScriptReady) {\n      try { await window.playgamaBridgeScriptReady; } catch (_) {}\n    }\n    if (!window.bridge || typeof window.bridge.initialize !== 'function') {\n",
            "Playgama async Bridge gate",
        )
    adapter.write_text(text, encoding="utf-8")

    runtime = dist / "openttd-runtime.js"
    text = runtime.read_text(encoding="utf-8")
    old = 'if(window.yandexGamesSDKReady){Promise.race([window.yandexGamesSDKReady,new Promise(resolve=>setTimeout(()=>resolve(null),3e3))]).then(finish_startup,finish_startup)}else{finish_startup()}'
    new = 'if(window.__openttdPlatformStartupIndependent===true){finish_startup()}else if(window.yandexGamesSDKReady){Promise.race([window.yandexGamesSDKReady,new Promise(resolve=>setTimeout(()=>resolve(null),3e3))]).then(finish_startup,finish_startup)}else{finish_startup()}'
    if old in text:
        text = text.replace(old, new, 1)
    elif "__openttdPlatformStartupIndependent" not in text:
        raise SystemExit("Playgama startup SDK gate was not found in runtime")
    runtime.write_text(text, encoding="utf-8")


def validate(dist: Path, platform: str) -> None:
    runtime = (dist / "openttd-runtime.js").read_text(encoding="utf-8")
    local = (dist / "openttd-ranking-core.js").read_text(encoding="utf-8")
    global_ranking = (dist / "openttd-global-ranking.js").read_text(encoding="utf-8")
    if "__openttdWebGLPresenter" not in runtime:
        raise SystemExit("WebGL framebuffer presenter missing")
    for text in (local, global_ranking):
        if "Module.calledRun === true" not in text or "typeof HEAP8 !== 'undefined'" not in text:
            raise SystemExit("Ranking runtime-ready guard missing")
    if "const MAX_SCORE = 1000" not in global_ranking:
        raise SystemExit("Global ranking score range is not bounded to 1000")
    if platform == "yandex":
        bridge = (dist / "yandex-bridge.js").read_text(encoding="utf-8")
        if "__openttdCloudDedupV2" not in bridge:
            raise SystemExit("Yandex cloud dedup marker missing")
    else:
        html = (dist / "index.html").read_text(encoding="utf-8")
        if "https://bridge.playgama.com" in html:
            raise SystemExit("Parser-active external Playgama Bridge remains in index.html")
        loader = (dist / "platform-bridge-loader.js").read_text(encoding="utf-8")
        if PLAYGAMA_BRIDGE_URL not in loader or "script.async = true" not in loader:
            raise SystemExit("Pinned non-blocking Playgama Bridge loader missing")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dist", type=Path)
    parser.add_argument("--platform", choices=("yandex", "playgama"), required=True)
    args = parser.parse_args()
    dist = args.dist.resolve()

    patch_renderer(dist / "openttd-runtime.js")
    patch_ranking(dist / "openttd-ranking-core.js", False)
    patch_ranking(dist / "openttd-global-ranking.js", True)
    if args.platform == "yandex":
        patch_yandex_cloud(dist / "yandex-bridge.js")
    else:
        patch_playgama(dist)
    validate(dist, args.platform)
    print(f"v14 performance hardening applied: {args.platform}")


if __name__ == "__main__":
    main()
