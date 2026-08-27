/* Optional bundled OpenTTD add-ons for the Playgama build.
 *
 * This file does NOT activate any NewGRF or base graphics set. It only makes
 * approved packages available in OpenTTD's normal local content directories.
 * Players opt in through OpenTTD's own NewGRF Settings / Game Options UI.
 *
 * IMPORTANT: bundled add-ons are optional and must never block OpenTTD startup.
 * They are restored/installed in the background after IDBFS is available. The
 * Playgama main-menu patch performs a defensive NewGRF rescan when the user opens
 * NewGRF Settings, so first launch stays fast even on slow storage/CDN paths.
 */
(() => {
  'use strict';
  if (window.__openttdBundledAddonsInstallerInstalled) return;
  window.__openttdBundledAddonsInstallerInstalled = true;

  const MANIFEST_URL = './OPENTTD-BUNDLED-ADDONS.json';
  const LICENSE_BUNDLE_URL = './PLAYGAMA-ALL-LICENSES.md';
  const LICENSE_TARGET_NAME = 'PLAYGAMA-LICENSES.md';
  const INSTALL_CONCURRENCY = 1;
  const CLOUD_RESTORE_GATE_MS = 2200;
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

  const isGzipPayload = (data) => data && data.byteLength >= 2 && data[0] === 0x1f && data[1] === 0x8b;

  const decodeAsset = async (item, packed, installedBytes) => {
    const compression = item.compression || 'none';
    if (compression === 'none') return packed;
    if (compression === 'gzip') {
      /* Some static hosts/CDNs treat .gz as Content-Encoding and transparently
         decode the body before fetch() exposes it. Accept that transport form
         when it already matches the verified installed size; otherwise inflate
         the opaque gzip payload ourselves. */
      if (!isGzipPayload(packed) && packed.byteLength === installedBytes) return packed;
      if (!isGzipPayload(packed)) {
        throw new Error(`Invalid gzip transport for ${item.content_id}: ${packed.byteLength} bytes`);
      }
      return inflateGzip(packed);
    }
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
    const transparentlyDecoded = (item.compression || 'none') === 'gzip' &&
      !isGzipPayload(packed) && packed.byteLength === installedBytes;
    if (!transparentlyDecoded && Number.isFinite(packagedBytes) && packagedBytes > 0 && packed.byteLength !== packagedBytes) {
      throw new Error(`Packaged size mismatch for ${item.content_id}: expected ${packagedBytes}, got ${packed.byteLength}`);
    }

    const data = await decodeAsset(item, packed, installedBytes);
    if (data.byteLength !== installedBytes) {
      throw new Error(`Installed size mismatch for ${item.content_id}: expected ${installedBytes}, got ${data.byteLength}`);
    }

    FS.writeFile(target, data);
    return {
      id: item.content_id,
      state: 'installed',
      packaged_bytes: packed.byteLength,
      installed_bytes: data.byteLength,
      transport_decoded: transparentlyDecoded,
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

  const installLicenseBundle = async (FS, personalDir) => {
    ensureDir(FS, personalDir);
    const response = await fetch(new URL(LICENSE_BUNDLE_URL, document.baseURI).toString(), { cache: 'force-cache' });
    if (!response.ok) throw new Error(`HTTP ${response.status} while loading license bundle`);
    const data = new Uint8Array(await response.arrayBuffer());
    if (data.byteLength < 1024) throw new Error('Bundled license document is unexpectedly small');
    const target = personalDir + '/' + LICENSE_TARGET_NAME;
    FS.writeFile(target, data);
    window.__openttdLicenseBundlePath = target;
    return { state: 'installed', bytes: data.byteLength, path: target };
  };

  const persistWithoutBlockingStartup = () => {
    const persist = () => {
      try {
        if (typeof window.openttd_syncfs === 'function') {
          window.openttd_syncfs(() => console.info('[Playgama/OpenTTD] Bundled content cache persisted'));
        }
      } catch (error) {
        console.warn('[Playgama/OpenTTD] Could not persist bundled content cache', error);
      }
    };

    /* Large NewGRFs can make the first IDBFS flush expensive. Do not contend
       with OpenTTD's first rendered frames; persist on idle (or shortly after). */
    try {
      if (typeof window.requestIdleCallback === 'function') {
        window.requestIdleCallback(persist, { timeout: 3000 });
      } else {
        setTimeout(persist, 500);
      }
    } catch (error) {
      console.warn('[Playgama/OpenTTD] Could not schedule bundled content persistence', error);
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
      throw new Error(`Failed to install ${failed.length} bundled add-on(s): ${failed.map((row) => row.id).join(', ')}`);
    }

    console.info(`[Playgama/OpenTTD] Optional add-ons ready: ${installed} installed, ${cached} cached`);
    return results;
  };

  /* Loaded before the generated runtime. The wrapper is called from the
     runtime's preRun flow after IDBFS populate. Optional local content is kicked
     off in the background and is deliberately excluded from the startup promise.
     This guarantees that a slow/blocked asset request cannot leave the game on
     the initial "Loading ..." screen. */
  const previousRestore = window.yandexRestoreOpenTTDCloud;
  window.yandexRestoreOpenTTDCloud = function(FS, personalDir) {
    const restoreTask = (async () => {
      if (typeof previousRestore !== 'function') return;
      try {
        await previousRestore(FS, personalDir);
      } catch (error) {
        console.warn('[Playgama/OpenTTD] Cloud/AI restore failed; continuing with local saves', error);
      }
    })();

    const localContentTask = (async () => {
      let licenseStatus = null;
      try {
        licenseStatus = await installLicenseBundle(FS, personalDir);
        await installBundledAddons(FS, personalDir);
        persistWithoutBlockingStartup();
      } catch (error) {
        window.__openttdBundledAddonsError = String(error);
        console.warn('[Playgama/OpenTTD] Optional bundled content is unavailable; game startup is unaffected', error);
      } finally {
        window.__openttdBundledLicenseStatus = licenseStatus;
      }
    })();

    window.__openttdBundledContentReady = localContentTask;
    return Promise.race([
      restoreTask,
      new Promise((resolve) => setTimeout(resolve, CLOUD_RESTORE_GATE_MS)),
    ]);
  };
})();
