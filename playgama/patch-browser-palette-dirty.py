#!/usr/bin/env python3
"""Browser-only palette animation dirty-region experiment.

OpenTTD's 32bpp animation blitter correctly scans the animation buffer and
updates every palette-animated framebuffer pixel, but then unconditionally marks
the entire screen dirty. In a browser that turns a small palette animation into
a full RGBA texture upload.

This patch preserves the exact pixel update loop. Under Emscripten it only
changes invalidation reporting: animated pixels are accumulated into a fixed
4x4 spatial grid and at most 16 bounding rectangles are marked dirty. Native
OpenTTD keeps the stock full-screen invalidation.
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

path = Path('openttd/src/blitter/32bpp_anim.cpp')
text = path.read_text(encoding='utf-8')

setup_anchor = '''\tconst int width = this->anim_buf_width;
\tconst int pitch_offset = _screen.pitch - width;
\tconst int anim_pitch_offset = this->anim_buf_pitch - width;
'''
setup_replacement = setup_anchor + '''#ifdef __EMSCRIPTEN__
\t/* Keep palette animation pixel-perfect, but remember only where animated
\t * pixels actually occur so the browser presenter does not upload the whole
\t * RGBA framebuffer for every palette tick. A fixed 4x4 grid keeps this O(1)
\t * memory and caps the number of final MakeDirty calls at 16. */
\tstatic constexpr int browser_palette_grid = 4;
\tstatic constexpr int browser_palette_regions = browser_palette_grid * browser_palette_grid;
\tint browser_left[browser_palette_regions]{};
\tint browser_top[browser_palette_regions]{};
\tint browser_right[browser_palette_regions]{};
\tint browser_bottom[browser_palette_regions]{};
\tuint16_t browser_used_mask = 0;
\tconst int browser_bucket_w = std::max(1, (width + browser_palette_grid - 1) / browser_palette_grid);
\tconst int browser_bucket_h = std::max(1, (this->anim_buf_height + browser_palette_grid - 1) / browser_palette_grid);
#endif
'''
if 'browser_palette_regions' not in text:
    if text.count(setup_anchor) != 1:
        raise SystemExit(f'Expected one PaletteAnimate setup anchor, got {text.count(setup_anchor)}')
    text = text.replace(setup_anchor, setup_replacement, 1)

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
\t\t\t\tconst int browser_y = this->anim_buf_height - y;
\t\t\t\tconst int browser_bx = std::min(browser_palette_grid - 1, browser_x / browser_bucket_w);
\t\t\t\tconst int browser_by = std::min(browser_palette_grid - 1, browser_y / browser_bucket_h);
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
if 'browser_used_mask & browser_bit' not in text:
    if text.count(pixel_anchor) != 1:
        raise SystemExit(f'Expected one PaletteAnimate pixel anchor, got {text.count(pixel_anchor)}')
    text = text.replace(pixel_anchor, pixel_replacement, 1)

final_anchor = '''\t/* Make sure the backend redraws the whole screen */
\tVideoDriver::GetInstance()->MakeDirty(0, 0, _screen.width, _screen.height);
'''
final_replacement = '''#ifdef __EMSCRIPTEN__
\t/* The framebuffer has already been updated exactly as stock OpenTTD does.
\t * Tell the browser only which coarse regions contain those changed pixels. */
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
if 'browser_palette_regions; ++browser_index' not in text:
    if text.count(final_anchor) != 1:
        raise SystemExit(f'Expected one PaletteAnimate full-screen dirty anchor, got {text.count(final_anchor)}')
    text = text.replace(final_anchor, final_replacement, 1)

path.write_text(text, encoding='utf-8')
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
        "browser_palette_regions",
        "browser_used_mask",
        "browser_palette_grid",
    ):
        if token not in text:
            raise SystemExit(f"Palette dirty-region invariant missing: {token}")
    path.write_text(text, encoding="utf-8")
    print("Browser palette animation dirty-region experiment enabled (4x4 spatial aggregation).")


if __name__ == "__main__":
    main()
