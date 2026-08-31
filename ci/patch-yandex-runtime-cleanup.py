#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path('openttd')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'Could not patch {label}')
    return text.replace(old, new, 1)


def patch_source():
    shell = ROOT / 'os/emscripten/shell.html'
    text = shell.read_text()

    # The platform build has Yandex Player cloud backup, so the stock red
    # IndexedDB warning is both misleading and visually inappropriate.
    text, count = re.subn(
        r'\n\s*<div class="overlay" id="overlay">\s*<div id="filesystem">.*?</div>\s*</div>',
        '',
        text,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise SystemExit('Could not remove Emscripten IndexedDB warning banner')

    text = text.replace(' oncontextmenu="event.preventDefault()"', '')

    old_warning = '''        onWarningFs: function() {
          document.getElementById("filesystem").style.display = "inline-block";
          document.getElementById("overlay").style.opacity = 1;
          setTimeout(function() {
            document.getElementById("overlay").style.opacity = 0;
            setTimeout(function() {
              document.getElementById("filesystem").style.display = "none";
            }, 300);
          }, 10000);
        }
'''
    new_warning = '''        onWarningFs: function() {
          /* Yandex edition: local persistence is backed up through Yandex Player. */
        }
'''
    text = replace_once(text, old_warning, new_warning, 'filesystem warning handler')

    # Replace the removed inline canvas handler with a normal listener; after
    # packaging this script is external, which is compatible with Yandex CSP.
    old_canvas = '''          var canvas = document.getElementById('canvas');

          // As a default initial behavior, pop up an alert when webgl context is lost.'''
    new_canvas = '''          var canvas = document.getElementById('canvas');
          canvas.addEventListener("contextmenu", function(e) { e.preventDefault(); }, false);

          // As a default initial behavior, pop up an alert when webgl context is lost.'''
    text = replace_once(text, old_canvas, new_canvas, 'canvas context-menu handler')
    shell.write_text(text)

    print('Yandex runtime source cleanup applied.')


def patch_pre():
    path = ROOT / 'os/emscripten/pre.js'
    text = path.read_text()

    # Emscripten IDBFS warns when multiple FS.syncfs() calls overlap. OpenTTD
    # can request persistence several times in quick succession, so serialize
    # them and coalesce calls that arrive while a flush is in progress.
    pattern = re.compile(
        r'''    window\.openttd_syncfs_shown_warning = false;\n'''
        r'''    window\.openttd_syncfs = function\(callback\) \{.*?\n    \}\n\n'''
        r'''    const openttd_local_syncfs = window\.openttd_syncfs;''',
        re.S,
    )
    replacement = '''    let openttd_syncfs_busy = false;
    let openttd_syncfs_pending = false;
    let openttd_syncfs_callbacks = [];

    function openttd_run_syncfs() {
        if (openttd_syncfs_busy) {
            openttd_syncfs_pending = true;
            return;
        }

        openttd_syncfs_busy = true;
        openttd_syncfs_pending = false;
        const callbacks = openttd_syncfs_callbacks;
        openttd_syncfs_callbacks = [];

        FS.syncfs(false, function (err) {
            if (err) console.warn('OpenTTD persistent save sync failed', err);
            openttd_syncfs_busy = false;

            for (const callback of callbacks) {
                try { callback(); } catch (e) { console.warn('OpenTTD sync callback failed', e); }
            }

            if (openttd_syncfs_pending || openttd_syncfs_callbacks.length !== 0) {
                openttd_run_syncfs();
            }
        });
    }

    window.openttd_syncfs = function(callback) {
        if (callback) openttd_syncfs_callbacks.push(callback);
        if (openttd_syncfs_busy) {
            openttd_syncfs_pending = true;
            return;
        }
        openttd_run_syncfs();
    }

    const openttd_local_syncfs = window.openttd_syncfs;'''
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise SystemExit('Could not serialize OpenTTD IDBFS sync operations')

    # Old local/cloud configuration from development builds may request AI
    # competitors even though no downloadable AI modules exist in this strictly
    # offline edition. Force the setting to zero before OpenTTD reads the config.
    old_release = '''            const releaseStartup = function() {
                Module.removeRunDependency('syncfs');
            };'''
    new_release = '''            const sanitizeYandexConfig = function() {
                try {
                    const configPath = personal_dir + '/openttd.cfg';
                    let config = '';
                    try { config = FS.readFile(configPath, { encoding: 'utf8' }); } catch (e) {}
                    if (/^max_no_competitors\\s*=.*$/m.test(config)) {
                        config = config.replace(/^max_no_competitors\\s*=.*$/m, 'max_no_competitors = 0');
                    } else if (/^\\[difficulty\\]\\s*$/m.test(config)) {
                        config = config.replace(/^\\[difficulty\\]\\s*$/m, '[difficulty]\\nmax_no_competitors = 0');
                    } else {
                        config += (config.length === 0 || config.endsWith('\\n') ? '' : '\\n') + '[difficulty]\\nmax_no_competitors = 0\\n';
                    }
                    FS.writeFile(configPath, config);
                } catch (e) {
                    console.warn('Could not enforce offline AI settings', e);
                }
            };
            const releaseStartup = function() {
                sanitizeYandexConfig();
                Module.removeRunDependency('syncfs');
            };'''
    text = replace_once(text, old_release, new_release, 'offline AI startup config')

    path.write_text(text)
    print('Yandex pre.js sync/config cleanup applied.')


def patch_bridge():
    path = Path('ci/yandex-bridge.js')
    text = path.read_text()

    old_read = '''  function readConfig(FS, personalDir) {
    try {
      return FS.readFile(personalDir + '/openttd.cfg', { encoding: 'utf8' });
    } catch (e) {
      return '';
    }
  }
'''
    new_read = '''  function sanitizeOfflineConfig(config) {
    config = String(config || '');
    if (/^max_no_competitors\\s*=.*$/m.test(config)) {
      return config.replace(/^max_no_competitors\\s*=.*$/m, 'max_no_competitors = 0');
    }
    if (/^\\[difficulty\\]\\s*$/m.test(config)) {
      return config.replace(/^\\[difficulty\\]\\s*$/m, '[difficulty]\\nmax_no_competitors = 0');
    }
    return config + (config.length === 0 || config.endsWith('\\n') ? '' : '\\n') + '[difficulty]\\nmax_no_competitors = 0\\n';
  }

  function readConfig(FS, personalDir) {
    try {
      return sanitizeOfflineConfig(FS.readFile(personalDir + '/openttd.cfg', { encoding: 'utf8' }));
    } catch (e) {
      return sanitizeOfflineConfig('');
    }
  }
'''
    text = replace_once(text, old_read, new_read, 'cloud config sanitizer')

    old_write = '''      try { FS.writeFile(configPath, cloudConfig.config); } catch (e) {}'''
    new_write = '''      try { FS.writeFile(configPath, sanitizeOfflineConfig(cloudConfig.config)); } catch (e) {}'''
    text = replace_once(text, old_write, new_write, 'cloud config restore sanitizer')

    path.write_text(text)
    print('Yandex bridge config cleanup applied.')


def patch_dist():
    dist = Path('dist')
    path = dist / 'index.html'
    html = path.read_text()

    # Defensive removal in case the upstream shell changes around the source
    # patch. The final page must not show the stock IndexedDB warning.
    html = re.sub(
        r'\n\s*<div class="overlay" id="overlay">\s*<div id="filesystem">.*?</div>\s*</div>',
        '',
        html,
        count=1,
        flags=re.S,
    )

    # Yandex serves the game under a nonce-based CSP. With a nonce/hash present,
    # `unsafe-inline` does not authorize arbitrary inline scripts. Preserve exact
    # execution order by extracting every inline script to a same-origin file at
    # the same DOM position. SINGLE_FILE still embeds WASM/assets in the large
    # runtime JS file, so file:// launch remains self-contained and needs no HTTP
    # server.
    script_re = re.compile(r'<script\b([^>]*)>(.*?)</script>', re.I | re.S)
    index = 0
    generated = []

    def externalize(match):
        nonlocal index
        attrs = match.group(1) or ''
        body = match.group(2) or ''
        if re.search(r'\bsrc\s*=', attrs, re.I):
            return match.group(0)
        if not body.strip():
            return match.group(0)

        if 'yandexGamesSDKReady' in body and 'YaGames.init' in body:
            name = 'yandex-bootstrap.js'
        elif 'CLOUD_CONFIG_KEY' in body and 'yandexGameSetGameplay' in body:
            name = 'yandex-bridge.js'
        elif len(body) > 1_000_000:
            name = 'openttd-runtime.js'
        else:
            name = f'openttd-shell-{index}.js'

        # Guarantee unique names if upstream adds another matching block.
        candidate = name
        suffix = 1
        while candidate in generated:
            stem, dot, ext = name.partition('.')
            candidate = f'{stem}-{suffix}.{ext}' if dot else f'{name}-{suffix}'
            suffix += 1
        name = candidate
        generated.append(name)
        (dist / name).write_text(body)
        index += 1

        kept_attrs = re.sub(r'\s*nonce\s*=\s*(["\']).*?\1', '', attrs, flags=re.I | re.S).strip()
        kept_attrs = (' ' + kept_attrs) if kept_attrs else ''
        return f'<script{kept_attrs} src="{name}"></script>'

    html = script_re.sub(externalize, html)
    path.write_text(html)

    if not generated:
        raise SystemExit('No inline scripts were externalized')

    remaining_inline = []
    for match in script_re.finditer(html):
        attrs = match.group(1) or ''
        if not re.search(r'\bsrc\s*=', attrs, re.I) and (match.group(2) or '').strip():
            remaining_inline.append(match.group(0)[:120])
    if remaining_inline:
        raise SystemExit(f'Inline scripts remain after CSP packaging: {remaining_inline[:2]}')

    handlers = re.findall(r'\son[a-zA-Z]+\s*=\s*(["\']).*?\1', html, flags=re.S)
    if handlers:
        raise SystemExit('Inline event handlers remain after CSP packaging')

    if 'Warning: savegames are stored in the Indexed DB' in html:
        raise SystemExit('IndexedDB warning banner text is still present')

    for name in generated:
        if not (dist / name).is_file() or (dist / name).stat().st_size == 0:
            raise SystemExit(f'Generated CSP script is missing/empty: {name}')

    print('Yandex CSP packaging complete:', ', '.join(generated))


if len(sys.argv) != 2 or sys.argv[1] not in {'source', 'pre', 'bridge', 'dist'}:
    raise SystemExit('usage: patch-yandex-runtime-cleanup.py source|pre|bridge|dist')

mode = sys.argv[1]
if mode == 'source':
    patch_source()
elif mode == 'pre':
    patch_pre()
elif mode == 'bridge':
    patch_bridge()
else:
    patch_dist()
