#!/usr/bin/env python3
"""Make the initial browser filesystem/cloud startup dependency fail-open.

The watchdog is independent from the obsolete offline-AI config sanitizer. It
patches the generated pre.js startup dependency directly, so removing the old
max_no_competitors=0 rewrite cannot break cold-start protection.
"""
from pathlib import Path

cleanup_path = Path('ci/patch-yandex-runtime-cleanup.py')
if not cleanup_path.is_file():
    raise SystemExit('Legacy runtime-cleanup generator is missing')

text = cleanup_path.read_text(encoding='utf-8')

serialize_anchor = """    if count != 1:\n        raise SystemExit('Could not serialize OpenTTD IDBFS sync operations')\n\n"""
if text.count(serialize_anchor) != 1:
    raise SystemExit('Could not find runtime-cleanup IDBFS serialization anchor')

# Insert both generator rewrites next to the stable IDBFS serialization patch.
# Do not depend on the removed "offline AI startup config" generator block.
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

    release_old = "                Module.removeRunDependency('syncfs');"
    release_new = """                clearTimeout(browser_startup_watchdog);
                browser_release_startup_dependency();"""
    text = replace_once(text, release_old, release_new, 'guarded startup dependency release')

'''
text = text.replace(serialize_anchor, serialize_anchor + watchdog_generator, 1)

cleanup_path.write_text(text, encoding='utf-8')
print('Cold-start watchdog wired into generated Emscripten pre.js without legacy AI sanitizer dependency.')
