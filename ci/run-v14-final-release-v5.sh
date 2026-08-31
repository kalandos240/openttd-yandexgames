#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${NATIVE_ARTIFACT_ID:=9746240087}"
: "${NATIVE_BUILD_RUN:=33358837803}"
: "${NATIVE_BUILD_SHA:=6a5f09490f97b6066d520fa058dcceb6ec1cf2b2}"
: "${AI_SOURCE_SHA:=6941b25d1dfaf941a66d38430632f850b78c54a1}"
: "${NATIVE_ARTIFACT_DIGEST:=sha256:ff29325bd343f94946e3e0becbcc8611f122ba81bdb153b697e7d2bf9169ef87}"
: "${VERIFIED_YA_ARTIFACT_ID:=9738530154}"
: "${VERIFIED_PG_ARTIFACT_ID:=9738530460}"

ROOT=/tmp/v14v5
rm -rf "$ROOT"
mkdir -p "$ROOT"/{artifact/native,artifact/ya,artifact/pg,native,baseline/ya,baseline/pg,prod/ya,prod/pg,test/ya,test/pg,out,browser-node}

download_artifact() {
  local id="$1" output="$2"
  curl -fL --retry 5 --retry-all-errors \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/artifacts/${id}/zip" \
    -o "$output"
}

echo '== Download exact native runtime and verified platform baselines =='
download_artifact "$NATIVE_ARTIFACT_ID" "$ROOT/native-artifact.zip"
download_artifact "$VERIFIED_YA_ARTIFACT_ID" "$ROOT/ya-artifact.zip"
download_artifact "$VERIFIED_PG_ARTIFACT_ID" "$ROOT/pg-artifact.zip"
unzip -q "$ROOT/native-artifact.zip" -d "$ROOT/artifact/native"
unzip -q "$ROOT/ya-artifact.zip" -d "$ROOT/artifact/ya"
unzip -q "$ROOT/pg-artifact.zip" -d "$ROOT/artifact/pg"
NATIVE_ZIP="$(find "$ROOT/artifact/native" -type f -name 'OpenTTD-YandexGames-Direct.zip' -print -quit)"
YA_ZIP="$(find "$ROOT/artifact/ya" -type f -name '*.zip' -print -quit)"
PG_ZIP="$(find "$ROOT/artifact/pg" -type f -name '*.zip' -print -quit)"
test -s "$NATIVE_ZIP"; test -s "$YA_ZIP"; test -s "$PG_ZIP"
unzip -q "$NATIVE_ZIP" -d "$ROOT/native"
unzip -q "$YA_ZIP" -d "$ROOT/baseline/ya"
unzip -q "$PG_ZIP" -d "$ROOT/baseline/pg"
cp -a "$ROOT/baseline/ya/." "$ROOT/prod/ya/"
cp -a "$ROOT/baseline/pg/." "$ROOT/prod/pg/"
test -s "$ROOT/native/openttd-runtime.js"
test ! -e "$ROOT/native/openttd.wasm"
test ! -e "$ROOT/native/openttd.data"
grep -Fq '__openttdDirtyRect' "$ROOT/native/openttd-runtime.js"
grep -Fq '__openttdAIStats' "$ROOT/native/openttd-runtime.js"

echo '== Assemble final Yandex and Playgama packages =='
python3 -m py_compile \
  ci/patch-v14-webgl-runtime.py \
  ci/patch-v14-performance-package.py \
  ci/patch-v14-playgama-single-file.py \
  ci/patch-v14-simpleai-bridge-cache.py \
  yandex/neutralize_yandex_runtime.py
for d in "$ROOT/prod/ya" "$ROOT/prod/pg"; do
  cp "$ROOT/native/openttd-runtime.js" "$d/openttd-runtime.js"
  rm -f "$d/openttd.wasm" "$d/openttd.data"
  python3 ci/patch-v14-webgl-runtime.py "$d/openttd-runtime.js"
  python3 ci/patch-v14-simpleai-bridge-cache.py "$d"
  node --check "$d/openttd-runtime.js"
  node --check "$d/openttd-classic-ai.js"
