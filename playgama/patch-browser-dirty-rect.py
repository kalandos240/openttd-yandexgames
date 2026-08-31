#!/usr/bin/env python3
"""Expose multiple OpenTTD SDL dirty rectangles to the browser presenter.

OpenTTD 15.3 collapses all invalidations into one bounding rectangle before the
Emscripten SDL2 backend presents the frame. That is correct but wasteful in a
browser: two small distant updates can become an almost full-screen upload.

This browser-only patch keeps the stock bounding rectangle for native SDL
behaviour, while additionally tracking up to 16 merged dirty rectangles for the
WebGL presenter. When the list is full, the new rectangle is merged into the
existing rectangle with the smallest area growth instead of falling back to a
all-screen bounding box.
"""
from __future__ import annotations

import argparse
from pathlib import Path

MARKER = "# V14_MULTI_DIRTY_RECT_SOURCE_PATCH\n"


def patch_build_script(text: str) -> str:
    if MARKER.strip() in text:
        return text

    anchor = "git clone --depth 1 --branch 15.3 https://github.com/OpenTTD/OpenTTD.git openttd\n"
    if text.count(anchor) != 1:
        raise SystemExit(f"Expected one OpenTTD clone anchor, got {text.count(anchor)}")

    source_patch = r"""# V14_MULTI_DIRTY_RECT_SOURCE_PATCH
python3 - <<'PY_DIRTY_RECT_SOURCE'
from pathlib import Path

header = Path('openttd/src/video/sdl2_v.h')
text = header.read_text(encoding='utf-8')
anchor = '''\tRect dirty_rect{}; ///< Rectangle encompassing the dirty area of the video buffer.\n'''
replacement = anchor + '''#ifdef __EMSCRIPTEN__
\tstatic constexpr size_t BROWSER_DIRTY_RECT_LIMIT = 16;
\tRect browser_dirty_rects[BROWSER_DIRTY_RECT_LIMIT]{};
\tsize_t browser_dirty_rect_count = 0;
#endif
'''
if 'BROWSER_DIRTY_RECT_LIMIT' not in text:
    if text.count(anchor) != 1:
        raise SystemExit(f'Expected one SDL dirty_rect field anchor, got {text.count(anchor)}')
    text = text.replace(anchor, replacement, 1)
header.write_text(text, encoding='utf-8')

base = Path('openttd/src/video/sdl2_v.cpp')
text = base.read_text(encoding='utf-8')
anchor = '''void VideoDriver_SDL_Base::MakeDirty(int left, int top, int width, int height)
{
\tRect r = {left, top, left + width, top + height};
\tthis->dirty_rect = BoundingRect(this->dirty_rect, r);
}
'''
replacement = '''void VideoDriver_SDL_Base::MakeDirty(int left, int top, int width, int height)
{
\tRect r = {left, top, left + width, top + height};
\tthis->dirty_rect = BoundingRect(this->dirty_rect, r);

#ifdef __EMSCRIPTEN__
\t/* Preserve spatial locality instead of collapsing every invalidation into
\t * one bounding box. Nearby rectangles are merged to keep GL call count low.
\t * When all slots are occupied, merge into the slot with the least area
\t * growth; this is still much cheaper than promoting the entire frame. */
\tconstexpr int browser_merge_gap = 4;
\tRect merged = r;
\tfor (size_t i = 0; i < this->browser_dirty_rect_count;) {
\t\tconst Rect &candidate = this->browser_dirty_rects[i];
\t\tconst bool nearby =
\t\t\tmerged.left <= candidate.right + browser_merge_gap &&
\t\t\tmerged.right + browser_merge_gap >= candidate.left &&
\t\t\tmerged.top <= candidate.bottom + browser_merge_gap &&
\t\t\tmerged.bottom + browser_merge_gap >= candidate.top;
\t\tif (!nearby) {
\t\t\t++i;
\t\t\tcontinue;
\t\t}

\t\tmerged = BoundingRect(merged, candidate);
\t\tthis->browser_dirty_rects[i] = this->browser_dirty_rects[this->browser_dirty_rect_count - 1];
\t\t--this->browser_dirty_rect_count;
\t\ti = 0;
\t}

\tif (this->browser_dirty_rect_count < BROWSER_DIRTY_RECT_LIMIT) {
\t\tthis->browser_dirty_rects[this->browser_dirty_rect_count++] = merged;
\t} else {
\t\tauto area = [](const Rect &rect) -> int64_t {
\t\t\treturn static_cast<int64_t>(rect.right - rect.left) * static_cast<int64_t>(rect.bottom - rect.top);
\t\t};
\t\tsize_t best = 0;
\t\tint64_t best_growth = INT64_MAX;
\t\tfor (size_t i = 0; i < this->browser_dirty_rect_count; ++i) {
\t\t\tconst Rect combined = BoundingRect(this->browser_dirty_rects[i], merged);
\t\t\tconst int64_t growth = area(combined) - area(this->browser_dirty_rects[i]);
\t\t\tif (growth < best_growth) {
\t\t\t\tbest = i;
\t\t\t\tbest_growth = growth;
\t\t\t}
\t\t}
\t\tthis->browser_dirty_rects[best] = BoundingRect(this->browser_dirty_rects[best], merged);
\t}
#endif
}
'''
if 'browser_dirty_rect_count' not in text:
    if text.count(anchor) != 1:
        raise SystemExit(f'Expected one SDL MakeDirty anchor, got {text.count(anchor)}')
    text = text.replace(anchor, replacement, 1)
base.write_text(text, encoding='utf-8')

path = Path('openttd/src/video/sdl2_default_v.cpp')
text = path.read_text(encoding='utf-8')
anchor = '''\tSDL_UpdateWindowSurfaceRects(this->sdl_window, &r, 1);\n'''
replacement = '''#ifdef __EMSCRIPTEN__
\t/* Publish the browser-only rectangle list immediately before SDL invokes its
\t * generated presenter. Keep the original single bounding rectangle too for
\t * compatibility with older runtime patches and as a correctness fallback. */
\tSDL_Rect browser_rects[BROWSER_DIRTY_RECT_LIMIT];
\tsize_t browser_rect_count = this->browser_dirty_rect_count;
\tif (browser_rect_count == 0) {
\t\tbrowser_rects[0] = r;
\t\tbrowser_rect_count = 1;
\t} else {
\t\tfor (size_t i = 0; i < browser_rect_count; ++i) {
\t\t\tconst Rect &dirty = this->browser_dirty_rects[i];
\t\t\tbrowser_rects[i] = {
\t\t\t\tdirty.left,
\t\t\t\tdirty.top,
\t\t\t\tdirty.right - dirty.left,
\t\t\t\tdirty.bottom - dirty.top,
\t\t\t};
\t\t}
\t}

\tEM_ASM({
\t\tvar src = $0 >> 2;
\t\tvar count = $1 | 0;
\t\tvar needed = count * 4;
\t\tif (!Module.__openttdDirtyRects || Module.__openttdDirtyRects.length < needed) {
\t\t\tModule.__openttdDirtyRects = new Int32Array(needed);
\t\t}
\t\tfor (var i = 0; i < needed; ++i) Module.__openttdDirtyRects[i] = HEAP32[src + i];
\t\tModule.__openttdDirtyRectCount = count;
\t\tif (!Module.__openttdDirtyRect) Module.__openttdDirtyRect = new Int32Array(4);
\t\tModule.__openttdDirtyRect[0] = $2;
\t\tModule.__openttdDirtyRect[1] = $3;
\t\tModule.__openttdDirtyRect[2] = $4;
\t\tModule.__openttdDirtyRect[3] = $5;
\t}, browser_rects, browser_rect_count, r.x, r.y, r.w, r.h);
#endif
\tSDL_UpdateWindowSurfaceRects(this->sdl_window, &r, 1);
#ifdef __EMSCRIPTEN__
\tthis->browser_dirty_rect_count = 0;
#endif
'''
if 'Module.__openttdDirtyRects' not in text:
    if text.count(anchor) != 1:
        raise SystemExit(f'Expected one SDL framebuffer update anchor, got {text.count(anchor)}')
    text = text.replace(anchor, replacement, 1)

resize_anchor = '''\tthis->dirty_rect = {};\n'''
if text.count(resize_anchor) < 1:
    raise SystemExit('Could not find SDL dirty-rect reset anchor')
allocate_pos = text.find('bool VideoDriver_SDL_Default::AllocateBackingStore')
if allocate_pos < 0:
    raise SystemExit('Could not find AllocateBackingStore')
reset_pos = text.find(resize_anchor, allocate_pos)
if reset_pos < 0:
    raise SystemExit('Could not find AllocateBackingStore dirty-rect reset')
reset_end = reset_pos + len(resize_anchor)
reset_code = '''#ifdef __EMSCRIPTEN__
\tthis->browser_dirty_rect_count = 0;
#endif
'''
if reset_code not in text[allocate_pos:]:
    text = text[:reset_end] + reset_code + text[reset_end:]

path.write_text(text, encoding='utf-8')
PY_DIRTY_RECT_SOURCE
"""
    return text.replace(anchor, anchor + source_patch, 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("build_script", type=Path)
    args = parser.parse_args()

    path = args.build_script
    text = path.read_text(encoding="utf-8")
    text = patch_build_script(text)
    required = (
        "BROWSER_DIRTY_RECT_LIMIT",
        "browser_dirty_rect_count",
        "Module.__openttdDirtyRects",
        "V14_MULTI_DIRTY_RECT_SOURCE_PATCH",
    )
    for token in required:
        if token not in text:
            raise SystemExit(f"Multi dirty-rect source invariant missing after patch: {token}")
    path.write_text(text, encoding="utf-8")
    print("Browser multi-dirty-rect bridge enabled for SDL2 framebuffer presentation.")


if __name__ == "__main__":
    main()
