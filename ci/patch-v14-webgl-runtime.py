#!/usr/bin/env python3
"""Patch the generated SDL2 software framebuffer presenter to a WebGL fast path.

Supports both the minified SINGLE_FILE glue used by the verified V28 package and
the normal split Emscripten 3.1.57 JS glue used by CrazyGames V2.  The locator
is deliberately independent of numeric EM_ASM entry IDs, property quoting and
local variable names.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def _matching_brace(text: str, open_pos: int) -> int:
    """Return the position of the closing brace for a JS block.

    Generated Emscripten EM_ASM bodies can contain nested functions, strings and
    comments, so a simple `},<next id>:` boundary is not reliable across output
    modes.  This small scanner is sufficient for generated JS and deliberately
    does not try to parse the whole JavaScript grammar.
    """
    if open_pos < 0 or open_pos >= len(text) or text[open_pos] != "{":
        raise ValueError("open_pos is not a JavaScript block")

    depth = 0
    i = open_pos
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False

    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if line_comment:
            if ch in "\r\n":
                line_comment = False
            i += 1
            continue
        if block_comment:
            if ch == "*" and nxt == "/":
                block_comment = False
                i += 2
            else:
                i += 1
            continue
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            i += 1
            continue

        if ch == "/" and nxt == "/":
            line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            block_comment = True
            i += 2
            continue
        if ch in ("'", '"', "`"):
            quote = ch
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1

    raise SystemExit("Could not locate SDL2 presenter closing brace")


def _entry_headers(text: str, start: int, end: int):
    """Yield supported Emscripten ASM_CONST entry headers in a window."""
    window = text[start:end]
    patterns = (
        # Emscripten optimized output: 123:(a,b,c)=>{
        re.compile(r"(?:^|[,\{])\s*(\d+)\s*:\s*\(([^)]*)\)\s*=>\s*\{"),
        # Readable/older output: 123:function(a,b,c){
        re.compile(r"(?:^|[,\{])\s*(\d+)\s*:\s*function\s*\(([^)]*)\)\s*\{"),
        # Some post-processors quote numeric object keys.
        re.compile(r"(?:^|[,\{])\s*['\"](\d+)['\"]\s*:\s*\(([^)]*)\)\s*=>\s*\{"),
        re.compile(r"(?:^|[,\{])\s*['\"](\d+)['\"]\s*:\s*function\s*\(([^)]*)\)\s*\{"),
    )
    hits = []
    for pattern in patterns:
        for match in pattern.finditer(window):
            brace_rel = match.end() - 1
            hits.append((start + match.start(), start + brace_rel, match.group(1), match.group(2)))
    return sorted(hits, key=lambda item: item[0])


def find_presenter(text: str) -> tuple[int, int, list[str], str, str]:
    """Return body start/end, argument names, original body and entry ID."""
    candidates: list[int] = []
    for hit in re.finditer(r"\.putImageData\s*\(", text):
        pos = hit.start()
        nearby = text[max(0, pos - 6000):pos + 512]
        # SDL2's software presenter always creates ImageData and writes it with
        # putImageData.  Accept both Module.SDL2 and Module['SDL2'] layouts.
        if "createImageData" in nearby and "SDL2" in nearby:
            candidates.append(pos)

    if not candidates:
        # Provide diagnostics in CI rather than silently dropping the fast path.
        raise SystemExit(
            "Could not locate SDL2 software framebuffer presenter "
            f"(putImageData={text.count('.putImageData')}, "
            f"createImageData={text.count('createImageData')}, SDL2={text.count('SDL2')})"
        )

    for candidate in candidates:
        window_start = max(0, candidate - 20000)
        headers = _entry_headers(text, window_start, candidate)
        for _, open_brace, entry_id, raw_args in reversed(headers):
            try:
                close_brace = _matching_brace(text, open_brace)
            except (ValueError, SystemExit):
                continue
            if not (open_brace < candidate < close_brace):
                continue

            args = [part.strip() for part in raw_args.split(",") if part.strip()]
            if len(args) != 3:
                continue
            body_start = open_brace + 1
            body_end = close_brace
            original = text[body_start:body_end]
            if (
                ".putImageData" in original
                and "createImageData" in original
                and "SDL2" in original
                and 250 <= len(original) <= 20000
            ):
                return body_start, body_end, args, original, entry_id

    raise SystemExit("Could not resolve Emscripten EM_ASM entry containing SDL2 presenter")


def webgl_fast_path(w: str, h: str, pixels: str) -> str:
    return f'''var __otW={w},__otH={h},__otPixels={pixels};Module.SDL2||(Module.SDL2={{}});var __otSDL=Module.SDL2,__otCanvas=Module.canvas;if(__otSDL.__openttdPresenterCanvas!==__otCanvas){{__otSDL.__openttdPresenterCanvas=__otCanvas;__otSDL.__openttdWebGLPresenter=null;try{{var __otAttrs={{alpha:false,antialias:false,depth:false,stencil:false,preserveDrawingBuffer:false,premultipliedAlpha:false}},__otGl=__otCanvas.getContext("webgl",__otAttrs)||__otCanvas.getContext("experimental-webgl",__otAttrs);if(__otGl){{var __otCompile=function(type,source){{var shader=__otGl.createShader(type);__otGl.shaderSource(shader,source);__otGl.compileShader(shader);if(!__otGl.getShaderParameter(shader,__otGl.COMPILE_STATUS))throw new Error(__otGl.getShaderInfoLog(shader)||"shader compile failed");return shader}},__otVs=__otCompile(__otGl.VERTEX_SHADER,"attribute vec2 a;varying vec2 v;void main(){{gl_Position=vec4(a,0.0,1.0);v=vec2((a.x+1.0)*0.5,(1.0-a.y)*0.5);}}"),__otFs=__otCompile(__otGl.FRAGMENT_SHADER,"precision mediump float;varying vec2 v;uniform sampler2D t;void main(){{vec3 c=texture2D(t,v).rgb;gl_FragColor=vec4(c,1.0);}}"),__otProgram=__otGl.createProgram();__otGl.attachShader(__otProgram,__otVs);__otGl.attachShader(__otProgram,__otFs);__otGl.linkProgram(__otProgram);if(!__otGl.getProgramParameter(__otProgram,__otGl.LINK_STATUS))throw new Error(__otGl.getProgramInfoLog(__otProgram)||"program link failed");__otGl.useProgram(__otProgram);var __otBuffer=__otGl.createBuffer();__otGl.bindBuffer(__otGl.ARRAY_BUFFER,__otBuffer);__otGl.bufferData(__otGl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),__otGl.STATIC_DRAW);var __otLoc=__otGl.getAttribLocation(__otProgram,"a");__otGl.enableVertexAttribArray(__otLoc);__otGl.vertexAttribPointer(__otLoc,2,__otGl.FLOAT,false,0,0);var __otTexture=__otGl.createTexture();__otGl.activeTexture(__otGl.TEXTURE0);__otGl.bindTexture(__otGl.TEXTURE_2D,__otTexture);__otGl.texParameteri(__otGl.TEXTURE_2D,__otGl.TEXTURE_MIN_FILTER,__otGl.NEAREST);__otGl.texParameteri(__otGl.TEXTURE_2D,__otGl.TEXTURE_MAG_FILTER,__otGl.NEAREST);__otGl.texParameteri(__otGl.TEXTURE_2D,__otGl.TEXTURE_WRAP_S,__otGl.CLAMP_TO_EDGE);__otGl.texParameteri(__otGl.TEXTURE_2D,__otGl.TEXTURE_WRAP_T,__otGl.CLAMP_TO_EDGE);__otGl.uniform1i(__otGl.getUniformLocation(__otProgram,"t"),0);__otGl.pixelStorei(__otGl.UNPACK_ALIGNMENT,4);__otSDL.__openttdWebGLPresenter={{gl:__otGl,program:__otProgram,buffer:__otBuffer,texture:__otTexture,w:0,h:0}};}}}}catch(e){{console.warn("[OpenTTD perf] WebGL framebuffer presenter unavailable; using Canvas2D fallback.",e)}}}}var __otPresenter=__otSDL.__openttdWebGLPresenter;if(__otPresenter){{var __otGl=__otPresenter.gl;__otGl.viewport(0,0,__otCanvas.width,__otCanvas.height);__otGl.useProgram(__otPresenter.program);__otGl.bindBuffer(__otGl.ARRAY_BUFFER,__otPresenter.buffer);__otGl.bindTexture(__otGl.TEXTURE_2D,__otPresenter.texture);var __otSrc=HEAPU8.subarray(__otPixels,__otPixels+__otW*__otH*4);if(__otPresenter.w!==__otW||__otPresenter.h!==__otH){{__otGl.texImage2D(__otGl.TEXTURE_2D,0,__otGl.RGBA,__otW,__otH,0,__otGl.RGBA,__otGl.UNSIGNED_BYTE,__otSrc);__otPresenter.w=__otW;__otPresenter.h=__otH}}else __otGl.texSubImage2D(__otGl.TEXTURE_2D,0,0,0,__otW,__otH,__otGl.RGBA,__otGl.UNSIGNED_BYTE,__otSrc);__otGl.drawArrays(__otGl.TRIANGLE_STRIP,0,4);return}}'''


def patch_renderer(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "__openttdWebGLPresenter" in text:
        print("WebGL presenter already present")
        return

    body_start, body_end, args, original, entry_id = find_presenter(text)
    fast = webgl_fast_path(args[0], args[1], args[2])
    text = text[:body_start] + fast + original + text[body_end:]
    if "__openttdWebGLPresenter" not in text or "texSubImage2D" not in text or "Canvas2D fallback" not in text:
        raise SystemExit("WebGL presenter patch failed")
    path.write_text(text, encoding="utf-8")
    print(f"WebGL presenter patched in Emscripten entry {entry_id}; Canvas2D fallback preserved")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("runtime", type=Path)
    args = parser.parse_args()
    patch_renderer(args.runtime.resolve())


if __name__ == "__main__":
    main()
