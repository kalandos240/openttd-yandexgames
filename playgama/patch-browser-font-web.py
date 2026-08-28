#!/usr/bin/env python3
"""Keep the web build usable when OpenTTD's sprite/font glyph probe is over-strict."""
from pathlib import Path

p = Path('openttd/src/strings.cpp')
s = p.read_text(encoding='utf-8')
old = '''void CheckForMissingGlyphs(MissingGlyphSearcher *searcher)\n{\n\tstatic LanguagePackGlyphSearcher pack_searcher;\n\tif (searcher == nullptr) searcher = &pack_searcher;\n\tbool bad_font = searcher->FindMissingGlyphs();\n'''
new = '''void CheckForMissingGlyphs(MissingGlyphSearcher *searcher)\n{\n\tstatic LanguagePackGlyphSearcher pack_searcher;\n\tif (searcher == nullptr) searcher = &pack_searcher;\n#ifdef __EMSCRIPTEN__\n\t/* The browser edition ships its own OpenTTD fonts and has no operating-system\n\t * fallback-font provider. The generic desktop probe therefore raises a\n\t * blocking warning even when the selected language is readable. Keep cache\n\t * metrics current, but do not present the desktop-only remediation dialog. */\n\tFontCache::LoadFontCaches(searcher->Monospace() ? FontSizes{FS_MONO} : FONTSIZES_REQUIRED);\n\tLoadStringWidthTable(searcher->Monospace() ? FontSizes{FS_MONO} : FONTSIZES_REQUIRED);\n\treturn;\n#endif\n\tbool bad_font = searcher->FindMissingGlyphs();\n'''
if old not in s:
    if 'The browser edition ships its own OpenTTD fonts' in s:
        raise SystemExit(0)
    raise SystemExit('CheckForMissingGlyphs anchor missing')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('Browser-only font warning disabled while font caches remain initialized.')
