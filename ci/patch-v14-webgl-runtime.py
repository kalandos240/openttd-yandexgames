#!/usr/bin/env python3
"""Patch the SDL2 software framebuffer presenter to WebGL without fixed EM_ASM IDs."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def patch_renderer(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "__openttdWebGLPresenter" in text:
        print("WebGL presenter already present")
        return

    start_marker = 'var w=$0;var h=$1;var pixels=$2;if(!Module["SDL2"])Module["SDL2"]={};var SDL2=Module["SDL2"];'
    start = text.find(start_marker)
    if start < 0:
        raise SystemExit("Could not locate SDL2 software framebuffer presenter start")

    # Emscripten emits EM_ASM bodies as numeric object entries. Native C++
    # changes can shift those numeric IDs, so match the structural next-entry
    # boundary instead of the historical literal `1302158`.
    boundary = re.search(r"},\d+:", text[start:])
    if boundary is None:
        raise SystemExit("Could not locate SDL2 framebuffer presenter boundary")
    end = start + boundary.start()
    span = end - start
    if span < 500 or span > 20000:
        raise SystemExit(f"Unexpected SDL2 presenter span: {span}")

    replacement = r'''var w=$0;var h=$1;var pixels=$2;if(!Module["SDL2"])Module["SDL2"]={};var SDL2=Module["SDL2"];var canvas=Module["canvas"];if(SDL2.__openttdPresenterCanvas!==canvas){SDL2.__openttdPresenterCanvas=canvas;SDL2.__openttdWebGLPresenter=null;SDL2.ctx=null;try{var attrs={alpha:false,antialias:false,depth:false,stencil:false,preserveDrawingBuffer:false,premultipliedAlpha:false};var gl=canvas.getContext("webgl",attrs)||canvas.getContext("experimental-webgl",attrs);if(gl){var compile=function(type,source){var shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(shader)||"shader compile failed");return shader};var vs=compile(gl.VERTEX_SHADER,"attribute vec2 a;varying vec2 v;void main(){gl_Position=vec4(a,0.0,1.0);v=vec2((a.x+1.0)*0.5,(1.0-a.y)*0.5);}");var fs=compile(gl.FRAGMENT_SHADER,"precision mediump float;varying vec2 v;uniform sampler2D t;void main(){vec3 c=texture2D(t,v).rgb;gl_FragColor=vec4(c,1.0);}");var program=gl.createProgram();gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program)||"program link failed");gl.useProgram(program);var buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW);var loc=gl.getAttribLocation(program,"a");gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);var texture=gl.createTexture();gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,texture);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.uniform1i(gl.getUniformLocation(program,"t"),0);gl.pixelStorei(gl.UNPACK_ALIGNMENT,4);SDL2.__openttdWebGLPresenter={gl:gl,program:program,buffer:buffer,texture:texture,w:0,h:0};}}catch(e){console.warn("[OpenTTD perf] WebGL framebuffer presenter unavailable; using Canvas2D fallback.",e)}if(!SDL2.__openttdWebGLPresenter){SDL2.ctx=canvas.getContext("2d",{alpha:false})||Module["createContext"](canvas,false,true);}}var presenter=SDL2.__openttdWebGLPresenter;if(presenter){var gl=presenter.gl;gl.viewport(0,0,canvas.width,canvas.height);gl.useProgram(presenter.program);gl.bindBuffer(gl.ARRAY_BUFFER,presenter.buffer);gl.bindTexture(gl.TEXTURE_2D,presenter.texture);var src8=HEAPU8.subarray(pixels,pixels+w*h*4);if(presenter.w!==w||presenter.h!==h){gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,w,h,0,gl.RGBA,gl.UNSIGNED_BYTE,src8);presenter.w=w;presenter.h=h}else{gl.texSubImage2D(gl.TEXTURE_2D,0,0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,src8)}gl.drawArrays(gl.TRIANGLE_STRIP,0,4);return}if(SDL2.w!==w||SDL2.h!==h||SDL2.imageCtx!==SDL2.ctx){SDL2.image=SDL2.ctx.createImageData(w,h);SDL2.w=w;SDL2.h=h;SDL2.imageCtx=SDL2.ctx}var data=SDL2.image.data;var src=pixels>>2;var dst=0;var num;if(typeof CanvasPixelArray!=="undefined"&&data instanceof CanvasPixelArray){num=data.length;while(dst<num){var val=HEAP32[src];data[dst]=val&255;data[dst+1]=val>>8&255;data[dst+2]=val>>16&255;data[dst+3]=255;src++;dst+=4}}else{if(SDL2.data32Data!==data){SDL2.data32=new Int32Array(data.buffer);SDL2.data8=new Uint8Array(data.buffer);SDL2.data32Data=data}var data32=SDL2.data32;num=data32.length;data32.set(HEAP32.subarray(src,src+num));var data8=SDL2.data8;var i=3;var j=i+4*num;if(num%8==0){while(i<j){data8[i]=255;i=i+4|0;data8[i]=255;i=i+4|0;data8[i]=255;i=i+4|0;data8[i]=255;i=i+4|0;data8[i]=255;i=i+4|0;data8[i]=255;i=i+4|0;data8[i]=255;i=i+4|0;data8[i]=255;i=i+4|0}}else{while(i<j){data8[i]=255;i=i+4|0}}}SDL2.ctx.putImageData(SDL2.image,0,0)'''

    text = text[:start] + replacement + text[end:]
    if "__openttdWebGLPresenter" not in text or "texSubImage2D" not in text:
        raise SystemExit("WebGL presenter patch failed")
    path.write_text(text, encoding="utf-8")
    print(f"WebGL presenter patched using structural boundary (old span {span} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("runtime", type=Path)
    args = parser.parse_args()
    patch_renderer(args.runtime.resolve())


if __name__ == "__main__":
    main()
