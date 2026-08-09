#!/usr/bin/env bash
set -euo pipefail

# Extend the already-tested direct-file/audio build with:
# - a strictly single-player/offline OpenTTD UI/runtime
# - Yandex Games cloud saves, gameplay lifecycle and interstitial ads
#
# We patch the base build script rather than duplicating its large, tested body.
python3 - <<'PY'
from pathlib import Path

p = Path('ci/build-final.sh')
s = p.read_text()

clone_marker = 'cp openttd/os/emscripten/ports/liblzma.py /emsdk/upstream/emscripten/tools/ports/contrib/\n'
source_hook = 'python3 ci/patch-yandex-offline.py source\npython3 ci/repair-yandex-newgrf.py\npython3 ci/patch-yandex-gameplay-state.py\n'
if clone_marker not in s:
    raise SystemExit('Could not find OpenTTD clone/source patch marker')
s = s.replace(clone_marker, clone_marker + source_hook, 1)

host_marker = 'mkdir -p openttd/build-host\n'
pre_hook = 'python3 ci/patch-yandex-offline.py pre\n\n'
if host_marker not in s:
    raise SystemExit('Could not find host build marker')
s = s.replace(host_marker, pre_hook + host_marker, 1)

notice_marker = "cat > dist/NOTICE.txt <<'EOF'\n"
bridge_hook = r'''python3 - <<'PY_YANDEX_BRIDGE'
from pathlib import Path
p = Path('dist/index.html')
html = p.read_text()
bridge = Path('ci/yandex-bridge.js').read_text()
if '</head>' not in html:
    raise SystemExit('No </head> found while injecting Yandex bridge')
html = html.replace('</head>', '<script>\n' + bridge + '\n</script>\n  </head>', 1)
p.write_text(html)
PY_YANDEX_BRIDGE

'''
if notice_marker not in s:
    raise SystemExit('Could not find final HTML/NOTICE marker')
s = s.replace(notice_marker, bridge_hook + notice_marker, 1)

p.write_text(s)
PY

bash ci/build-direct-file.sh
