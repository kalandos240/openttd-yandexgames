#!/usr/bin/env bash
set -euo pipefail

# Direct-file variant of the Yandex/OpenTTD build.
# - all Emscripten resources are embedded, so index.html works via file://
# - OpenSFX uses SDL2 audio
# - OpenMSX MIDI tracks are rendered to compact MP3 files at build time and
#   played by a small Emscripten/HTMLAudio music driver
# - the upstream survey prompt is pre-answered with "No"
cp ci/build-final.sh /tmp/build-direct-file-base.sh

python3 - <<'PY'
from pathlib import Path
p = Path('/tmp/build-direct-file-base.sh')
s = p.read_text()

# Tools used only while building the browser soundtrack.
old_apt = 'apt-get install -y --no-install-recommends git gcc-12 g++-12 zip unzip curl ca-certificates\n'
new_apt = 'apt-get install -y --no-install-recommends git gcc-12 g++-12 zip unzip curl ca-certificates fluidsynth fluid-soundfont-gm ffmpeg\n'
if old_apt not in s:
    raise SystemExit('Could not find apt package line')
s = s.replace(old_apt, new_apt, 1)

# Add a browser music driver to the temporary OpenTTD source checkout.
clone_marker = 'cp openttd/os/emscripten/ports/liblzma.py /emsdk/upstream/emscripten/tools/ports/contrib/\n'
driver_hook = r'''cp openttd/os/emscripten/ports/liblzma.py /emsdk/upstream/emscripten/tools/ports/contrib/

cat > openttd/src/music/webaudio_m.h <<'EOF_WEBMUSIC_H'
/* Browser music driver for the Yandex Games WebAssembly port. */
#ifndef MUSIC_WEBAUDIO_H
#define MUSIC_WEBAUDIO_H

#include "music_driver.hpp"

class MusicDriver_WebAudio : public MusicDriver {
public:
    std::optional<std::string_view> Start(const StringList &) override;
    void Stop() override;
    void PlaySong(const MusicSongInfo &song) override;
    void StopSong() override;
    bool IsSongPlaying() override;
    void SetVolume(uint8_t vol) override;
    std::string_view GetName() const override { return "webaudio"; }
};

class FMusicDriver_WebAudio : public DriverFactoryBase {
public:
    FMusicDriver_WebAudio() : DriverFactoryBase(Driver::DT_MUSIC, 10, "webaudio", "Browser WebAudio Music Driver") {}
    std::unique_ptr<Driver> CreateInstance() const override { return std::make_unique<MusicDriver_WebAudio>(); }
};

#endif
EOF_WEBMUSIC_H

cat > openttd/src/music/webaudio_m.cpp <<'EOF_WEBMUSIC_CPP'
/* Browser music driver for the Yandex Games WebAssembly port. */
#include "../stdafx.h"
#include "../base_media_music.h"
#include "webaudio_m.h"
#include <emscripten.h>

#include "../safeguards.h"

static FMusicDriver_WebAudio iFMusicDriver_WebAudio;

static std::string BrowserMusicPath(const MusicSongInfo &song)
{
    std::string filename = song.filename;
    const size_t slash = filename.find_last_of("/\\");
    if (slash != std::string::npos) filename.erase(0, slash + 1);
    const size_t dot = filename.find_last_of('.');
    if (dot != std::string::npos) filename.erase(dot);
    return "/baseset/" + filename + ".mp3";
}

std::optional<std::string_view> MusicDriver_WebAudio::Start(const StringList &)
{
    EM_ASM({
        if (!Module.openTTDWebMusic) {
            Module.openTTDWebMusic = {
                audio: null,
                url: null,
                volume: 1,
                pending: false,
                generation: 0
            };
        }
    });
    return std::nullopt;
}

void MusicDriver_WebAudio::Stop()
{
    this->StopSong();
}

void MusicDriver_WebAudio::PlaySong(const MusicSongInfo &song)
{
    const std::string path = BrowserMusicPath(song);
    const int loop = song.loop ? 1 : 0;

    EM_ASM({
        const path = UTF8ToString($0);
        const loop = !!$1;
        const state = Module.openTTDWebMusic || (Module.openTTDWebMusic = {
            audio: null, url: null, volume: 1, pending: false, generation: 0
        });

        state.generation++;
        const generation = state.generation;

        if (state.audio) {
            try { state.audio.pause(); } catch (e) {}
            state.audio.src = '';
            state.audio = null;
        }
        if (state.url) {
            try { URL.revokeObjectURL(state.url); } catch (e) {}
            state.url = null;
        }

        let data;
        try {
            data = FS.readFile(path);
        } catch (e) {
            console.warn('OpenTTD browser music: missing rendered track', path, e);
            state.pending = false;
            return;
        }

        /* Copy out of wasm-backed memory before creating the Blob. */
        const bytes = new Uint8Array(data.length);
        bytes.set(data);
        state.url = URL.createObjectURL(new Blob([bytes], { type: 'audio/mpeg' }));

        const audio = new Audio();
        state.audio = audio;
        audio.preload = 'auto';
        audio.src = state.url;
        audio.loop = loop;
        audio.volume = state.volume;
        state.pending = true;

        audio.addEventListener('ended', function() {
            if (state.generation === generation) state.pending = false;
        });

        const attemptPlay = function() {
            if (state.generation !== generation || state.audio !== audio) return;
            let result;
            try {
                result = audio.play();
            } catch (e) {
                return;
            }
            if (result && typeof result.then === 'function') {
                result.then(function() {
                    if (state.generation === generation) state.pending = false;
                }).catch(function() {
                    /* Browser autoplay policy: the one-shot listeners below
                     * will retry after the first real user gesture. */
                });
            } else {
                state.pending = false;
            }
        };

        const resumeAfterGesture = function() {
            attemptPlay();
        };
        document.addEventListener('pointerdown', resumeAfterGesture, { once: true, capture: true });
        document.addEventListener('keydown', resumeAfterGesture, { once: true, capture: true });
        document.addEventListener('touchstart', resumeAfterGesture, { once: true, capture: true });
        attemptPlay();
    }, path.c_str(), loop);
}

void MusicDriver_WebAudio::StopSong()
{
    EM_ASM({
        const state = Module.openTTDWebMusic;
        if (!state) return;
        state.generation++;
        state.pending = false;
        if (state.audio) {
            try { state.audio.pause(); } catch (e) {}
            state.audio.src = '';
            state.audio = null;
        }
        if (state.url) {
            try { URL.revokeObjectURL(state.url); } catch (e) {}
            state.url = null;
        }
    });
}

bool MusicDriver_WebAudio::IsSongPlaying()
{
    return EM_ASM_INT({
        const state = Module.openTTDWebMusic;
        if (!state || !state.audio) return 0;
        /* While waiting for the first user gesture, keep OpenTTD on the same
         * track instead of rapidly advancing the playlist. */
        if (state.pending) return 1;
        return state.audio.ended ? 0 : 1;
    }) != 0;
}

void MusicDriver_WebAudio::SetVolume(uint8_t vol)
{
    EM_ASM({
        const state = Module.openTTDWebMusic || (Module.openTTDWebMusic = {
            audio: null, url: null, volume: 1, pending: false, generation: 0
        });
        state.volume = Math.max(0, Math.min(1, $0 / 127.0));
        if (state.audio) state.audio.volume = state.volume;
    }, static_cast<int>(vol));
}
EOF_WEBMUSIC_CPP

cat >> openttd/src/music/CMakeLists.txt <<'EOF_WEBMUSIC_CMAKE'

if(EMSCRIPTEN)
    add_files(
        webaudio_m.cpp
        webaudio_m.h
    )
endif()
EOF_WEBMUSIC_CMAKE
'''
if clone_marker not in s:
    raise SystemExit('Could not find liblzma copy marker')
