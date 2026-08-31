#!/usr/bin/env python3
"""Browser-only palette-animation invalidation optimization.

For the 32bpp animation blitter OpenTTD already walks the animation buffer and
rewrites only pixels that use palette-animation colours. The SDL2 path still
forces a full-screen dirty rectangle as soon as the palette changes, before the
blitter gets a chance to describe what actually changed. That converts every
palette tick into a full RGBA texture upload in the browser.

Under Emscripten this patch preserves the exact palette and framebuffer update
logic, but:
  * CheckPaletteAnim does not pre-mark the whole screen when the active blitter
    performs palette animation itself; Paint() already runs because the copied
    palette remains dirty.
  * Blitter_32bppAnim::PaletteAnimate aggregates pixels it actually updates into
    a fixed 4x4 spatial grid and publishes at most 16 dirty rectangles.

Native OpenTTD behaviour is untouched. The bookkeeping uses only fixed stack
arrays; no per-frame heap allocation is introduced.
"""
from __future__ import annotations

import argparse
from pathlib import Path

MARKER = "# V14_BROWSER_PALETTE_DIRTY_PATCH\n"


def patch_build_script(text: str) -> str:
    if MARKER.strip() in text:
        return text

    anchor = "git clone --depth 1 --branch 15.3 https://github.com/OpenTTD/OpenTTD.git openttd\n"
    if text.count(anchor) != 1:
        raise SystemExit(f"Expected one OpenTTD clone anchor, got {text.count(anchor)}")

    source_patch = r"""# V14_BROWSER_PALETTE_DIRTY_PATCH
python3 - <<'PY_BROWSER_PALETTE_DIRTY'
from pathlib import Path

sdl = Path('openttd/src/video/sdl2_v.cpp')
s = sdl.read_text(encoding='utf-8')
check_anchor = '''void VideoDriver_SDL_Base::CheckPaletteAnim()
{
\tif (!CopyPalette(this->local_palette)) return;
\tthis->MakeDirty(0, 0, _screen.width, _screen.height);
}
'''
check_replacement = '''void VideoDriver_SDL_Base::CheckPaletteAnim()
{
\tif (!CopyPalette(this->local_palette)) return;
#ifdef __EMSCRIPTEN__
\tBlitter *blitter = BlitterFactory::GetCurrentBlitter();
\tif (blitter != nullptr && blitter->UsePaletteAnimation() == Blitter::PaletteAnimation::Blitter) return;
#endif
\tthis->MakeDirty(0, 0, _screen.width, _screen.height);
}
'''
if 'UsePaletteAnimation() == Blitter::PaletteAnimation::Blitter) return;' not in s:
    if s.count(check_anchor) != 1:
        raise SystemExit(f'Expected one SDL CheckPaletteAnim anchor, got {s.count(check_anchor)}')
    s = s.replace(check_anchor, check_replacement, 1)
sdl.write_text(s, encoding='utf-8')

path = Path('openttd/src/blitter/32bpp_anim.cpp')
b = path.read_text(encoding='utf-8')

setup_anchor = '''\tconst int width = this->anim_buf_width;
\tconst int pitch_offset = _screen.pitch - width;
\tconst int anim_pitch_offset = this->anim_buf_pitch - width;
'''
setup_replacement = setup_anchor + '''#ifdef __EMSCRIPTEN__
\tstatic constexpr int browser_palette_grid = 4;
\tstatic constexpr int browser_palette_regions = browser_palette_grid * browser_palette_grid;
\tint browser_left[browser_palette_regions]{};
\tint browser_top[browser_palette_regions]{};
\tint browser_right[browser_palette_regions]{};
\tint browser_bottom[browser_palette_regions]{};
\tuint16_t browser_used_mask = 0;
\tconst int browser_x1 = (width + 3) / 4;
\tconst int browser_x2 = (width + 1) / 2;
\tconst int browser_x3 = (width * 3 + 3) / 4;
\tconst int browser_height = this->anim_buf_height;
\tconst int browser_y1 = (browser_height + 3) / 4;
\tconst int browser_y2 = (browser_height + 1) / 2;
\tconst int browser_y3 = (browser_height * 3 + 3) / 4;
#endif
'''
if 'browser_palette_regions' not in b:
    if b.count(setup_anchor) != 1:
        raise SystemExit(f'Expected one PaletteAnimate setup anchor, got {b.count(setup_anchor)}')
    b = b.replace(setup_anchor, setup_replacement, 1)

loop_anchor = '''\tfor (int y = this->anim_buf_height; y != 0 ; y--) {
\t\tfor (int x = width; x != 0 ; x--) {
'''
loop_replacement = '''\tfor (int y = this->anim_buf_height; y != 0 ; y--) {
#ifdef __EMSCRIPTEN__
\t\tconst int browser_y = browser_height - y;
\t\tconst int browser_by = browser_y < browser_y1 ? 0 : (browser_y < browser_y2 ? 1 : (browser_y < browser_y3 ? 2 : 3));
#endif
\t\tfor (int x = width; x != 0 ; x--) {
'''
if 'const int browser_by' not in b:
    if b.count(loop_anchor) != 1:
        raise SystemExit(f'Expected one PaletteAnimate row-loop anchor, got {b.count(loop_anchor)}')
    b = b.replace(loop_anchor, loop_replacement, 1)

pixel_anchor = '''\t\t\tif (colour >= PALETTE_ANIM_START) {
\t\t\t\t/* Update this pixel */
\t\t\t\t*dst = AdjustBrightness(LookupColourInPalette(colour), GB(value, 8, 8));
\t\t\t}
'''
pixel_replacement = '''\t\t\tif (colour >= PALETTE_ANIM_START) {
\t\t\t\t/* Update this pixel */
\t\t\t\t*dst = AdjustBrightness(LookupColourInPalette(colour), GB(value, 8, 8));
#ifdef __EMSCRIPTEN__
\t\t\t\tconst int browser_x = width - x;
\t\t\t\tconst int browser_bx = browser_x < browser_x1 ? 0 : (browser_x < browser_x2 ? 1 : (browser_x < browser_x3 ? 2 : 3));
\t\t\t\tconst int browser_index = browser_by * browser_palette_grid + browser_bx;
\t\t\t\tconst uint16_t browser_bit = static_cast<uint16_t>(1u << browser_index);
\t\t\t\tif ((browser_used_mask & browser_bit) == 0) {
\t\t\t\t\tbrowser_used_mask |= browser_bit;
\t\t\t\t\tbrowser_left[browser_index] = browser_x;
\t\t\t\t\tbrowser_top[browser_index] = browser_y;
\t\t\t\t\tbrowser_right[browser_index] = browser_x + 1;
\t\t\t\t\tbrowser_bottom[browser_index] = browser_y + 1;
\t\t\t\t} else {
\t\t\t\t\tbrowser_left[browser_index] = std::min(browser_left[browser_index], browser_x);
\t\t\t\t\tbrowser_top[browser_index] = std::min(browser_top[browser_index], browser_y);
\t\t\t\t\tbrowser_right[browser_index] = std::max(browser_right[browser_index], browser_x + 1);
\t\t\t\t\tbrowser_bottom[browser_index] = std::max(browser_bottom[browser_index], browser_y + 1);
\t\t\t\t}
#endif
\t\t\t}
'''
if 'browser_used_mask & browser_bit' not in b:
    if b.count(pixel_anchor) != 1:
        raise SystemExit(f'Expected one PaletteAnimate pixel anchor, got {b.count(pixel_anchor)}')
    b = b.replace(pixel_anchor, pixel_replacement, 1)

final_anchor = '''\t/* Make sure the backend redraws the whole screen */
\tVideoDriver::GetInstance()->MakeDirty(0, 0, _screen.width, _screen.height);
'''
final_replacement = '''#ifdef __EMSCRIPTEN__
\tfor (int browser_index = 0; browser_index < browser_palette_regions; ++browser_index) {
\t\tif ((browser_used_mask & static_cast<uint16_t>(1u << browser_index)) == 0) continue;
\t\tVideoDriver::GetInstance()->MakeDirty(
\t\t\tbrowser_left[browser_index],
\t\t\tbrowser_top[browser_index],
\t\t\tbrowser_right[browser_index] - browser_left[browser_index],
\t\t\tbrowser_bottom[browser_index] - browser_top[browser_index]);
\t}
#else
\t/* Make sure the backend redraws the whole screen */
\tVideoDriver::GetInstance()->MakeDirty(0, 0, _screen.width, _screen.height);
#endif
'''
if 'browser_palette_regions; ++browser_index' not in b:
    if b.count(final_anchor) != 1:
        raise SystemExit(f'Expected one PaletteAnimate full-screen dirty anchor, got {b.count(final_anchor)}')
    b = b.replace(final_anchor, final_replacement, 1)

path.write_text(b, encoding='utf-8')
PY_BROWSER_PALETTE_DIRTY
"""
    return text.replace(anchor, anchor + source_patch, 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("build_script", type=Path)
    args = parser.parse_args()

    path = args.build_script
    text = path.read_text(encoding="utf-8")
    text = patch_build_script(text)
    for token in (
        "V14_BROWSER_PALETTE_DIRTY_PATCH",
        "UsePaletteAnimation() == Blitter::PaletteAnimation::Blitter) return;",
        "browser_palette_regions",
        "browser_used_mask",
        "browser_palette_grid",
    ):
        if token not in text:
            raise SystemExit(f"Palette dirty-region invariant missing: {token}")
    path.write_text(text, encoding="utf-8")
    print("Browser palette animation invalidation optimized: no pre-full-dirty for 32bpp blitter; 4x4 changed-region aggregation enabled.")


if __name__ == "__main__":
    main()