done
python3 ci/patch-v14-performance-package.py "$ROOT/prod/ya" --platform yandex
python3 ci/patch-v14-playgama-single-file.py "$ROOT/prod/pg"
python3 yandex/neutralize_yandex_runtime.py "$ROOT/prod/ya"

echo '== Static autonomy, feature and platform gates =='
for d in "$ROOT/prod/ya" "$ROOT/prod/pg"; do
  test -s "$d/openttd-runtime.js"
  test -s "$d/openttd-classic-ai.js"
  test ! -e "$d/openttd.wasm"
  test ! -e "$d/openttd.data"
  node --check "$d/openttd-runtime.js"
  node --check "$d/openttd-classic-ai.js"
  grep -Fq '__openttdWebGLPresenter' "$d/openttd-runtime.js"
  grep -Fq '__openttdDirtyRect' "$d/openttd-runtime.js"
  grep -Fq '__openttdUploadStats' "$d/openttd-runtime.js"
  grep -Fq '__openttdAIStats' "$d/openttd-runtime.js"
  grep -Fq 'texSubImage2D' "$d/openttd-runtime.js"
  grep -Fq 'bridge-type-cache-per-game-date-2026-08-31' "$d/openttd-classic-ai.js"
  grep -Fq 'web_payload_md5' "$d/openttd-classic-ai.js"
  grep -Fq 'const MAX_SCORE = 1000' "$d/openttd-global-ranking.js"
  grep -Fq 'Module.calledRun === true' "$d/openttd-ranking-core.js"
done

grep -Fq "script.src = '/sdk.js'" "$ROOT/prod/ya/yandex-bootstrap.js"
test -s "$ROOT/prod/ya/THIRD-PARTY-LICENSES.md"
test ! -e "$ROOT/prod/ya/PLAYGAMA-ALL-LICENSES.md"
! grep -Eiq 'playgama' "$ROOT/prod/ya/openttd-bundled-addons.js"
! grep -Eiq 'https?://' "$ROOT/prod/ya/OPENTTD-BUNDLED-ADDONS.json"
! grep -Eiq 'https?://[^"[:space:]]+' "$ROOT/prod/ya/index.html"
! grep -Fq 'bridge.playgama.com' "$ROOT/prod/pg/index.html"
grep -Fq 'https://bridge.playgama.com/v1.31.0/playgama-bridge.js' "$ROOT/prod/pg/platform-bridge-loader.js"
grep -Fq 'window.__openttdPlatformStartupIndependent===true' "$ROOT/prod/pg/openttd-runtime.js"
python3 - <<'PY'
from pathlib import Path
p = Path('/tmp/v14v5/prod/pg/index.html')
s = p.read_text(encoding='utf-8')
cloud = 'openttd-playgama-cloud-saves.js'
fixes = 'openttd-playgama-fixes.js'
addons = 'openttd-bundled-addons.js'
assert s.count(cloud) == s.count(fixes) == s.count(addons) == 1
assert s.index(cloud) < s.index(fixes) < s.index(addons), 'Playgama AI restore hook order regressed'
print('Playgama restore order:', s.index(cloud), s.index(fixes), s.index(addons))
PY

