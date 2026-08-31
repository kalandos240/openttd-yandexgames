#!/usr/bin/env python3
"""Proven v5 WebGL1 dirty-rect presenter for clean A/B testing.

This file is intentionally kept separate from the experimental WebGL2 presenter.
It is the renderer implementation used by the stable 6a5f094 runtime path.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def find_presenter(text: str) -> tuple[int, int, list[str], str, str]:
    candidate = None
    for hit in re.finditer(r"\.putImageData\(", text):
        pos = hit.start()
        nearby = text[max(0, pos - 3000):pos]
        if "Module.SDL2" in nearby and "createImageData" in nearby:
            candidate = pos
            break
    if candidate is None:
        raise SystemExit("Could not locate SDL2 software framebuffer presenter")
    window_start = max(0, candidate - 10000)
    entries = list(re.finditer(r"(\d+):\(([^)]*)\)=>\{", text[window_start:candidate]))
    if not entries:
        raise SystemExit("Could not locate Emscripten entry containing SDL2 presenter")
    entry = entries[-1]
    entry_id = entry.group(1)
    args = [part.strip() for part in entry.group(2).split(",") if part.strip()]
    if len(args) != 3:
        raise SystemExit(f"Unexpected SDL2 presenter signature in entry {entry_id}: {args}")
    body_start = window_start + entry.end()
    boundary = re.search(r"\},\d+:", text[candidate:])
    if boundary is None:
        raise SystemExit("Could not locate SDL2 presenter end boundary")
    body_end = candidate + boundary.start()
    original = text[body_start:body_end]
    if "Module.SDL2" not in original or ".putImageData(" not in original or "createImageData" not in original:
        raise SystemExit(f"Resolved wrong Emscripten body for SDL2 presenter entry {entry_id}")
    if not 400 <= len(original) <= 10000:
        raise SystemExit(f"Unexpected SDL2 presenter body size in entry {entry_id}: {len(original)}")
    return body_start, body_end, args, original, entry_id


def webgl_fast_path(w: str, h: str, pixels: str) -> str:
    return f'''var __otW={w},__otH={h},__otPixels={pixels};Module.SDL2||(Module.SDL2={{}});var __otSDL=Module.SDL2,__otCanvas=Module.canvas;if(__otSDL.__openttdPresenterCanvas!==__otCanvas){{__otSDL.__openttdPresenterCanvas=__otCanvas;__otSDL.__openttdWebGLPresenter=null;try{{var __otAttrs={{alpha:false,antialias:false,depth:false,stencil:false,preserveDrawingBuffer:false,premultipliedAlpha:false}},__otGl=__otCanvas.getContext("webgl",__otAttrs)||__otCanvas.getContext("experimental-webgl",__otAttrs);if(__otGl){{var __otCompile=function(type,source){{var shader=__otGl.createShader(type);__otGl.shaderSource(shader,source);__otGl.compileShader(shader);if(!__otGl.getShaderParameter(shader,__otGl.COMPILE_STATUS))throw new Error(__otGl.getShaderInfoLog(shader)||"shader compile failed");return shader}},__otVs=__otCompile(__otGl.VERTEX_SHADER,"attribute vec2 a;varying vec2 v;void main(){{gl_Position=vec4(a,0.0,1.0);v=vec2((a.x+1.0)*0.5,(1.0-a.y)*0.5);}}"),__otFs=__otCompile(__otGl.FRAGMENT_SHADER,"precision mediump float;varying vec2 v;uniform sampler2D t;void main(){{vec3 c=texture2D(t,v).rgb;gl_FragColor=vec4(c,1.0);}}"),__otProgram=__otGl.createProgram();__otGl.attachShader(__otProgram,__otVs);__otGl.attachShader(__otProgram,__otFs);__otGl.linkProgram(__otProgram);if(!__otGl.getProgramParameter(__otProgram,__otGl.LINK_STATUS))throw new Error(__otGl.getProgramInfoLog(__otProgram)||"program link failed");__otGl.useProgram(__otProgram);var __otBuffer=__otGl.createBuffer();__otGl.bindBuffer(__otGl.ARRAY_BUFFER,__otBuffer);__otGl.bufferData(__otGl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),__otGl.STATIC_DRAW);var __otLoc=__otGl.getAttribLocation(__otProgram,"a");__otGl.enableVertexAttribArray(__otLoc);__otGl.vertexAttribPointer(__otLoc,2,__otGl.FLOAT,false,0,0);var __otTexture=__otGl.createTexture();__otGl.activeTexture(__otGl.TEXTURE0);__otGl.bindTexture(__otGl.TEXTURE_2D,__otTexture);__otGl.texParameteri(__otGl.TEXTURE_2D,__otGl.TEXTURE_MIN_FILTER,__otGl.NEAREST);__otGl.texParameteri(__otGl.TEXTURE_2D,__otGl.TEXTURE_MAG_FILTER,__otGl.NEAREST);__otGl.texParameteri(__otGl.TEXTURE_2D,__otGl.TEXTURE_WRAP_S,__otGl.CLAMP_TO_EDGE);__otGl.texParameteri(__otGl.TEXTURE_2D,__otGl.TEXTURE_WRAP_T,__otGl.CLAMP_TO_EDGE);__otGl.uniform1i(__otGl.getUniformLocation(__otProgram,"t"),0);__otGl.pixelStorei(__otGl.UNPACK_ALIGNMENT,4);__otSDL.__openttdWebGLPresenter={{gl:__otGl,program:__otProgram,buffer:__otBuffer,texture:__otTexture,w:0,h:0,scratch:null}};Module.__openttdUploadStats={{fullUploads:0,partialUploads:0,bytesUploaded:0,lastRect:null}};}}}}catch(e){{console.warn("[OpenTTD perf] WebGL framebuffer presenter unavailable; using Canvas2D fallback.",e)}}}}var __otPresenter=__otSDL.__openttdWebGLPresenter;if(__otPresenter){{var __otGl=__otPresenter.gl;__otGl.viewport(0,0,__otCanvas.width,__otCanvas.height);__otGl.useProgram(__otPresenter.program);__otGl.bindBuffer(__otGl.ARRAY_BUFFER,__otPresenter.buffer);__otGl.bindTexture(__otGl.TEXTURE_2D,__otPresenter.texture);var __otStats=Module.__openttdUploadStats||(Module.__openttdUploadStats={{fullUploads:0,partialUploads:0,bytesUploaded:0,lastRect:null}}),__otFullBytes=__otW*__otH*4;if(__otPresenter.w!==__otW||__otPresenter.h!==__otH){{var __otSrc=HEAPU8.subarray(__otPixels,__otPixels+__otFullBytes);__otGl.texImage2D(__otGl.TEXTURE_2D,0,__otGl.RGBA,__otW,__otH,0,__otGl.RGBA,__otGl.UNSIGNED_BYTE,__otSrc);__otPresenter.w=__otW;__otPresenter.h=__otH;__otStats.fullUploads++;__otStats.bytesUploaded+=__otFullBytes;__otStats.lastRect=[0,0,__otW,__otH]}}else{{var __otR=Module.__openttdDirtyRect,__otX=0,__otY=0,__otDW=__otW,__otDH=__otH,__otPartial=false;if(__otR&&__otR.length===4){{var __otRX=__otR[0]|0,__otRY=__otR[1]|0,__otRW=__otR[2]|0,__otRH=__otR[3]|0;if(__otRX>=0&&__otRY>=0&&__otRW>0&&__otRH>0&&__otRX+__otRW<=__otW&&__otRY+__otRH<=__otH&&__otRW*__otRH<__otW*__otH*.7){{__otX=__otRX;__otY=__otRY;__otDW=__otRW;__otDH=__otRH;__otPartial=true}}}}var __otBytes=__otDW*__otDH*4,__otUpload;if(__otPartial&&__otX===0&&__otDW===__otW){{var __otStart=__otPixels+__otY*__otW*4;__otUpload=HEAPU8.subarray(__otStart,__otStart+__otBytes)}}else if(__otPartial){{if(!__otPresenter.scratch||__otPresenter.scratch.length<__otBytes)__otPresenter.scratch=new Uint8Array(__otBytes);var __otRowBytes=__otDW*4;for(var __otRow=0;__otRow<__otDH;__otRow++){{var __otStart=__otPixels+((__otY+__otRow)*__otW+__otX)*4;__otPresenter.scratch.set(HEAPU8.subarray(__otStart,__otStart+__otRowBytes),__otRow*__otRowBytes)}}__otUpload=__otPresenter.scratch.subarray(0,__otBytes)}}else __otUpload=HEAPU8.subarray(__otPixels,__otPixels+__otFullBytes);__otGl.texSubImage2D(__otGl.TEXTURE_2D,0,__otX,__otY,__otDW,__otDH,__otGl.RGBA,__otGl.UNSIGNED_BYTE,__otUpload);if(__otPartial)__otStats.partialUploads++;else __otStats.fullUploads++;__otStats.bytesUploaded+=__otBytes;__otStats.lastRect=[__otX,__otY,__otDW,__otDH]}}__otGl.drawArrays(__otGl.TRIANGLE_STRIP,0,4);return}}'''


def patch_renderer(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "__openttdUploadStats" in text:
        print("Dirty-rect WebGL presenter already present")
        return
    if "__openttdWebGLPresenter" in text:
        raise SystemExit("Older WebGL presenter already present; apply this patch to a clean generated runtime")
    body_start, body_end, args, original, entry_id = find_presenter(text)
    text = text[:body_start] + webgl_fast_path(args[0], args[1], args[2]) + original + text[body_end:]
    for token in ("__openttdWebGLPresenter", "__openttdDirtyRect", "__openttdUploadStats", "texSubImage2D", "Canvas2D fallback"):
        if token not in text:
            raise SystemExit(f"WebGL presenter patch missing invariant: {token}")
    path.write_text(text, encoding="utf-8")
    print(f"Proven v5 WebGL1 dirty-rect presenter patched in Emscripten entry {entry_id}; Canvas2D fallback preserved")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("runtime", type=Path)
    args = parser.parse_args()
    patch_renderer(args.runtime.resolve())


if __name__ == "__main__":
    main()
