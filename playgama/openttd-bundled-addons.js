/* Optional bundled OpenTTD add-ons for the browser builds.
 *
 * Bundled content is immutable package data, not user data. It deliberately
 * lives outside /home/web_user/.openttd so IDBFS never has to restore tens of
 * MiB of static GRFs during a cold start. OpenTTD scans the binary search path
 * (including /newgrf and /baseset) natively when the NewGRF menu rescans.
 *
 * The installer is intentionally paced: network/decompression stays async and
 * each synchronous MEMFS write is moved to a browser idle turn. This prevents
 * the old behaviour where several large GRFs were written back-to-back shortly
 * after the first menu frame, which produced visible post-start stutters.
 */
(() => {
  'use strict';
  if (window.__openttdBundledAddonsInstallerInstalled) return;
  window.__openttdBundledAddonsInstallerInstalled = true;

  const MANIFEST_URL = './OPENTTD-BUNDLED-ADDONS.json';
  const INSTALL_CONCURRENCY = 1;
  const FETCH_TIMEOUT_MS = 8000;
  const RESTORE_STARTUP_GATE_MS = 1500;
  const POST_START_DELAY_MS = 1200;
  const POST_START_IDLE_TIMEOUT_MS = 5000;
  const WRITE_IDLE_TIMEOUT_MS = 1500;
  const INTER_ITEM_YIELD_MS = 32;

  let manifestPromise = null;

  const ensureDir = (FS, path) => {
    let current = '';
    for (const part of String(path).split('/').filter(Boolean)) {
      current += '/' + part;
      try { FS.mkdir(current); } catch (_) {}
    }
  };

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const waitForIdle = (timeout = WRITE_IDLE_TIMEOUT_MS) => new Promise((resolve) => {
    if (typeof window.requestIdleCallback === 'function') {
      window.requestIdleCallback(() => resolve(), { timeout });
    } else {
      setTimeout(resolve, 16);
    }
  });

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

  const installRootFor = (item) => {
    if (item.type === 'newgrf') return '/newgrf';
    if (item.type === 'base-graphics') return '/baseset';
    throw new Error(`Unsupported bundled addon type: ${item.type}`);
  };

  const installedBytesFor = (item) => Number(item.installed_bytes ?? item.bytes);

  const orderedItems = (items) => [...items].sort((a, b) => {
    const aBase = a?.type === 'base-graphics' ? 1 : 0;
    const bBase = b?.type === 'base-graphics' ? 1 : 0;
    if (aBase !== bBase) return aBase - bBase;
    const aBytes = installedBytesFor(a);
    const bBytes = installedBytesFor(b);
    if (Number.isFinite(aBytes) && Number.isFinite(bBytes) && aBytes !== bBytes) return aBytes - bBytes;
    return String(a?.content_id || '').localeCompare(String(b?.content_id || ''));
  });

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

  const installOne = async (FS, item) => {
    const root = installRootFor(item);
    ensureDir(FS, root);
    const target = root + '/' + item.install_filename;
    const installedBytes = installedBytesFor(item);
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

    // FS.writeFile is synchronous and can block a frame for multi-megabyte GRFs.
    // Enter an idle turn immediately before the write, then yield once more so
    // rendering/input gets a chance to run before the next asset starts.
    await waitForIdle();
    FS.writeFile(target, data);
    await sleep(INTER_ITEM_YIELD_MS);
    return { id: item.content_id, state: 'installed', installed_bytes: data.byteLength, target };
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

  const installBundledContent = async (FS) => {
    const manifest = await getManifest();
    const items = orderedItems(manifest.items);
    window.__openttdBundledAddonsProgress = { total: items.length, completed: 0, current: null };

    const results = await mapLimit(items, INSTALL_CONCURRENCY, async (item) => {
      window.__openttdBundledAddonsProgress.current = item.content_id;
      const result = await installOne(FS, item);
      window.__openttdBundledAddonsProgress.completed += 1;
      return result;
    });

    window.__openttdBundledAddonsProgress.current = null;
    const failed = results.filter((row) => row?.state === 'failed');
    window.__openttdBundledAddonsStatus = {
      manifest_version: manifest.manifest_version,
      installed: results.filter((row) => row?.state === 'installed').length,
      cached: results.filter((row) => row?.state === 'cached').length,
      failed,
      results,
      persistent: false,
      paced_writes: true,
    };
    if (failed.length) console.warn('[OpenTTD] Some optional add-ons were unavailable:', failed);
    return results;
  };

  let bundledContentScheduled = false;
  let bundledContentStarted = false;

  const startBundledContent = (FS) => {
    if (bundledContentStarted) return window.__openttdBundledContentReady || Promise.resolve([]);
    bundledContentStarted = true;
    window.__openttdBundledAddonsState = 'installing-after-main';
    const contentTask = installBundledContent(FS)
      .then((results) => {
        window.__openttdBundledAddonsState = 'ready';
        return results;
      })
      .catch((error) => {
        window.__openttdBundledAddonsState = 'failed';
        window.__openttdBundledAddonsFatalError = String(error);
        console.warn('[OpenTTD] Optional content install failed; gameplay is not blocked', error);
        return [];
      });
    window.__openttdBundledContentReady = contentTask;
    return contentTask;
  };

  const scheduleBundledContentAfterStartup = (FS) => {
    if (bundledContentScheduled) return;
    bundledContentScheduled = true;
    window.__openttdBundledAddonsState = 'waiting-for-main';

    const waitForMain = () => {
      const module = window.Module;
      if (!module || module.calledRun !== true) {
        setTimeout(waitForMain, 100);
        return;
      }

      const startWhenIdle = () => {
        if (typeof window.requestIdleCallback === 'function') {
          window.requestIdleCallback(
            () => startBundledContent(FS),
            { timeout: POST_START_IDLE_TIMEOUT_MS },
          );
        } else {
          setTimeout(() => startBundledContent(FS), 0);
        }
      };

      // Let the first menu frames render before bundled content begins. Each
      // individual MEMFS write is additionally paced by installOne().
      setTimeout(startWhenIdle, POST_START_DELAY_MS);
    };

    const module = window.Module;
    if (module && module.calledRun === true) {
      waitForMain();
    } else if (module && Array.isArray(module.postRun)) {
      module.postRun.push(waitForMain);
    } else {
      setTimeout(waitForMain, 0);
    }
  };

  const previousRestore = window.yandexRestoreOpenTTDCloud;
  window.yandexRestoreOpenTTDCloud = async function(FS, personalDir) {
    // Merely arm optional content in preRun. No HTTP, decompression or static
    // content writes are permitted before OpenTTD enters main().
    scheduleBundledContentAfterStartup(FS);

    const restoreTask = (async () => {
      if (typeof previousRestore !== 'function') return;
      try { await previousRestore(FS, personalDir); }
      catch (error) { console.warn('[OpenTTD] Cloud restore failed; continuing locally', error); }
    })();

    await Promise.race([
      restoreTask,
      new Promise((resolve) => setTimeout(resolve, RESTORE_STARTUP_GATE_MS)),
    ]);
  };
})();
