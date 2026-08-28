#!/usr/bin/env python3
"""Make the initial browser filesystem/cloud startup dependency fail-open.

The Emscripten main loop must never remain blocked forever if IndexedDB or a
platform storage callback fails to return on a cold browser profile. The legacy
pipeline generates the final pre.js later, so patch that generator here rather
than byte-editing the built runtime.
"""
from pathlib import Path

cleanup_path = Path('ci/patch-yandex-runtime-cleanup.py')
if not cleanup_path.is_file():
    raise SystemExit('Legacy runtime-cleanup generator is missing')

text = cleanup_path.read_text(encoding='utf-8')

serialize_anchor = """    if count != 1:\n        raise SystemExit('Could not serialize OpenTTD IDBFS sync operations')\n\n"""
if text.count(serialize_anchor) != 1:
    raise SystemExit('Could not find runtime-cleanup IDBFS serialization anchor')

watchdog_generator = r'''    startup_old = "    Module.addRunDependency('syncfs');\n    FS.syncfs(true, function (err) {\n"
    startup_new = """    Module.addRunDependency('syncfs');
    let browser_startup_dependency_released = false;
    const browser_release_startup_dependency = function(reason) {
        if (browser_startup_dependency_released) return;
        browser_startup_dependency_released = true;
        if (reason) console.warn('OpenTTD startup watchdog released a stalled startup dependency:', reason);
        Module.removeRunDependency('syncfs');
    };
    const browser_startup_watchdog = setTimeout(function() {
        browser_release_startup_dependency('filesystem/cloud initialization exceeded 8000 ms');
    }, 8000);
    FS.syncfs(true, function (err) {
"""
    text = replace_once(text, startup_old, startup_new, 'cold-start filesystem watchdog')

'''
text = text.replace(serialize_anchor, serialize_anchor + watchdog_generator, 1)

release_anchor = "    text = replace_once(text, old_release, new_release, 'offline AI startup config')\n"
if text.count(release_anchor) != 1:
    raise SystemExit('Could not find generated startup release anchor')

release_generator = r'''
    release_old = "                Module.removeRunDependency('syncfs');"
    release_new = """                clearTimeout(browser_startup_watchdog);
                browser_release_startup_dependency();"""
    text = replace_once(text, release_old, release_new, 'guarded startup dependency release')
'''
text = text.replace(release_anchor, release_anchor + release_generator, 1)

cleanup_path.write_text(text, encoding='utf-8')
print('Cold-start watchdog wired into generated Emscripten pre.js (8 second hard ceiling).')