echo '== Build final candidate ZIPs and provenance =='
(cd "$ROOT/prod/ya" && zip -q -r -9 "$ROOT/out/openttd-yandexgames-v14-final.zip" .)
(cd "$ROOT/prod/pg" && zip -q -r -9 "$ROOT/out/openttd-playgama-v14-final.zip" .)
unzip -tq "$ROOT/out/openttd-yandexgames-v14-final.zip"
unzip -tq "$ROOT/out/openttd-playgama-v14-final.zip"
(
  cd "$ROOT/out"
  sha256sum openttd-yandexgames-v14-final.zip openttd-playgama-v14-final.zip > SHA256SUMS.txt
)
cat > "$ROOT/out/BUILD-PROVENANCE.txt" <<EOF
OpenTTD v14 final web release v5
Native build run: ${NATIVE_BUILD_RUN}
Native build SHA: ${NATIVE_BUILD_SHA}
AI source-pipeline SHA: ${AI_SOURCE_SHA}
Native artifact ID: ${NATIVE_ARTIFACT_ID}
Native artifact API digest: ${NATIVE_ARTIFACT_DIGEST}
Verified Yandex platform base artifact: ${VERIFIED_YA_ARTIFACT_ID}
Verified Playgama platform base artifact: ${VERIFIED_PG_ARTIFACT_ID}
Final package branch SHA: ${GITHUB_SHA}
Release gate: exact 4096x4096 world, max_no_competitors=14, competitors_interval=0, 30-second post-generation sample on both platforms.
AI gate: 14 active competitors, scaled aggregate opcode budget, complete 15 -> 1.2 compatibility chain, no dummy/no-suitable/script-died diagnostics.
Renderer gate: WebGL framebuffer presenter active with dirty-rect partial uploads observed.
Autonomy gate: all OpenTTD game assets local; Yandex keeps only relative /sdk.js; Playgama Bridge is optional/non-blocking and pinned in platform-bridge-loader.js.
EOF

echo '== Prepare isolated browser tests =='
cp -a "$ROOT/prod/ya/." "$ROOT/test/ya/"
cp -a "$ROOT/prod/pg/." "$ROOT/test/pg/"
cp ci/v14-yandex-sdk-mock.js "$ROOT/test/ya/sdk.js"
cp ci/v14-playgama-loader-mock.js "$ROOT/test/pg/platform-bridge-loader.js"

echo '== Install Chromium controller =='
export CHROME_BIN="$(command -v google-chrome || command -v google-chrome-stable || command -v chromium)"
test -n "$CHROME_BIN"
cd "$ROOT/browser-node"
npm init -y >/dev/null 2>&1
npm install --no-audit --no-fund puppeteer-core@24.16.0
cp "$GITHUB_WORKSPACE/ci/platform-hosted-smoke.mjs" ./smoke.mjs
cp "$GITHUB_WORKSPACE/ci/v14-performance-browser.mjs" ./perf.mjs
cp "$GITHUB_WORKSPACE/ci/v14-viewport-smoke.mjs" ./viewport.mjs
node --check ./smoke.mjs
node --check ./perf.mjs
node --check ./viewport.mjs
grep -Fq 'protocolTimeout: 900000' ./perf.mjs
grep -Fq "mapLog2 >= 12 ? 'during' : 'after'" ./perf.mjs
grep -Fq "document.activeElement === canvas" ./perf.mjs
grep -Fq 'mainThreadProbeBlockedMs: mainThreadBlockedMs' ./perf.mjs

run_smoke_viewport() {
  local dir="$1" platform="$2" port="$3"
  cd "$dir"
  python3 -m http.server "$port" --bind 127.0.0.1 >"$ROOT/${platform}-${port}.http.log" 2>&1 &
  local pid=$!
  for _ in $(seq 1 100); do curl -fsS "http://127.0.0.1:${port}/index.html" >/dev/null && break; sleep 0.1; done
  cd "$ROOT/browser-node"
  node smoke.mjs "$platform" "http://127.0.0.1:${port}/index.html" "$ROOT/out/${platform}-smoke.json"
  node viewport.mjs "$platform" "http://127.0.0.1:${port}/index.html" "$ROOT/out/viewport-${platform}"
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}

