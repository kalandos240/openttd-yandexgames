#!/usr/bin/env python3
from pathlib import Path
import argparse, re, shutil

ap=argparse.ArgumentParser(); ap.add_argument('root',type=Path); ap.add_argument('--platform',choices=['yandex','playgama']); a=ap.parse_args()
r=a.root.resolve()
platform=a.platform or ('yandex' if (r/'YANDEX-INTEGRATION.txt').is_file() else 'playgama' if (r/'PLAYGAMA-INTEGRATION.txt').is_file() else None)
if platform is None: raise SystemExit('could not detect platform package')
idx=r/'index.html'
if not idx.is_file() or not (r/'openttd-runtime.js').is_file(): raise SystemExit('bad package root')
s=idx.read_text(encoding='utf-8')
tag='<script src="openttd-bundled-addons.js"></script>'
migration_tag='<script src="openttd-vanilla-migration.js"></script>'
if s.count(tag)!=1: raise SystemExit(f'expected one addon script tag, got {s.count(tag)}')
idx.write_text(s.replace(tag,migration_tag,1),encoding='utf-8')

migration=r'''/* Vanilla profile migration: remove NewGRF state left by older bundled-add-on builds.
 * Runs after the final platform/cloud restore wrapper has been installed and before
 * openttd-runtime.js starts main(), so stale IDBFS/cloud config cannot reactivate it. */
(function () {
  'use strict';
  if (window.__openttdVanillaMigrationInstalled) return;
  window.__openttdVanillaMigrationInstalled = true;

  const removeTree = (FS, path) => {
    let entries;
    try { entries = FS.readdir(path); } catch (_) { return false; }
    for (const name of entries) {
      if (name === '.' || name === '..') continue;
      const child = path + '/' + name;
      try {
        const stat = FS.stat(child);
        if (FS.isDir(stat.mode)) removeTree(FS, child);
        else FS.unlink(child);
      } catch (_) {}
    }
    try { FS.rmdir(path); } catch (_) {}
    return true;
  };

  const unlink = (FS, path) => {
    try { FS.unlink(path); return true; } catch (_) { return false; }
  };

  const stripNewGRFSections = (text) => {
    const lines = String(text || '').split(/\r?\n/);
    const out = [];
    let skip = false;
    for (const line of lines) {
      const section = line.match(/^\s*\[([^\]]+)\]\s*$/);
      if (section) {
        const name = section[1].trim().toLowerCase();
        skip = name === 'newgrf' || name === 'newgrf-static';
        if (skip) continue;
      }
      if (!skip) out.push(line);
    }
    return out.join('\n');
  };

  const purge = (FS, personalDir) => {
    const removed = [];
    for (const path of [personalDir + '/newgrf', personalDir + '/content_download/newgrf']) {
      if (removeTree(FS, path)) removed.push(path);
    }
    const oldBase = personalDir + '/baseset/OpenGFX2_Classic-0.8.1.tar';
    if (unlink(FS, oldBase)) removed.push(oldBase);

    const configPath = personalDir + '/openttd.cfg';
    try {
      const before = FS.readFile(configPath, { encoding: 'utf8' });
      const after = stripNewGRFSections(before);
      if (after !== before) {
        FS.writeFile(configPath, after);
        removed.push(configPath + ':[newgrf]');
      }
    } catch (_) {}

    console.info('[OpenTTD vanilla] Persistent NewGRF migration complete', removed);
  };

  const previousRestore = window.yandexRestoreOpenTTDCloud;
  window.yandexRestoreOpenTTDCloud = async function (FS, personalDir) {
    if (typeof previousRestore === 'function') await previousRestore(FS, personalDir);
    purge(FS, personalDir);
    if (typeof FS.syncfs === 'function') {
      await new Promise((resolve) => {
        try { FS.syncfs(false, () => resolve()); } catch (_) { resolve(); }
      });
    }
  };
})();
'''
(r/'openttd-vanilla-migration.js').write_text(migration,encoding='utf-8')

for name in ['BUNDLED-ADDONS.md','LOCALIZATION-REPORT.md','OPENTTD-BUNDLED-ADDONS.json','ADDON-PACKAGE-SHA256SUMS.txt','THIRD-PARTY-ADDONS.md','openttd-bundled-addons.js']:
 p=r/name
 if p.exists(): p.unlink()