s = s.replace(clone_marker, driver_hook, 1)

# Extend the Python patch that build-final.sh applies to OpenTTD's CMake.
needle = "cmake.write_text(s)\n"
patch = r'''# Direct-file build: embed all files and the WebAssembly binary.
s = s.replace('--preload-file', '--embed-file')
wasm_marker = '    target_link_libraries(WASM::WASM INTERFACE "-s WASM_BIGINT")\n'
single_file = '    target_link_libraries(WASM::WASM INTERFACE "-s SINGLE_FILE=1")\n'
if single_file not in s:
    if wasm_marker not in s:
        raise SystemExit('Could not find WASM_BIGINT linker marker')
    s = s.replace(wasm_marker, wasm_marker + single_file, 1)
cmake.write_text(s)
'''
if needle not in s:
    raise SystemExit('Could not patch OpenTTD CMake mutation block')
s = s.replace(needle, patch, 1)

# Patch the generated Emscripten startup code before pre.js is written.
# Enable SDL sound + our browser music driver, suppress the survey prompt,
# and keep direct-file startup usable without IndexedDB.
needle = "pre.write_text(s)\n"
patch = r'''args_old = "Module.arguments.push('-mnull', '-snull', '-vsdl');"
args_new = "Module.arguments.push('-mwebaudio', '-ssdl', '-vsdl');"
if args_old not in s:
    raise SystemExit('Could not find Emscripten null audio arguments')
s = s.replace(args_old, args_new, 1)

survey_dependency = "            Module.removeRunDependency('syncfs');"
survey_lines = [
    "            try {",
    "                const private_path = personal_dir + '/private.cfg';",
    "                let private_config = '';",
    "                try { private_config = FS.readFile(private_path, { encoding: 'utf8' }); } catch (e) {}",
    "                if (/^participate_survey\\s*=.*$/m.test(private_config)) {",
    "                    private_config = private_config.replace(/^participate_survey\\s*=.*$/m, 'participate_survey = no');",
    "                } else if (/^\\[network\\]\\s*$/m.test(private_config)) {",
    "                    private_config = private_config.replace(/^\\[network\\]\\s*$/m, '[network]\\nparticipate_survey = no');",
    "                } else {",
    "                    private_config += (private_config.length === 0 || private_config.endsWith('\\n') ? '' : '\\n') + '[network]\\nparticipate_survey = no\\n';",
    "                }",
    "                FS.writeFile(private_path, private_config);",
    "            } catch (e) { console.warn('Could not disable OpenTTD survey prompt', e); }",
    "",
]
survey_patch = "\n".join(survey_lines)
if survey_dependency not in s:
    raise SystemExit('Could not find startup dependency removal point')
s = s.replace(survey_dependency, survey_patch + survey_dependency, 1)

file_mount = "    FS.mount(IDBFS, {}, personal_dir);\n"
file_mount_replacement = """    if (typeof location !== 'undefined' && location.protocol === 'file:') {
        console.warn('OpenTTD direct-file mode: IndexedDB persistence is disabled for this local launch.');
    } else {
        FS.mount(IDBFS, {}, personal_dir);
    }
"""
if file_mount not in s:
    raise SystemExit('Could not find IDBFS mount line')
s = s.replace(file_mount, file_mount_replacement, 1)
pre.write_text(s)
'''
if needle not in s:
    raise SystemExit('Could not patch OpenTTD pre.js mutation block')