echo '== Hosted Chromium smoke and viewport gates =='
run_smoke_viewport "$ROOT/test/ya" yandex 8553
run_smoke_viewport "$ROOT/test/pg" playgama 8554
grep -Fq '"passed": true' "$ROOT/out/yandex-smoke.json"
grep -Fq '"passed": true' "$ROOT/out/playgama-smoke.json"
grep -Fq '"passed": true' "$ROOT/out/viewport-yandex/yandex-viewport.json"
grep -Fq '"passed": true' "$ROOT/out/viewport-playgama/playgama-viewport.json"

run_stress() {
  local dir="$1" platform="$2" port="$3"
  cd "$dir"
  python3 -m http.server "$port" --bind 127.0.0.1 >"$ROOT/stress-${platform}.http.log" 2>&1 &
  local pid=$!
  for _ in $(seq 1 100); do curl -fsS "http://127.0.0.1:${port}/index.html" >/dev/null && break; sleep 0.1; done
  cd "$ROOT/browser-node"
  set +e
  node perf.mjs "$platform" "http://127.0.0.1:${port}/index.html" "$ROOT/out/stress-final-${platform}.json" optimized 12 30000 during
  local rc=$?
  set -e
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  return "$rc"
}

echo '== Exact 4096x4096 + 14 SimpleAI Yandex stress =='
run_stress "$ROOT/test/ya" yandex 8570

echo '== Exact 4096x4096 + 14 SimpleAI Playgama stress =='
run_stress "$ROOT/test/pg" playgama 8571

echo '== Validate stress evidence and create final report =='
python3 - <<'PY'
import json, re
from pathlib import Path
out = Path('/tmp/v14v5/out')
report = {
    'release': 'OpenTTD v14 final web release v5',
    'methodology': 'Exact 4096x4096 newgame with max_no_competitors=14, competitors_interval=0, then 30-second post-generation sample.',
    'native_build_run': 33358837803,
    'native_build_sha': '6a5f09490f97b6066d520fa058dcceb6ec1cf2b2',
    'ai_source_sha': '6941b25d1dfaf941a66d38430632f850b78c54a1',
    'native_artifact_id': 9746240087,
    'native_artifact_digest': 'sha256:ff29325bd343f94946e3e0becbcc8611f122ba81bdb153b697e7d2bf9169ef87',
    'platforms': {},
}
bad = re.compile(r'(script died|no suitable ai found|dummy ai|AI[^\n]{0,40}crash|squirrel[^\n]{0,40}error|fatal error|runtimeerror|uncaught)', re.I)
compat = re.compile(r'AI compatibility chain 15 -> 1\.2 installed \(13 scripts\)', re.I)
for platform in ('yandex', 'playgama'):
    path = out / f'stress-final-{platform}.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    if not data.get('passed'):
        raise SystemExit(f'{platform}: stress failed: {data.get("failure")}')
    if data.get('map', {}).get('width') != 4096 or data.get('map', {}).get('height') != 4096:
        raise SystemExit(f'{platform}: map size is not 4096x4096')
    if data.get('aiMode') != 'during':
        raise SystemExit(f'{platform}: stress did not use during-generation AI mode')
    scheduler = data.get('aiScheduler') or {}
    renderer = data.get('renderer') or {}
    upload = renderer.get('upload') or {}
    if scheduler.get('activeAI') != 14:
        raise SystemExit(f'{platform}: expected 14 active AI, got {scheduler}')
    if not (0 < scheduler.get('effectiveOpcodeBudget', 0) < scheduler.get('configuredOpcodeBudget', 0)):
        raise SystemExit(f'{platform}: invalid scaled AI budget: {scheduler}')
    if not renderer.get('active') or upload.get('partialUploads', 0) < 1:
        raise SystemExit(f'{platform}: dirty-rect WebGL evidence missing: {renderer}')
    if (data.get('network') or {}).get('blockedExternal'):
        raise SystemExit(f'{platform}: unexpected external runtime requests: {data["network"]["blockedExternal"][:10]}')
    console = '\n'.join((data.get('console') or {}).get('tail') or [])
    if bad.search(console):
        raise SystemExit(f'{platform}: dummy/dead/crashed AI or runtime error found in console')
    if not compat.search(console):
        raise SystemExit(f'{platform}: complete SimpleAI compatibility chain was not observed')
    snap = data['ai14']['snapshot']
    report['platforms'][platform] = {
        'generation4096Ms': data['generation']['wallMsUntilResponsive'],
        'mainThreadGenerationBlockMs': data['generation']['mainThreadProbeBlockedMs'],
        'estimatedFps': snap['estimatedFps'],
        'p50FrameGapMs': snap['p50FrameGapMs'],
        'p95FrameGapMs': snap['p95FrameGapMs'],
        'p99FrameGapMs': snap['p99FrameGapMs'],
        'maxFrameGapMs': snap['maxFrameGapMs'],
        'longTaskCount': snap['longTaskCount'],
        'longestLongTaskMs': snap['longestLongTaskMs'],
        'wasmHeapBytes': snap['wasmHeapBytes'],
        'aiScheduler': scheduler,
        'renderer': renderer,
        'aiCompatibilityChainObserved': True,
        'dummyOrDeadAIObserved': False,
    }
