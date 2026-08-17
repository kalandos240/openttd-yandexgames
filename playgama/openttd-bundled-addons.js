/* Optional bundled OpenTTD add-ons for the Playgama build.
 *
 * This file does NOT activate any NewGRF or base graphics set. It only makes
 * approved packages available in OpenTTD's normal local content directories
 * before main() starts. Players opt in through OpenTTD's own NewGRF Settings /
 * Game Options UI.
 *
 * Large payloads are stored as gzip-compressed files under ./addons. They are
 * decompressed only once into the persistent OpenTTD IDBFS area. Subsequent
 * launches compare the installed byte size and skip both download/decompression
 * when the local copy is already present. Installation is serial on purpose to
 * keep peak browser memory low on large NewGRFs.
 */
(() => {
  'use strict';
  if (window.__openttdBundledAddonsInstallerInstalled) return;
  window.__openttdBundledAddonsInstallerInstalled = true;

  const MANIFEST_URL = './OPENTTD-BUNDLED-ADDONS.json';
  const INSTALL_CONCURRENCY = 1;
  let manifestPromise = null;

  const ensureDir = (FS, path) => {
    let current = '';
    for (const part of String(path).split('/').filter(Boolean)) {
      current += '/' + part;
      try { FS.mkdir(current); } catch (_) {}
    }
  };

  const getManifest = () => {
    if (!manifestPromise) {
      manifestPromise = fetch(MANIFEST_URL, { cache: 'force-cache' }).then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status} while loading addon manifest`);
        const manifest = await response.json();
        if (!manifest || !Array.isArray(manifest.items)) throw new Error('Invalid bundled addon manifest');
        if (manifest.enabled_by_default !== false) throw new Error('Bundled add-ons must remain opt-in');
        return manifest;
      });
    }
    return manifestPromise;
  };

  const installRootFor = (personalDir, item) => {
    if (item.type === 'newgrf') return personalDir + '/newgrf';
    if (item.type === 'base-graphics') return personalDir + '/baseset';
    throw new Error(`Unsupported bundled addon type: ${item.type}`);
  };

  const inflateGzip = async (packed) => {
    if (typeof DecompressionStream !== 'function') {
      throw new Error('This browser does not support DecompressionStream(gzip)');
    }
    const stream = new Blob([packed]).stream().pipeThrough(new DecompressionStream('gzip'));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  };

  const decodeAsset = async (item, packed) => {
    const compression = item.compression || 'none';
    if (compression === 'none') return packed;
    if (compression === 'gzip') return inflateGzip(packed);
    throw new Error(`Unsupported compression ${compression} for ${item.content_id}`);
  };

  const installOne = async (FS, personalDir, item) => {
    const root = installRootFor(personalDir, item);
    ensureDir(FS, root);
    const target = root + '/' + item.install_filename;
    const installedBytes = Number(item.installed_bytes ?? item.bytes);
    const packagedBytes = Number(item.packaged_bytes ?? item.bytes);

    if (!Number.isFinite(installedBytes) || installedBytes <= 0) {
      throw new Error(`Invalid installed byte count for ${item.content_id}`);
    }

    try {
      const stat = FS.stat(target);
      if (Number(stat.size) === installedBytes) {
        return { id: item.content_id, state: 'cached', installed_bytes: installedBytes };
      }
    } catch (_) {}

    const assetUrl = new URL(item.asset, document.baseURI).toString();
    const response = await fetch(assetUrl, { cache: 'force-cache' });
    if (!response.ok) throw new Error(`HTTP ${response.status} while loading ${item.content_id}`);

    const packed = new Uint8Array(await response.arrayBuffer());
    if (Number.isFinite(packagedBytes) && packagedBytes > 0 && packed.byteLength !== packagedBytes) {
      throw new Error(`Packaged size mismatch for ${item.content_id}: expected ${packagedBytes}, got ${packed.byteLength}`);
    }

    const data = await decodeAsset(item, packed);
    if (data.byteLength !== installedBytes) {
      throw new Error(`Installed size mismatch for ${item.content_id}: expected ${installedBytes}, got ${data.byteLength}`);
    }

    FS.writeFile(target, data);
    return {
      id: item.content_id,
      state: 'installed',
      packaged_bytes: packed.byteLength,
      installed_bytes: data.byteLength,
    };
  };

  const mapLimit = async (items, limit, worker) => {
    const results = new Array(items.length);
    let next = 0;
    const runner = async () => {
      while (true) {
        const index = next++;
        if (index >= items.length) return;
        try {
          results[index] = await worker(items[index]);
        } catch (error) {
          results[index] = { id: items[index]?.content_id || String(index), state: 'failed', error: String(error) };
        }
      }
    };
    await Promise.all(Array.from({ length: Math.min(limit, items.length) }, runner));
    return results;
  };

  const persistWithoutBlockingStartup = () => {
    try {
      if (typeof window.openttd_syncfs === 'function') {
        window.openttd_syncfs(() => console.info('[Playgama/OpenTTD] Bundled addon cache persisted'));
      }
    } catch (error) {
      console.warn('[Playgama/OpenTTD] Could not schedule bundled addon persistence', error);
    }
  };

  const installBundledAddons = async (FS, personalDir) => {
    const manifest = await getManifest();
    const results = await mapLimit(manifest.items, INSTALL_CONCURRENCY, (item) => installOne(FS, personalDir, item));

    const installed = results.filter((row) => row?.state === 'installed').length;
    const cached = results.filter((row) => row?.state === 'cached').length;
    const failed = results.filter((row) => row?.state === 'failed');

    window.__openttdBundledAddonsStatus = {
      manifest_version: manifest.manifest_version,
      installed,
      cached,
      failed,
      results,
    };

    if (failed.length) {
      console.warn('[Playgama/OpenTTD] Some optional bundled add-ons could not be installed', failed);
    } else {
      console.info(`[Playgama/OpenTTD] Optional add-ons ready: ${installed} installed, ${cached} cached`);
    }

    if (installed > 0) persistWithoutBlockingStartup();
    return results;
  };

  /* Loaded after openttd-playgama-fixes.js, so this wraps the already-installed
     AI/config/cloud restore hook. Optional content is installed after cloud
     restore so older cloud state cannot overwrite the local bundled catalog. */
  const previousRestore = window.yandexRestoreOpenTTDCloud;
  window.yandexRestoreOpenTTDCloud = async function(FS, personalDir) {
    if (typeof previousRestore === 'function') await previousRestore(FS, personalDir);
    try {
      await installBundledAddons(FS, personalDir);
    } catch (error) {
      /* Add-on failure must never make the base game unbootable. */
      console.warn('[Playgama/OpenTTD] Optional addon installation failed; continuing with base game', error);
    }
  };
})();
