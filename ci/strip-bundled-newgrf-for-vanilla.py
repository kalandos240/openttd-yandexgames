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
if s.count(tag)!=1: raise SystemExit(f'expected one addon script tag, got {s.count(tag)}')
idx.write_text(s.replace(tag,'',1),encoding='utf-8')

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
if bad: raise SystemExit('addon remnants: '+repr(bad))
print(f'vanilla strip passed for {platform}')
