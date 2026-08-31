#!/usr/bin/env python3
"""Patch SDL2's generated software framebuffer presenter to a multi-rect WebGL fast path.

The patch is independent of Emscripten numeric entry IDs. OpenTTD publishes up
to 16 merged dirty rectangles. The presenter prefers WebGL2 so rectangular
sub-images can be uploaded directly from the WASM framebuffer via
UNPACK_ROW_LENGTH / UNPACK_SKIP_* without repacking pixels in JavaScript.
WebGL1 remains supported with the previous contiguous-row / scratch-buffer
fallback, and the stock Canvas2D body remains untouched when WebGL is absent.
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
    js = r'''
var __otW=__OT_W__,__otH=__OT_H__,__otPixels=__OT_PIXELS__;
Module.SDL2||(Module.SDL2={});
var __otSDL=Module.SDL2,__otCanvas=Module.canvas;
if(__otSDL.__openttdPresenterCanvas!==__otCanvas){
  __otSDL.__openttdPresenterCanvas=__otCanvas;
  __otSDL.__openttdWebGLPresenter=null;
  try{
    var __otAttrs={alpha:false,antialias:false,depth:false,stencil:false,preserveDrawingBuffer:false,premultipliedAlpha:false};
    var __otGl=__otCanvas.getContext("webgl2",__otAttrs);
    var __otIsWebGL2=!!__otGl;
    if(!__otGl)__otGl=__otCanvas.getContext("webgl",__otAttrs)||__otCanvas.getContext("experimental-webgl",__otAttrs);
    if(__otGl){
      var __otCompile=function(type,source){
        var shader=__otGl.createShader(type);
        __otGl.shaderSource(shader,source);
        __otGl.compileShader(shader);
        if(!__otGl.getShaderParameter(shader,__otGl.COMPILE_STATUS))throw new Error(__otGl.getShaderInfoLog(shader)||"shader compile failed");
        return shader;
      };
      var __otVsSource=__otIsWebGL2?
        "#version 300 es\nin vec2 a;out vec2 v;void main(){gl_Position=vec4(a,0.0,1.0);v=vec2((a.x+1.0)*0.5,(1.0-a.y)*0.5);}":
        "attribute vec2 a;varying vec2 v;void main(){gl_Position=vec4(a,0.0,1.0);v=vec2((a.x+1.0)*0.5,(1.0-a.y)*0.5);}";
      var __otFsSource=__otIsWebGL2?
        "#version 300 es\nprecision mediump float;in vec2 v;uniform sampler2D t;out vec4 outColor;void main(){vec3 c=texture(t,v).rgb;outColor=vec4(c,1.0);}":
        "precision mediump float;varying vec2 v;uniform sampler2D t;void main(){vec3 c=texture2D(t,v).rgb;gl_FragColor=vec4(c,1.0);}";
      var __otVs=__otCompile(__otGl.VERTEX_SHADER,__otVsSource),__otFs=__otCompile(__otGl.FRAGMENT_SHADER,__otFsSource),__otProgram=__otGl.createProgram();
      __otGl.attachShader(__otProgram,__otVs);
      __otGl.attachShader(__otProgram,__otFs);
      __otGl.linkProgram(__otProgram);
      if(!__otGl.getProgramParameter(__otProgram,__otGl.LINK_STATUS))throw new Error(__otGl.getProgramInfoLog(__otProgram)||"program link failed");
      __otGl.useProgram(__otProgram);
      var __otBuffer=__otGl.createBuffer();
      __otGl.bindBuffer(__otGl.ARRAY_BUFFER,__otBuffer);
      __otGl.bufferData(__otGl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),__otGl.STATIC_DRAW);
      var __otLoc=__otGl.getAttribLocation(__otProgram,"a");
      __otGl.enableVertexAttribArray(__otLoc);
      __otGl.vertexAttribPointer(__otLoc,2,__otGl.FLOAT,false,0,0);
      var __otTexture=__otGl.createTexture();
      __otGl.activeTexture(__otGl.TEXTURE0);
      __otGl.bindTexture(__otGl.TEXTURE_2D,__otTexture);
      __otGl.texParameteri(__otGl.TEXTURE_2D,__otGl.TEXTURE_MIN_FILTER,__otGl.NEAREST);
      __otGl.texParameteri(__otGl.TEXTURE_2D,__otGl.TEXTURE_MAG_FILTER,__otGl.NEAREST);
      __otGl.texParameteri(__otGl.TEXTURE_2D,__otGl.TEXTURE_WRAP_S,__otGl.CLAMP_TO_EDGE);
      __otGl.texParameteri(__otGl.TEXTURE_2D,__otGl.TEXTURE_WRAP_T,__otGl.CLAMP_TO_EDGE);
      __otGl.uniform1i(__otGl.getUniformLocation(__otProgram,"t"),0);
      __otGl.pixelStorei(__otGl.UNPACK_ALIGNMENT,4);
      __otSDL.__openttdWebGLPresenter={gl:__otGl,program:__otProgram,buffer:__otBuffer,texture:__otTexture,w:0,h:0,scratch:null,isWebGL2:__otIsWebGL2,rowUploadDisabled:false};
      Module.__openttdUploadStats={fullUploads:0,partialUploads:0,rectUploads:0,zeroCopyRectUploads:0,packedRectUploads:0,bytesUploaded:0,bytesSaved:0,maxDirtyRects:0,multiRectFrames:0,lastRect:null,lastRects:null,webgl2:__otIsWebGL2};
    }
  }catch(e){console.warn("[OpenTTD perf] WebGL framebuffer presenter unavailable; using Canvas2D fallback.",e)}
}
var __otPresenter=__otSDL.__openttdWebGLPresenter;
if(__otPresenter){
  var __otGl=__otPresenter.gl;
  __otGl.viewport(0,0,__otCanvas.width,__otCanvas.height);
  __otGl.useProgram(__otPresenter.program);
  __otGl.bindBuffer(__otGl.ARRAY_BUFFER,__otPresenter.buffer);
  __otGl.bindTexture(__otGl.TEXTURE_2D,__otPresenter.texture);
  var __otStats=Module.__openttdUploadStats||(Module.__openttdUploadStats={fullUploads:0,partialUploads:0,rectUploads:0,zeroCopyRectUploads:0,packedRectUploads:0,bytesUploaded:0,bytesSaved:0,maxDirtyRects:0,multiRectFrames:0,lastRect:null,lastRects:null,webgl2:__otPresenter.isWebGL2});
  __otStats.webgl2=!!__otPresenter.isWebGL2;
  var __otFullBytes=__otW*__otH*4,__otFullPixels=__otW*__otH;
  if(__otPresenter.w!==__otW||__otPresenter.h!==__otH){
    var __otSrc=HEAPU8.subarray(__otPixels,__otPixels+__otFullBytes);
    __otGl.texImage2D(__otGl.TEXTURE_2D,0,__otGl.RGBA,__otW,__otH,0,__otGl.RGBA,__otGl.UNSIGNED_BYTE,__otSrc);
    __otPresenter.w=__otW;
    __otPresenter.h=__otH;
    __otStats.fullUploads++;
    __otStats.rectUploads++;
    __otStats.bytesUploaded+=__otFullBytes;
    __otStats.lastRect=[0,0,__otW,__otH];
    __otStats.lastRects=[__otStats.lastRect];
  }else{
    var __otRects=Module.__openttdDirtyRects,__otRectCount=Module.__openttdDirtyRectCount|0,__otPlan=[],__otTotalPixels=0,__otValid=false;
    if(__otRects&&__otRectCount>0&&__otRectCount<=16&&__otRects.length>=__otRectCount*4){
      __otValid=true;
      for(var __otI=0;__otI<__otRectCount;__otI++){
        var __otBase=__otI*4,__otX=__otRects[__otBase]|0,__otY=__otRects[__otBase+1]|0,__otDW=__otRects[__otBase+2]|0,__otDH=__otRects[__otBase+3]|0;
        if(__otX<0||__otY<0||__otDW<=0||__otDH<=0||__otX+__otDW>__otW||__otY+__otDH>__otH){__otValid=false;break}
        __otPlan.push([__otX,__otY,__otDW,__otDH]);
        __otTotalPixels+=__otDW*__otDH;
      }
    }
    if(!__otValid){
      __otPlan=[];
      __otTotalPixels=0;
      var __otR=Module.__openttdDirtyRect;
      if(__otR&&__otR.length===4){
        var __otX=__otR[0]|0,__otY=__otR[1]|0,__otDW=__otR[2]|0,__otDH=__otR[3]|0;
        if(__otX>=0&&__otY>=0&&__otDW>0&&__otDH>0&&__otX+__otDW<=__otW&&__otY+__otDH<=__otH){
          __otPlan.push([__otX,__otY,__otDW,__otDH]);
          __otTotalPixels=__otDW*__otDH;
          __otValid=true;
        }
      }
    }
    var __otUseRowUpload=!!(__otPresenter.isWebGL2&&!__otPresenter.rowUploadDisabled),__otAllContiguous=true;
    if(!__otUseRowUpload&&__otValid){
      for(var __otI=0;__otI<__otPlan.length;__otI++)if(__otPlan[__otI][0]!==0||__otPlan[__otI][2]!==__otW){__otAllContiguous=false;break}
    }
    var __otCheapPartial=__otUseRowUpload||__otAllContiguous;
    var __otCallPenalty=(__otPlan.length>1?__otPlan.length-1:0)*(__otCheapPartial?2048:8192);
    var __otPartialThreshold=__otCheapPartial?0.94:0.72;
    var __otUsePartial=__otValid&&__otTotalPixels>0&&(__otTotalPixels+__otCallPenalty)<__otFullPixels*__otPartialThreshold;
    var __otPartialOk=false,__otFrameBytes=0;
    if(__otUsePartial){
      try{
        var __otFullView=null;
        if(__otUseRowUpload){
          __otFullView=HEAPU8.subarray(__otPixels,__otPixels+__otFullBytes);
          __otGl.pixelStorei(__otGl.UNPACK_ROW_LENGTH,__otW);
        }
        for(var __otI=0;__otI<__otPlan.length;__otI++){
          var __otRect=__otPlan[__otI],__otX=__otRect[0],__otY=__otRect[1],__otDW=__otRect[2],__otDH=__otRect[3],__otBytes=__otDW*__otDH*4,__otUpload;
          if(__otUseRowUpload){
            __otGl.pixelStorei(__otGl.UNPACK_SKIP_PIXELS,__otX);
            __otGl.pixelStorei(__otGl.UNPACK_SKIP_ROWS,__otY);
            __otUpload=__otFullView;
            __otStats.zeroCopyRectUploads++;
          }else if(__otX===0&&__otDW===__otW){
            var __otStart=__otPixels+__otY*__otW*4;
            __otUpload=HEAPU8.subarray(__otStart,__otStart+__otBytes);
            __otStats.zeroCopyRectUploads++;
          }else{
            if(!__otPresenter.scratch||__otPresenter.scratch.length<__otBytes)__otPresenter.scratch=new Uint8Array(__otBytes);
            var __otRowBytes=__otDW*4;
            for(var __otRow=0;__otRow<__otDH;__otRow++){
              var __otStart=__otPixels+((__otY+__otRow)*__otW+__otX)*4;
              __otPresenter.scratch.set(HEAPU8.subarray(__otStart,__otStart+__otRowBytes),__otRow*__otRowBytes);
            }
            __otUpload=__otPresenter.scratch.subarray(0,__otBytes);
            __otStats.packedRectUploads++;
          }
          __otGl.texSubImage2D(__otGl.TEXTURE_2D,0,__otX,__otY,__otDW,__otDH,__otGl.RGBA,__otGl.UNSIGNED_BYTE,__otUpload);
          __otFrameBytes+=__otBytes;
          __otStats.rectUploads++;
        }
        __otPartialOk=true;
      }catch(e){
        if(__otUseRowUpload){
          __otPresenter.rowUploadDisabled=true;
          if(!__otPresenter.rowUploadWarned){__otPresenter.rowUploadWarned=true;console.warn("[OpenTTD perf] WebGL2 zero-copy rectangle upload disabled; using packed fallback.",e)}
        }else throw e;
      }finally{
        if(__otUseRowUpload){
          __otGl.pixelStorei(__otGl.UNPACK_ROW_LENGTH,0);
          __otGl.pixelStorei(__otGl.UNPACK_SKIP_PIXELS,0);
          __otGl.pixelStorei(__otGl.UNPACK_SKIP_ROWS,0);
        }
      }
    }
    if(__otPartialOk){
      __otStats.partialUploads++;
      __otStats.bytesUploaded+=__otFrameBytes;
      __otStats.bytesSaved+=Math.max(0,__otFullBytes-__otFrameBytes);
      if(__otPlan.length>__otStats.maxDirtyRects)__otStats.maxDirtyRects=__otPlan.length;
      if(__otPlan.length>1)__otStats.multiRectFrames++;
      __otStats.lastRect=__otPlan.length===1?__otPlan[0]:null;
      __otStats.lastRects=__otPlan;
    }else{
      var __otUpload=HEAPU8.subarray(__otPixels,__otPixels+__otFullBytes);
      __otGl.texSubImage2D(__otGl.TEXTURE_2D,0,0,0,__otW,__otH,__otGl.RGBA,__otGl.UNSIGNED_BYTE,__otUpload);
      __otStats.fullUploads++;
      __otStats.rectUploads++;
      __otStats.bytesUploaded+=__otFullBytes;
      __otStats.lastRect=[0,0,__otW,__otH];
      __otStats.lastRects=[__otStats.lastRect];
    }
  }
  __otGl.drawArrays(__otGl.TRIANGLE_STRIP,0,4);
  return;
}
'''
    return js.replace("__OT_W__", w).replace("__OT_H__", h).replace("__OT_PIXELS__", pixels)


def patch_renderer(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "multiRectFrames" in text and "UNPACK_ROW_LENGTH" in text:
        print("Multi-rect WebGL2 presenter already present")
        return
    if "__openttdWebGLPresenter" in text:
        raise SystemExit("Older WebGL presenter already present; apply this patch to a clean generated runtime")

    body_start, body_end, args, original, entry_id = find_presenter(text)
    fast = webgl_fast_path(args[0], args[1], args[2])
    text = text[:body_start] + fast + original + text[body_end:]
    required = (
        "__openttdWebGLPresenter",
        "__openttdDirtyRects",
        "__openttdDirtyRectCount",
        "__openttdUploadStats",
        "UNPACK_ROW_LENGTH",
        "zeroCopyRectUploads",
        "multiRectFrames",
        "texSubImage2D",
        "Canvas2D fallback",
    )
    for token in required:
        if token not in text:
            raise SystemExit(f"WebGL presenter patch missing invariant: {token}")
    path.write_text(text, encoding="utf-8")
    print(f"Multi-rect WebGL2 presenter patched in Emscripten entry {entry_id}; WebGL1/Canvas2D fallback preserved")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("runtime", type=Path)
    args = parser.parse_args()
    patch_renderer(args.runtime.resolve())


if __name__ == "__main__":
    main()
