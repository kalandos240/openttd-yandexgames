/* Optional bundled OpenTTD add-ons for the Playgama build.
 *
 * This file does NOT activate any NewGRF or base graphics set. It only makes
 * approved packages available in OpenTTD's normal local content directories.
 * Players opt in through OpenTTD's own NewGRF Settings / Game Options UI.
 *
 * IMPORTANT: the installer owns an Emscripten run dependency while the local
 * catalogue is being restored/installed. OpenTTD must not reach main() and its
 * initial NewGRF scan before the files exist in IDBFS. This fixes the v7 race
 * where the runtime's 2.5 s cloud-restore timeout allowed the game to start
 * while large NewGRFs were still being decompressed in the background.
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
  const STARTUP_DEPENDENCY = 'playgama-bundled-content';

  let manifestPromise = null;
  let startupDependencyHeld = false;
  let startupDependencyReleased = false;

  const ensureDir = (FS, path) => {
    let current = '';
    for (const part of String(path).split('/').filter(Boolean)) {
      current += '/' + part;
      try { FS.mkdir(current); } catch (_) {}
    }
  };

  const holdStartupDependency = () => {
    if (startupDependencyHeld || startupDependencyReleased) return startupDependencyHeld;
    const module = window.Module;
    if (module && typeof module.addRunDependency === 'function') {
      module.addRunDependency(STARTUP_DEPENDENCY);
      startupDependencyHeld = true;
      console.info('[Playgama/OpenTTD] Holding startup until bundled content is ready');
      return true;
    }
    console.warn('[Playgama/OpenTTD] Could not acquire bundled-content startup dependency');
    return false;
  };

  const releaseStartupDependency = () => {
    if (!startupDependencyHeld || startupDependencyReleased) return;
    startupDependencyReleased = true;
    const module = window.Module;
    if (module && typeof module.removeRunDependency === 'function') {
      module.removeRunDependency(STARTUP_DEPENDENCY);
      console.info('[Playgama/OpenTTD] Bundled content ready; startup released');
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

    console.info(`[Playgama/OpenTTD] Optional add-ons ready before main(): ${installed} installed, ${cached} cached`);
    return results;
  };

  /* Loaded before the generated runtime. The wrapper is called from the
     runtime's preRun flow after IDBFS populate. Acquiring our own run dependency
     synchronously here makes the runtime's separate 2.5 s cloud timeout harmless:
     main() remains blocked until every bundled local package has been installed. */
  const previousRestore = window.yandexRestoreOpenTTDCloud;
  window.yandexRestoreOpenTTDCloud = function(FS, personalDir) {
    holdStartupDependency();

    const task = (async () => {
      let restoreError = null;
      let restoreTimedOut = false;

      /* Cloud restore and local add-on installation are independent. Start them
         together so network latency cannot unnecessarily extend first launch. */
      const restoreTask = (async () => {
        if (typeof previousRestore !== 'function') return;
        try {
          await previousRestore(FS, personalDir);
        } catch (error) {
          restoreError = error;
          console.warn('[Playgama/OpenTTD] Cloud/AI restore failed; continuing with local bundled content', error);
        }
      })();
      const restoreGate = Promise.race([
        restoreTask,
        new Promise((resolve) => setTimeout(() => { restoreTimedOut = true; resolve(); }, CLOUD_RESTORE_GATE_MS)),
      ]);

      let licenseStatus = null;
      try {
        const localContentTask = (async () => {
          licenseStatus = await installLicenseBundle(FS, personalDir);
          await installBundledAddons(FS, personalDir);
        })();
        await Promise.all([localContentTask, restoreGate]);
        persistWithoutBlockingStartup();
      } catch (error) {
        window.__openttdBundledAddonsFatalError = String(error);
        console.error('[Playgama/OpenTTD] Bundled content installation failed', error);
        throw error;
      } finally {
        window.__openttdBundledLicenseStatus = licenseStatus;
      }

      if (restoreError) console.warn('[Playgama/OpenTTD] Game started with local content despite restore warning');
      if (restoreTimedOut) console.info('[Playgama/OpenTTD] Cloud restore continues in background after startup gate');
    })();

    window.__openttdBundledContentReady = task;
    return task.finally(releaseStartupDependency);
  };
})();
