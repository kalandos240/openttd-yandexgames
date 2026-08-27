/* Optional bundled OpenTTD add-ons for the Playgama build.
 *
 * Add-ons are deliberately NOT a startup dependency. Platform moderation must
 * always reach OpenTTD even when an optional asset, IndexedDB, cloud storage or
 * CDN request is slow/unavailable. The local catalogue is filled in the
 * background and the existing native NewGRF menu performs a defensive rescan.
 */
(() => {
  'use strict';
  if (window.__openttdBundledAddonsInstallerInstalled) return;
  window.__openttdBundledAddonsInstallerInstalled = true;

  const MANIFEST_URL = './OPENTTD-BUNDLED-ADDONS.json';
  const LICENSE_BUNDLE_URL = './PLAYGAMA-ALL-LICENSES.md';
  const LICENSE_TARGET_NAME = 'PLAYGAMA-LICENSES.md';
  const INSTALL_CONCURRENCY = 1;
  const FETCH_TIMEOUT_MS = 8000;
  const RESTORE_STARTUP_GATE_MS = 1500;

  let manifestPromise = null;

  const ensureDir = (FS, path) => {
    let current = '';
    for (const part of String(path).split('/').filter(Boolean)) {
      current += '/' + part;
      try { FS.mkdir(current); } catch (_) {}
    }
  };

  const fetchWithTimeout = async (url, options = {}) => {
    if (typeof AbortController !== 'function') return fetch(url, options);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
    try {
      return await fetch(url, { ...options, signal: controller.signal });
    } finally {
      clearTimeout(timer);
    }
  };

  const getManifest = () => {
    if (!manifestPromise) {
      manifestPromise = fetchWithTimeout(MANIFEST_URL, { cache: 'force-cache' }).then(async (response) => {
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
      if (!isGzipPayload(packed) && packed.byteLength === installedBytes) return packed;
      if (!isGzipPayload(packed)) throw new Error(`Invalid gzip transport for ${item.content_id}`);
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
      if (Number(stat.size) === installedBytes) return { id: item.content_id, state: 'cached' };
    } catch (_) {}

    const assetUrl = new URL(item.asset, document.baseURI).toString();
    const response = await fetchWithTimeout(assetUrl, { cache: 'force-cache' });
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
    return { id: item.content_id, state: 'installed', installed_bytes: data.byteLength };
  };

  const mapLimit = async (items, limit, worker) => {
    const results = new Array(items.length);
    let next = 0;
    const runner = async () => {
      while (true) {
        const index = next++;
        if (index >= items.length) return;
        try { results[index] = await worker(items[index]); }
        catch (error) {
          results[index] = { id: items[index]?.content_id || String(index), state: 'failed', error: String(error) };
        }
      }
    };
    await Promise.all(Array.from({ length: Math.min(limit, Math.max(items.length, 1)) }, runner));
    return results;
  };

  const installLicenseBundle = async (FS, personalDir) => {
    ensureDir(FS, personalDir);
    const response = await fetchWithTimeout(new URL(LICENSE_BUNDLE_URL, document.baseURI).toString(), { cache: 'force-cache' });
    if (!response.ok) throw new Error(`HTTP ${response.status} while loading license bundle`);
    const data = new Uint8Array(await response.arrayBuffer());
    if (data.byteLength < 1024) throw new Error('Bundled license document is unexpectedly small');
    const target = personalDir + '/' + LICENSE_TARGET_NAME;
    FS.writeFile(target, data);
    window.__openttdLicenseBundlePath = target;
    return { state: 'installed', bytes: data.byteLength, path: target };
  };

  const persistLater = () => {
    const persist = () => {
      try {
        if (typeof window.openttd_syncfs === 'function') {
          window.openttd_syncfs(() => console.info('[Playgama/OpenTTD] Optional content cache persisted'));
        }
      } catch (error) {
        console.warn('[Playgama/OpenTTD] Could not persist optional content cache', error);
      }
    };
    if (typeof window.requestIdleCallback === 'function') window.requestIdleCallback(persist, { timeout: 3000 });
    else setTimeout(persist, 500);
  };

  const installBundledContent = async (FS, personalDir) => {
    let licenseStatus = null;
    try { licenseStatus = await installLicenseBundle(FS, personalDir); }
    catch (error) { console.warn('[Playgama/OpenTTD] License bundle background install failed', error); }

    const manifest = await getManifest();
    const results = await mapLimit(manifest.items, INSTALL_CONCURRENCY, (item) => installOne(FS, personalDir, item));
    const failed = results.filter((row) => row?.state === 'failed');
    window.__openttdBundledLicenseStatus = licenseStatus;
    window.__openttdBundledAddonsStatus = {
      manifest_version: manifest.manifest_version,
      installed: results.filter((row) => row?.state === 'installed').length,
      cached: results.filter((row) => row?.state === 'cached').length,
      failed,
      results,
    };
    if (failed.length) console.warn('[Playgama/OpenTTD] Some optional add-ons were unavailable:', failed);
    persistLater();
    return results;
  };

  const previousRestore = window.yandexRestoreOpenTTDCloud;
  window.yandexRestoreOpenTTDCloud = async function(FS, personalDir) {
    const restoreTask = (async () => {
      if (typeof previousRestore !== 'function') return;
      try { await previousRestore(FS, personalDir); }
      catch (error) { console.warn('[Playgama/OpenTTD] Cloud restore failed; continuing locally', error); }
    })();

    const contentTask = installBundledContent(FS, personalDir).catch((error) => {
      window.__openttdBundledAddonsFatalError = String(error);
      console.warn('[Playgama/OpenTTD] Optional content install failed; gameplay is not blocked', error);
    });
    window.__openttdBundledContentReady = contentTask;

    // Cloud state gets a short opportunity to restore before main(). Optional
    // content never participates in this gate. This guarantees a bounded launch.
    await Promise.race([
      restoreTask,
      new Promise((resolve) => setTimeout(resolve, RESTORE_STARTUP_GATE_MS)),
    ]);
  };
})();