for name in ['addons','licenses/addons']:
 p=r/name
 if p.exists(): shutil.rmtree(p)

names=['Iron Horse','FIRS Industries','Road Hog','GIST','Early Vehicle Set','OpenGFX2 Settings','OpenGFX2 Classic']
for lic in ['THIRD-PARTY-LICENSES.md','PLAYGAMA-ALL-LICENSES.md']:
 p=r/lic
 if not p.is_file(): continue
 t=p.read_text(encoding='utf-8')
 t=t.replace('bundled base sets, AI packages, AI libraries and every optional NewGRF/base-graphics add-on shipped in this build.','bundled base sets, AI packages and AI libraries shipped in this build.')
 t=re.sub(r'(?ms)^## Optional add-ons \(disabled by default\)\s*\n.*?(?=^## |\Z)','',t)
 t=re.sub(r'(?ms)^## THIRD-PARTY-ADDONS\.md\s*\n.*?(?=^## |\Z)','',t)
 t=re.sub(r'(?ms)^## licenses/addons/[^\n]+\n.*?(?=^## |\Z)','',t)
 if platform=='yandex':
  for h in ['SOURCE_CODE.txt','NOTICE.txt','PLAYGAMA-INTEGRATION.txt']:
   t=re.sub(rf'(?ms)^## {re.escape(h)}\s*\n.*?(?=^## |\Z)','',t)
  t=t.replace('# OpenTTD Playgama — licenses and third-party notices','# OpenTTD Yandex Games — licenses and third-party notices')
  t=t.replace('OpenTTD 15.3 browser/Playgama port','OpenTTD 15.3 browser/Yandex Games port')
 t=re.sub(r'\n{3,}','\n\n',t).rstrip()+'\n'
 for n in names:
  if n in t: raise SystemExit(f'{lic}: addon mention remains: {n}')
 if platform=='yandex' and re.search(r'playgama|playgamma',t,re.I): raise SystemExit(f'{lic}: Playgama marker remains in Yandex notice')
 p.write_text(t,encoding='utf-8')

if platform=='yandex':
 p=r/'SOURCE_CODE.txt'
 t=p.read_text(encoding='utf-8')
 t=t.replace('OpenTTD 15.3 - Playgama WebAssembly edition','OpenTTD 15.3 - Yandex Games WebAssembly edition')
 t=t.replace('Web/Playgama port source, patches and reproducible build scripts:','Web/Yandex Games port source, patches and reproducible build scripts:')
 p.write_text(t,encoding='utf-8')
 p=r/'NOTICE.txt'
 t=p.read_text(encoding='utf-8')
 t=t.replace('OpenTTD 15.3 - Playgama WebAssembly edition','OpenTTD 15.3 - Yandex Games WebAssembly edition')
 t=t.replace('Playgama integration and WebAssembly build modifications are distributed','Yandex Games integration and WebAssembly build modifications are distributed')
 p.write_text(t,encoding='utf-8')

bad=[]
for p in r.rglob('*'):
 if not p.is_file(): continue
 rel=p.relative_to(r).as_posix(); low=rel.lower()
 if low.startswith('addons/') or low.startswith('licenses/addons/') or low.endswith(('.grf','.grf.bin','.tar.bin')): bad.append(rel)
 if p.suffix.lower() in {'.html','.js','.json','.md','.txt'}:
  try:t=p.read_text(encoding='utf-8')
  except UnicodeDecodeError: continue
  for m in ['OPENTTD-BUNDLED-ADDONS','__openttdBundled','openttd-bundled-addons.js']:
   if m in t: bad.append(rel+':'+m)
  if platform=='yandex' and re.search(r'playgama|playgamma',t,re.I): bad.append(rel+':playgama-marker')
if bad: raise SystemExit('release remnants: '+repr(bad))
if migration_tag not in idx.read_text(encoding='utf-8'): raise SystemExit('vanilla migration tag missing')
if not (r/'openttd-vanilla-migration.js').is_file(): raise SystemExit('vanilla migration script missing')
print(f'vanilla strip passed for {platform}; persistent NewGRF migration installed')
