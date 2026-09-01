#!/usr/bin/env python3
"""Patch the generated SDL2 software framebuffer presenter to a WebGL fast path.

The locator is deliberately independent of Emscripten numeric entry IDs and of
whether the generated JS uses readable or minified local variable names.

WebGL2 additionally consumes the native OpenTTD dirty rectangle (when present)
and uses UNPACK_ROW_LENGTH / UNPACK_SKIP_* to transfer only changed pixels from
the Wasm heap. WebGL1 and the original Canvas2D presenter stay as fallbacks.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def find_presenter(text: str) -> tuple[int, int, list[str], str, str]:
    """Return body start/end, argument names, original body and entry ID."""
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
    # Keep this as ordinary JS (rather than trying to rewrite the SDL port). It
    # executes in the generated Emscripten scope, where HEAPU8 and Module exist.
    return f'''var __otW={w},__otH={h},__otPixels={pixels};
Module.SDL2||(Module.SDL2={{}});
var __otSDL=Module.SDL2,__otCanvas=Module.canvas;
if(__otSDL.__openttdPresenterCanvas!==__otCanvas){{
  __otSDL.__openttdPresenterCanvas=__otCanvas;
  __otSDL.__openttdWebGLPresenter=null;
  try{{
    var __otAttrs={{alpha:false,antialias:false,depth:false,stencil:false,preserveDrawingBuffer:false,premultipliedAlpha:false}},
        __otGl=__otCanvas.getContext("webgl2",__otAttrs),__otIs2=!!__otGl;
    if(!__otGl)__otGl=__otCanvas.getContext("webgl",__otAttrs)||__otCanvas.getContext("experimental-webgl",__otAttrs);
    if(__otGl){{
      var __otCompile=function(type,source){{
        var shader=__otGl.createShader(type);
        __otGl.shaderSource(shader,source);
        __otGl.compileShader(shader);
        if(!__otGl.getShaderParameter(shader,__otGl.COMPILE_STATUS))throw new Error(__otGl.getShaderInfoLog(shader)||"shader compile failed");
        return shader;
      }},
      __otVsSource=__otIs2?"#version 300 es\\nin vec2 a;out vec2 v;void main(){{gl_Position=vec4(a,0.0,1.0);v=vec2((a.x+1.0)*0.5,(1.0-a.y)*0.5);}}":"attribute vec2 a;varying vec2 v;void main(){{gl_Position=vec4(a,0.0,1.0);v=vec2((a.x+1.0)*0.5,(1.0-a.y)*0.5);}}",
      __otFsSource=__otIs2?"#version 300 es\\nprecision mediump float;in vec2 v;uniform sampler2D t;out vec4 outColor;void main(){{vec3 c=texture(t,v).rgb;outColor=vec4(c,1.0);}}":"precision mediump float;varying vec2 v;uniform sampler2D t;void main(){{vec3 c=texture2D(t,v).rgb;gl_FragColor=vec4(c,1.0);}}",
      __otVs=__otCompile(__otGl.VERTEX_SHADER,__otVsSource),__otFs=__otCompile(__otGl.FRAGMENT_SHADER,__otFsSource),__otProgram=__otGl.createProgram();
      __otGl.attachShader(__otProgram,__otVs);__otGl.attachShader(__otProgram,__otFs);__otGl.linkProgram(__otProgram);
      if(!__otGl.getProgramParameter(__otProgram,__otGl.LINK_STATUS))throw new Error(__otGl.getProgramInfoLog(__otProgram)||"program link failed");
      __otGl.useProgram(__otProgram);
      var __otBuffer=__otGl.createBuffer();
      __otGl.bindBuffer(__otGl.ARRAY_BUFFER,__otBuffer);
      __otGl.bufferData(__otGl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),__otGl.STATIC_DRAW);
      var __otLoc=__otGl.getAttribLocation(__otProgram,"a");
      __otGl.enableVertexAttribArray(__otLoc);__otGl.vertexAttribPointer(__otLoc,2,__otGl.FLOAT,false,0,0);
      var __otTexture=__otGl.createTexture();
      __otGl.activeTexture(__otGl.TEXTURE0);__otGl.bindTexture(__otGl.TEXTURE_2D,__otTexture);
      __otGl.texParameteri(__otGl.TEXTURE_2D,__otGl.TEXTURE_MIN_FILTER,__otGl.NEAREST);
      __otGl.texParameteri(__otGl.TEXTURE_2D,__otGl.TEXTURE_MAG_FILTER,__otGl.NEAREST);
      __otGl.texParameteri(__otGl.TEXTURE_2D,__otGl.TEXTURE_WRAP_S,__otGl.CLAMP_TO_EDGE);
      __otGl.texParameteri(__otGl.TEXTURE_2D,__otGl.TEXTURE_WRAP_T,__otGl.CLAMP_TO_EDGE);
      __otGl.uniform1i(__otGl.getUniformLocation(__otProgram,"t"),0);
      __otGl.pixelStorei(__otGl.UNPACK_ALIGNMENT,4);
      __otSDL.__openttdWebGLPresenter={{gl:__otGl,program:__otProgram,buffer:__otBuffer,texture:__otTexture,isWebGL2:__otIs2,w:0,h:0,cw:0,ch:0}};
      __otSDL.__openttdWebGL2ZeroCopy=__otIs2;
      __otSDL.__openttdFramebufferFullUploads=0;
      __otSDL.__openttdFramebufferPartialUploads=0;
      __otSDL.__openttdFramebufferUploadedPixels=0;
    }}
  }}catch(e){{console.warn("[OpenTTD perf] WebGL framebuffer presenter unavailable; using Canvas2D fallback.",e)}}
}}
var __otPresenter=__otSDL.__openttdWebGLPresenter;
if(__otPresenter){{
  var __otGl=__otPresenter.gl;
  if(__otPresenter.cw!==__otCanvas.width||__otPresenter.ch!==__otCanvas.height){{
    __otGl.viewport(0,0,__otCanvas.width,__otCanvas.height);
    __otPresenter.cw=__otCanvas.width;__otPresenter.ch=__otCanvas.height;
  }}
  __otGl.useProgram(__otPresenter.program);
  __otGl.bindBuffer(__otGl.ARRAY_BUFFER,__otPresenter.buffer);
  __otGl.bindTexture(__otGl.TEXTURE_2D,__otPresenter.texture);

  var __otResize=__otPresenter.w!==__otW||__otPresenter.h!==__otH,
      __otX=__otSDL.__openttdDirtyX|0,__otY=__otSDL.__openttdDirtyY|0,
      __otDW=__otSDL.__openttdDirtyW|0,__otDH=__otSDL.__openttdDirtyH|0,
      __otHasDirty=__otSDL.__openttdDirtyValid===1;
  __otSDL.__openttdDirtyValid=0;
  var __otDirtyArea=__otDW*__otDH,__otFrameArea=__otW*__otH,
      __otPartial=__otPresenter.isWebGL2&&!__otResize&&__otHasDirty&&
        __otX>=0&&__otY>=0&&__otDW>0&&__otDH>0&&
        __otX+__otDW<=__otW&&__otY+__otDH<=__otH&&
        __otDirtyArea*10<__otFrameArea*9;

  if(__otResize){{
    if(__otPresenter.isWebGL2){{
      __otGl.texImage2D(__otGl.TEXTURE_2D,0,__otGl.RGBA,__otW,__otH,0,__otGl.RGBA,__otGl.UNSIGNED_BYTE,null);
      __otGl.texSubImage2D(__otGl.TEXTURE_2D,0,0,0,__otW,__otH,__otGl.RGBA,__otGl.UNSIGNED_BYTE,HEAPU8,__otPixels);
    }}else{{
      var __otSrc=HEAPU8.subarray(__otPixels,__otPixels+__otW*__otH*4);
      __otGl.texImage2D(__otGl.TEXTURE_2D,0,__otGl.RGBA,__otW,__otH,0,__otGl.RGBA,__otGl.UNSIGNED_BYTE,__otSrc);
    }}
    __otPresenter.w=__otW;__otPresenter.h=__otH;
    __otSDL.__openttdFramebufferFullUploads++;
    __otSDL.__openttdFramebufferUploadedPixels+=__otFrameArea;
  }}else if(__otPartial){{
    /* WebGL2 can address a rectangular view inside HEAPU8 without creating a
       temporary typed array or copying rows in JavaScript. */
    __otGl.pixelStorei(__otGl.UNPACK_ROW_LENGTH,__otW);
    __otGl.pixelStorei(__otGl.UNPACK_SKIP_PIXELS,__otX);
    __otGl.pixelStorei(__otGl.UNPACK_SKIP_ROWS,__otY);
    __otGl.texSubImage2D(__otGl.TEXTURE_2D,0,__otX,__otY,__otDW,__otDH,__otGl.RGBA,__otGl.UNSIGNED_BYTE,HEAPU8,__otPixels);
    __otGl.pixelStorei(__otGl.UNPACK_ROW_LENGTH,0);
    __otGl.pixelStorei(__otGl.UNPACK_SKIP_PIXELS,0);
    __otGl.pixelStorei(__otGl.UNPACK_SKIP_ROWS,0);
    __otSDL.__openttdFramebufferPartialUploads++;
    __otSDL.__openttdFramebufferUploadedPixels+=__otDirtyArea;
    __otSDL.__openttdFramebufferLastDirtyArea=__otDirtyArea;
  }}else{{
    if(__otPresenter.isWebGL2){{
      __otGl.texSubImage2D(__otGl.TEXTURE_2D,0,0,0,__otW,__otH,__otGl.RGBA,__otGl.UNSIGNED_BYTE,HEAPU8,__otPixels);
    }}else{{
      var __otSrc2=HEAPU8.subarray(__otPixels,__otPixels+__otW*__otH*4);
      __otGl.texSubImage2D(__otGl.TEXTURE_2D,0,0,0,__otW,__otH,__otGl.RGBA,__otGl.UNSIGNED_BYTE,__otSrc2);
    }}
    __otSDL.__openttdFramebufferFullUploads++;
    __otSDL.__openttdFramebufferUploadedPixels+=__otFrameArea;
  }}
  __otGl.drawArrays(__otGl.TRIANGLE_STRIP,0,4);
  return;
}}
'''


def patch_renderer(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "__openttdFramebufferPartialUploads" in text:
        print("Dirty-rect WebGL presenter already present")
        return
    if "__openttdWebGLPresenter" in text:
        raise SystemExit("Older WebGL presenter patch is already present; expected a clean native runtime")

    body_start, body_end, args, original, entry_id = find_presenter(text)
    fast = webgl_fast_path(args[0], args[1], args[2])
    text = text[:body_start] + fast + original + text[body_end:]
    required = (
        "__openttdWebGLPresenter",
        "__openttdWebGL2ZeroCopy",
        "__openttdFramebufferPartialUploads",
        'getContext("webgl2"',
        "UNPACK_ROW_LENGTH",
        "UNPACK_SKIP_PIXELS",
        "UNPACK_SKIP_ROWS",
        "texSubImage2D",
        "Canvas2D fallback",
    )
    if any(marker not in text for marker in required):
        raise SystemExit("Dirty-rect WebGL presenter patch failed")
    path.write_text(text, encoding="utf-8")
    print(f"WebGL2 dirty-rect zero-copy presenter patched in Emscripten entry {entry_id}; WebGL1/Canvas2D fallbacks preserved")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("runtime", type=Path)
    args = parser.parse_args()
    patch_renderer(args.runtime.resolve())


if __name__ == "__main__":
    main()