s = s.replace(needle, patch, 1)

# Render OpenMSX MIDI files to compact browser-playable MP3 tracks. The
# original OpenMSX tar stays bundled too, so OpenTTD still validates and
# exposes the proper soundtrack/metadata in its normal music UI.
asset_marker = "echo 'Bundled base-set files:'\n"
render_hook = r'''echo 'Rendering OpenMSX MIDI soundtrack for browser playback...'
OPENMSX_TAR="$(find /tmp/ottd-assets/openmsx -type f -name '*.tar' -print -quit)"
test -n "${OPENMSX_TAR}"
rm -rf /tmp/openmsx-render
mkdir -p /tmp/openmsx-render/src /tmp/openmsx-render/wav
tar -xf "${OPENMSX_TAR}" -C /tmp/openmsx-render/src
SOUNDFONT="$(find /usr/share/sounds -type f -iname '*.sf2' -print -quit)"
test -n "${SOUNDFONT}"
rendered=0
while IFS= read -r midi; do
    base="$(basename "${midi}")"
    stem="${base%.*}"
    wav="/tmp/openmsx-render/wav/${stem}.wav"
    mp3="openttd/build/yandex_baseset/${stem}.mp3"
    fluidsynth -ni -r 22050 -F "${wav}" "${SOUNDFONT}" "${midi}" >/dev/null 2>&1
    ffmpeg -loglevel error -y -i "${wav}" -ar 32000 -ac 2 -codec:a libmp3lame -b:a 48k "${mp3}"
    rm -f "${wav}"
    rendered=$((rendered + 1))
done < <(find /tmp/openmsx-render/src -type f \( -iname '*.mid' -o -iname '*.midi' \) | sort)
echo "Rendered OpenMSX tracks: ${rendered}"
test "${rendered}" -ge 31

'''
if asset_marker not in s:
    raise SystemExit('Could not find base-set listing marker')
s = s.replace(asset_marker, render_hook + asset_marker, 1)

# SINGLE_FILE + --embed-file intentionally produce no external .wasm/.data.
s = s.replace('cp openttd/build/openttd.wasm dist/\n', '')
s = s.replace('cp openttd/build/openttd.data dist/\n', '')
s = s.replace('cp openttd/build/openttd.js dist/\n', '[ ! -f openttd/build/openttd.js ] || cp openttd/build/openttd.js dist/\n')

marker = "cat > dist/NOTICE.txt <<'EOF'\n"
checks = '''test -f dist/index.html\ntest ! -e dist/openttd.wasm\ntest ! -e dist/openttd.data\n\n'''
if marker not in s:
    raise SystemExit('Could not find NOTICE marker')
s = s.replace(marker, checks + marker, 1)

# Update release notes inside the package.
s = s.replace(
    'Bundled free base sets: OpenGFX 8.0, OpenSFX 1.0.3, OpenMSX 0.4.2.',
    'Bundled free base sets: OpenGFX 8.0, OpenSFX 1.0.3, OpenMSX 0.4.2. OpenMSX is rendered to MP3 at build time for browser playback.'
)
s = s.replace('openttd-yandexgames.zip', 'OpenTTD-YandexGames-Direct.zip')
p.write_text(s)
PY

# Preserve Cyrillic/TrueType support.
echo 'Preparing Emscripten FreeType for Russian/Cyrillic text...'
embuilder build freetype

bash /tmp/build-direct-file-base.sh
