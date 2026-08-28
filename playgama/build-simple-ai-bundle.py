#!/usr/bin/env python3
"""Build the pinned SimpleAI browser payload from OpenTTD BaNaNaS."""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

from openttdlab import download_from_bananas


def build() -> tuple[dict[str, str], list[dict[str, object]]]:
    payload: dict[str, str] = {}
    manifest: list[dict[str, object]] = []

    with download_from_bananas('ai/534d504c') as files:
        for item in files:
            if len(item) == 5:
                content_id, filename, license_name, md5, get_data = item
            elif len(item) == 4:
                content_id, filename, md5, get_data = item
                license_name = 'unknown'
            else:
                raise RuntimeError(f'Unexpected BaNaNaS item: {item!r}')

            content_id = str(content_id)
            filename = str(filename)
            with get_data() as chunks:
                data = b''.join(chunks)
            if not data:
                raise RuntimeError(f'Empty BaNaNaS payload: {content_id}')

            if content_id.startswith('ai/'):
                relative = 'ai/' + filename
            elif content_id.startswith(('ai-library/', 'ailibrary/')):
                relative = 'ai/library/' + filename
            else:
                raise RuntimeError(f'Unexpected SimpleAI dependency type: {content_id}')

            payload[relative] = base64.b64encode(data).decode('ascii')
            manifest.append({
                'content_id': content_id,
                'filename': filename,
                'license': str(license_name),
                'md5': str(md5),
                'bytes': len(data),
                'install_path': relative,
            })

    if not any(row['content_id'] == 'ai/534d504c' for row in manifest):
        raise RuntimeError('SimpleAI was not returned by BaNaNaS')
    if len(manifest) < 3:
        raise RuntimeError(f'Expected SimpleAI plus dependencies, got {manifest!r}')
    return payload, manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--output-js', type=Path, required=True)
    ap.add_argument('--output-manifest', type=Path, required=True)
    args = ap.parse_args()

    payload, manifest = build()
    args.output_js.parent.mkdir(parents=True, exist_ok=True)
    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output_js.write_text(
        '/* Generated in CI from OpenTTD BaNaNaS SimpleAI and dependencies. */\n'
        'window.__openttdClassicAIArchives = ' + json.dumps(payload, separators=(',', ':')) + ';\n'
        'window.__openttdClassicAIManifest = ' + json.dumps(manifest, separators=(',', ':')) + ';\n',
        encoding='utf-8',
    )
    args.output_manifest.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
