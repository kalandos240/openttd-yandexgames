#!/usr/bin/env bash
set -euo pipefail

mkdir -p dist/licenses/OpenTTD dist/licenses/OpenGFX dist/licenses/OpenSFX dist/licenses/OpenMSX

# OpenTTD itself and the bundled third-party source notices shipped by OpenTTD.
cp openttd/COPYING.md dist/licenses/OpenTTD/COPYING.md
cp openttd/CREDITS.md dist/licenses/OpenTTD/CREDITS.md
cp openttd/README.md dist/licenses/OpenTTD/README.md

copy_if_exists() {
  local src="$1"
  local dst="$2"
  if [ -f "$src" ]; then
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
  fi
}

copy_if_exists openttd/src/3rdparty/squirrel/COPYRIGHT dist/licenses/OpenTTD/SQUIRREL-COPYRIGHT.txt
copy_if_exists openttd/src/3rdparty/fmt/LICENSE.rst dist/licenses/OpenTTD/FMT-LICENSE.rst
copy_if_exists openttd/src/3rdparty/nlohmann/LICENSE.MIT dist/licenses/OpenTTD/NLOHMANN-LICENSE.MIT
copy_if_exists openttd/src/3rdparty/catch2/LICENSE.txt dist/licenses/OpenTTD/CATCH2-LICENSE.txt
copy_if_exists openttd/src/3rdparty/icu/LICENSE dist/licenses/OpenTTD/ICU-LICENSE.txt
copy_if_exists openttd/src/3rdparty/monocypher/LICENSE.md dist/licenses/OpenTTD/MONOCYPHER-LICENSE.md
copy_if_exists openttd/src/3rdparty/openttd_social_integration_api/LICENSE dist/licenses/OpenTTD/SOCIAL-INTEGRATION-API-LICENSE.txt
copy_if_exists openttd/cmake/3rdparty/llvm/LICENSE.txt dist/licenses/OpenTTD/LLVM-CMAKE-LICENSE.txt

# The official downloadable base-set ZIPs primarily contain a versioned .tar
# package. Their license/readme/credits files live inside that tar, so inspect
# both the outer extraction tree and every embedded tar. This deliberately uses
# the exact release packages bundled into the game rather than a moving branch.
copy_release_docs() {
  local root="$1"
  local dest="$2"
  local found=0

  mkdir -p "$dest"

  # Some release layouts expose documentation next to the tar archive.
  while IFS= read -r -d '' f; do
    local rel safe
    rel="${f#"$root"/}"
    safe="${rel//\//__}"
    cp "$f" "$dest/$safe"
    found=1
  done < <(find "$root" -type f \( \
      -iname 'license*' -o -iname 'copying*' -o -iname 'readme*' -o \
      -iname 'credits*' -o -iname 'authors*' -o -iname 'changelog*' \
    \) -print0)

  # The normal OpenTTD content-service packages keep these documents inside
  # their .tar. Extract only documentation, never arbitrary archive paths.
  while IFS= read -r -d '' archive; do
    while IFS= read -r member; do
      [ -n "$member" ] || continue
      local safe
      safe="${member#./}"
      safe="${safe//\//__}"
      # Avoid an unlikely basename collision between outer and inner docs.
      if [ -e "$dest/$safe" ]; then
        safe="archive__${safe}"
      fi
      tar -xOf "$archive" "$member" > "$dest/$safe"
      test -s "$dest/$safe"
      found=1
    done < <(tar -tf "$archive" | grep -Ei '(^|/)(license|copying|readme|credits|authors|changelog)([^/]*)$' || true)
  done < <(find "$root" -type f -name '*.tar' -print0)

  if [ "$found" -eq 0 ]; then
    echo "No legal/readme documentation found in release package under $root" >&2
    echo "Package contents were:" >&2
    find "$root" -maxdepth 3 -type f -print >&2 || true
    return 1
  fi
}

copy_release_docs /tmp/ottd-assets/opengfx dist/licenses/OpenGFX
copy_release_docs /tmp/ottd-assets/opensfx dist/licenses/OpenSFX
copy_release_docs /tmp/ottd-assets/openmsx dist/licenses/OpenMSX

cat > dist/SOURCE_CODE.txt <<EOF
OpenTTD 15.3 - Yandex Games WebAssembly edition
================================================

This distribution contains a modified build of OpenTTD 15.3.
OpenTTD is licensed under the GNU General Public License version 2.

Upstream OpenTTD source used for this build:
https://github.com/OpenTTD/OpenTTD/tree/15.3
Upstream commit pinned by the build: 14ec60f248547d4d062a1160f0fc26d742319888

Yandex Games port source, patches and reproducible build scripts:
https://github.com/kalandos240/openttd-yandexgames
Build revision: ${GITHUB_SHA:-local-build}

The repository above contains the port-specific source changes and build
scripts used to produce this WebAssembly package. Together with the pinned
OpenTTD 15.3 upstream source, these are the preferred source form for the
modified program.

No proprietary Transport Tycoon Deluxe graphics, sounds or music are bundled.
The build uses the free OpenGFX 8.0, OpenSFX 1.0.3 and OpenMSX 0.4.2 base sets.

See the licenses/ directory for license texts, notices and credits.
EOF

cat > dist/NOTICE.txt <<'EOF'
OpenTTD 15.3 - Yandex Games WebAssembly edition
================================================

This is a modified distribution of OpenTTD and is not an official release of
the OpenTTD project.

OpenTTD
-------
OpenTTD is Copyright (C) the OpenTTD contributors and is licensed under the
GNU General Public License version 2. The complete GPL v2 text shipped by
OpenTTD is included at:
  licenses/OpenTTD/COPYING.md
Credits and third-party notices are included in licenses/OpenTTD/.

Free base sets bundled with this build
--------------------------------------
OpenGFX 8.0  - graphics base set. OpenGFX is licensed under GNU GPL v2.
OpenSFX 1.0.3 - sound base set. The sound collection as a whole is licensed
                under Creative Commons Attribution-ShareAlike 3.0 Unported;
                supporting files have their own GPL/CDDL terms as documented
                by OpenSFX.
OpenMSX 0.4.2 - music base set, licensed under GNU GPL v2.

The exact license/readme/credits files distributed with those official release
packages are included under licenses/OpenGFX, licenses/OpenSFX and
licenses/OpenMSX.

Source code
-----------
The source location and exact upstream revision are documented in
SOURCE_CODE.txt. Port source/build scripts are publicly available at:
  https://github.com/kalandos240/openttd-yandexgames

No original/proprietary Transport Tycoon Deluxe asset files are included.

Yandex Games integration and WebAssembly build modifications are distributed
under GNU GPL v2 as part of this modified OpenTTD distribution.
EOF

# Licensing files are part of the release contract; fail the build rather than
# silently ship an incomplete legal bundle.
test -s dist/NOTICE.txt
test -s dist/SOURCE_CODE.txt
test -s dist/licenses/OpenTTD/COPYING.md
test -n "$(find dist/licenses/OpenGFX -type f -print -quit)"
test -n "$(find dist/licenses/OpenSFX -type f -print -quit)"
test -n "$(find dist/licenses/OpenMSX -type f -print -quit)"

echo 'Release license/source bundle packaged:'
find dist/licenses -maxdepth 2 -type f -print | sort