(out / 'FINAL-RELEASE-STRESS.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
lines = [
    '# OpenTTD v14 final release v5', '',
    'Exact 4096x4096 new game, 14 live SimpleAI competitors, interval 0, both platform packages.', '',
]
for platform, d in report['platforms'].items():
    lines += [
        f'## {platform}', '',
        f"Generation to responsive: {d['generation4096Ms']:.0f} ms",
        f"Main-thread generation block: {d['mainThreadGenerationBlockMs']:.0f} ms",
        f"14-AI estimated FPS: {d['estimatedFps']:.2f}",
        f"p95 frame gap: {d['p95FrameGapMs']:.2f} ms",
        f"p99 frame gap: {d['p99FrameGapMs']:.2f} ms",
        f"Longest long task during 30s AI sample: {d['longestLongTaskMs']:.2f} ms",
        'SimpleAI compatibility chain: 13/13 observed',
        'Dummy/dead AI diagnostics: none',
        f"AI scheduler: `{json.dumps(d['aiScheduler'])}`",
        f"Renderer: `{json.dumps(d['renderer'])}`", '',
    ]
(out / 'FINAL-RELEASE-STRESS.md').write_text('\n'.join(lines), encoding='utf-8')
print('\n'.join(lines))
PY

echo '== Final release integrity gate =='
grep -Fq '"passed": true' "$ROOT/out/stress-final-yandex.json"
grep -Fq '"passed": true' "$ROOT/out/stress-final-playgama.json"
grep -Fq '"passed": true' "$ROOT/out/yandex-smoke.json"
grep -Fq '"passed": true' "$ROOT/out/playgama-smoke.json"
grep -Fq '"passed": true' "$ROOT/out/viewport-yandex/yandex-viewport.json"
grep -Fq '"passed": true' "$ROOT/out/viewport-playgama/playgama-viewport.json"
test -s "$ROOT/out/stress-final-yandex-final.png"
test -s "$ROOT/out/stress-final-playgama-final.png"
test -s "$ROOT/out/FINAL-RELEASE-STRESS.json"
test -s "$ROOT/out/FINAL-RELEASE-STRESS.md"
test -s "$ROOT/out/SHA256SUMS.txt"
test -s "$ROOT/out/BUILD-PROVENANCE.txt"
unzip -tq "$ROOT/out/openttd-yandexgames-v14-final.zip"
unzip -tq "$ROOT/out/openttd-playgama-v14-final.zip"
(cd "$ROOT/out" && sha256sum -c SHA256SUMS.txt)
ls -lah "$ROOT/out"

echo 'FINAL_V14_RELEASE_V5_GATE_PASSED'
