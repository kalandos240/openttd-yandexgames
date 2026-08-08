#!/usr/bin/env bash
set -euo pipefail

echo 'Preparing the Emscripten FreeType port for Russian/Cyrillic text...'
embuilder build freetype

bash ci/build-final.sh

echo 'FreeType CMake detection:'
grep -i 'freetype' openttd/build/CMakeCache.txt | head -40 || true
