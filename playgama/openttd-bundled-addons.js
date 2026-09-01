/* Optional bundled OpenTTD add-ons for the browser builds.
 *
 * Bundled content is immutable package data, not user data. It deliberately
 * lives outside /home/web_user/.openttd so IDBFS never has to restore tens of
 * MiB of static GRFs during a cold start. OpenTTD scans the binary search path
 * (including /newgrf and /baseset) natively when the NewGRF menu rescans.
 *
 * The installer is intentionally paced: optional same-origin network traffic
 * is low priority, one following asset may download while the current asset is
 * decoded/published, and synchronous MEMFS publication happens in idle turns.
 * The decoded Uint8Array is handed to MEMFS with canOwn=true, so Emscripten can
 * adopt that buffer instead of cloning multi-megabyte GRFs during writeFile().
 */
(() => {
  'use strict';

  /* Reuse this same same-origin script as a decompression worker. This keeps
     Yandex CSP/autonomy simple: no blob: workers and no additional package
     resource are required. Large gzip expansion stays off the game/render
     thread, while the main-thread path remains an explicit fallback. */
  if (typeof window === 'undefined' && typeof self !== 'undefined') {
    self.onmessage = async (event) => {
      const message = event?.data || {};
      if (message.type === 'probe') {
        self.postMessage({ type: 'probe-result', id: message.id, supported: typeof DecompressionStream === 'function' });
        return;
      }
      if (message.type !== 'inflate') return;
      try {
        if (typeof DecompressionStream !== 'function') throw new Error('DecompressionStream(gzip) is unavailable in worker');
        const packed = new Uint8Array(message.buffer);
        const stream = new Blob([packed]).stream().pipeThrough(new DecompressionStream('gzip'));
        const buffer = await new Response(stream).arrayBuffer();
        self.postMessage({ type: 'inflate-result', id: message.id, ok: true, buffer }, [buffer]);
      } catch (error) {
        self.postMessage({ type: 'inflate-result', id: message.id, ok: false, error: String(error) });
      }
    };
    return;
  }

  if (window.__openttdBundledAddonsInstallerInstalled) return;
  window.__openttdBundledAddonsInstallerInstalled = true;

  const MANIFEST_URL = './OPENTTD-BUNDLED-ADDONS.json';
  const NETWORK_PREFETCH_AHEAD = 1;
  const WORKER_DECOMPRESSION_MIN_BYTES = 1024 * 1024;
  const FETCH_BASE_TIMEOUT_MS = 15000;
  const FETCH_MAX_TIMEOUT_MS = 120000;
  const FETCH_BYTES_PER_SECOND_FLOOR = 96 * 1024;
  const RESTORE_STARTUP_GATE_MS = 1500;
  const POST_START_DELAY_MS = 1200;
  const POST_START_IDLE_TIMEOUT_MS = 5000;
  const WRITE_IDLE_TIMEOUT_MS = 1500;
  const INTER_ITEM_YIELD_MS = 32;
  const OPTIONAL_ASSET_FETCH_OPTIONS = { cache: 'force-cache', priority: 'low' };

  let manifestPromise = null;
  const packedAssetPromises = new Map();
  const loaderScriptUrl = document.currentScript?.src || new URL('./openttd-bundled-addons.js', document.baseURI).toString();
  let decompressionWorkerPromise = null;
  let decompressionWorker = null;
  let decompressionRequestId = 0;
  const networkStats = window.__openttdBundledAddonsNetworkStats = {
    lowPriority: true,
    prefetchAhead: NETWORK_PREFETCH_AHEAD,
    adaptiveTimeout: true,
    workerDecompression: true,
    workerAvailable: false,
    workerInflates: 0,
    workerFallbacks: 0,
    workerTerminatedAfterInstall: false,
    fetchesStarted: 0,
    prefetchedAssets: 0,
  };

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

  const timeoutForBytes = (bytes) => {
    const size = Number(bytes);
    if (!Number.isFinite(size) || size <= 0) return FETCH_BASE_TIMEOUT_MS;
    const transferBudget = Math.ceil((size / FETCH_BYTES_PER_SECOND_FLOOR) * 1000) + 10000;
    return Math.min(FETCH_MAX_TIMEOUT_MS, Math.max(FETCH_BASE_TIMEOUT_MS, transferBudget));
  };

  const fetchWithTimeout = async (url, options = {}, timeoutMs = FETCH_BASE_TIMEOUT_MS) => {
    if (typeof AbortController !== 'function') return fetch(url, options);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await fetch(url, { ...options, signal: controller.signal });
    } finally {
      clearTimeout(timer);
    }
  };

  const getManifest = () => {
    if (!manifestPromise) {
      manifestPromise = fetchWithTimeout(MANIFEST_URL, OPTIONAL_ASSET_FETCH_OPTIONS).then(async (response) => {
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

  const inflateGzipMainThread = async (packed) => {
    if (typeof DecompressionStream !== 'function') {
      throw new Error('This browser does not support DecompressionStream(gzip)');
    }
    const stream = new Blob([packed]).stream().pipeThrough(new DecompressionStream('gzip'));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  };

  const getDecompressionWorker = () => {
    if (decompressionWorkerPromise) return decompressionWorkerPromise;
    decompressionWorkerPromise = new Promise((resolve) => {
      if (typeof Worker !== 'function') { resolve(null); return; }
      let worker;
      try {
        worker = new Worker(loaderScriptUrl, { name: 'openttd-addon-inflate' });
      } catch (_) {
        resolve(null);
        return;
      }
      const id = ++decompressionRequestId;
      let settled = false;
      const finish = (value) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        worker.removeEventListener('message', onMessage);
        worker.removeEventListener('error', onError);
        if (!value) { try { worker.terminate(); } catch (_) {} }
        decompressionWorker = value || null;
        networkStats.workerAvailable = !!value;
        resolve(value);
      };
      const onMessage = (event) => {
        const message = event?.data || {};
        if (message.type === 'probe-result' && message.id === id) finish(message.supported === true ? worker : null);
      };
      const onError = () => finish(null);
      const timer = setTimeout(() => finish(null), 1500);
      worker.addEventListener('message', onMessage);
      worker.addEventListener('error', onError);
      try { worker.postMessage({ type: 'probe', id }); } catch (_) { finish(null); }
    });
    return decompressionWorkerPromise;
  };

  const shutdownDecompressionWorker = () => {
    const worker = decompressionWorker;
    decompressionWorker = null;
    decompressionWorkerPromise = null;
    if (!worker) return;
    try { worker.terminate(); } catch (_) {}
    networkStats.workerTerminatedAfterInstall = true;
  };

  const inflateGzipInWorker = async (packed) => {
    const worker = await getDecompressionWorker();
    if (!worker) return null;
    const id = ++decompressionRequestId;
    return new Promise((resolve, reject) => {
      let settled = false;
      const finish = (fn, value) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        worker.removeEventListener('message', onMessage);
        worker.removeEventListener('error', onError);
        fn(value);
      };
      const onMessage = (event) => {
        const message = event?.data || {};
        if (message.type !== 'inflate-result' || message.id !== id) return;
        if (message.ok && message.buffer) finish(resolve, new Uint8Array(message.buffer));
        else finish(reject, new Error(message.error || 'Add-on decompression worker failed'));
      };
      const onError = (event) => finish(reject, new Error(event?.message || 'Add-on decompression worker error'));
      const timer = setTimeout(() => finish(reject, new Error('Add-on decompression worker timeout')), 120000);
      worker.addEventListener('message', onMessage);
      worker.addEventListener('error', onError);
      try {
        /* Transfer the compressed buffer without copying. If the worker fails,
           decodeAsset refetches the immutable package asset through force-cache
           before using the main-thread fallback. */
        worker.postMessage({ type: 'inflate', id, buffer: packed.buffer }, [packed.buffer]);
      } catch (error) {
        finish(reject, error);
      }
    });
  };

  const isGzipPayload = (data) => data && data.byteLength >= 2 && data[0] === 0x1f && data[1] === 0x8b;

  const decodeAsset = async (item, packed, installedBytes) => {
    const compression = item.compression || 'none';
    if (compression === 'none') return packed;
    if (compression === 'gzip') {
      if (!isGzipPayload(packed) && packed.byteLength === installedBytes) return packed;
      if (!isGzipPayload(packed)) throw new Error(`Invalid gzip transport for ${item.content_id}`);

      if (installedBytes >= WORKER_DECOMPRESSION_MIN_BYTES) {
        try {
          const decoded = await inflateGzipInWorker(packed);
          if (decoded) {
            networkStats.workerInflates++;
            return decoded;
          }
        } catch (error) {
          networkStats.workerFallbacks++;
          console.info('[OpenTTD] Add-on worker decompression fell back to main thread:', item.content_id, error);
          /* The transferable packed buffer is detached after postMessage().
             Refetch the immutable same-origin asset; force-cache normally makes
             this a local browser-cache read rather than another network trip. */
          const assetUrl = new URL(item.asset, document.baseURI).toString();
          const response = await fetchWithTimeout(assetUrl, OPTIONAL_ASSET_FETCH_OPTIONS, timeoutForBytes(item.packaged_bytes ?? item.bytes));
          if (!response.ok) throw new Error(`HTTP ${response.status} while reloading ${item.content_id} after worker fallback`);
          packed = new Uint8Array(await response.arrayBuffer());
        }
      }
      return inflateGzipMainThread(packed);
    }
    throw new Error(`Unsupported compression ${compression} for ${item.content_id}`);
  };

  const primePackedAsset = (item, prefetched = false) => {
    const id = String(item?.content_id || '');
    if (!id || packedAssetPromises.has(id)) return;
    const assetUrl = new URL(item.asset, document.baseURI).toString();
    const packagedBytes = Number(item.packaged_bytes ?? item.bytes);
    const timeoutMs = timeoutForBytes(packagedBytes);
    networkStats.fetchesStarted++;
    if (prefetched) networkStats.prefetchedAssets++;

    /* Resolve failures into the promise value so a one-ahead request cannot
       produce an unhandled rejection before its turn reaches installOne(). */
    const task = fetchWithTimeout(assetUrl, OPTIONAL_ASSET_FETCH_OPTIONS, timeoutMs)
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status} while loading ${id}`);
        return { packed: new Uint8Array(await response.arrayBuffer()), timeoutMs };
      })
      .catch((error) => ({ error, timeoutMs }));
    packedAssetPromises.set(id, task);
  };

  const consumePackedAsset = async (item) => {
    const id = String(item?.content_id || '');
    primePackedAsset(item, false);
    const task = packedAssetPromises.get(id);
    const result = await task;
    packedAssetPromises.delete(id);
    if (result?.error) throw result.error;
    return result?.packed;
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

    /* The current request may already be in flight because installBundledContent
       primes one following item. Decompression and MEMFS publication remain
       strictly sequential, so the pipeline overlaps only low-priority network
       latency without doubling the expensive decoded-memory working set. */
    const packed = await consumePackedAsset(item);
    const transparentlyDecoded = (item.compression || 'none') === 'gzip' &&
      !isGzipPayload(packed) && packed.byteLength === installedBytes;
    if (!transparentlyDecoded && Number.isFinite(packagedBytes) && packagedBytes > 0 && packed.byteLength !== packagedBytes) {
      throw new Error(`Packaged size mismatch for ${item.content_id}: expected ${packagedBytes}, got ${packed.byteLength}`);
    }

    /* Begin large decompression from an idle turn as well. DecompressionStream
       itself remains asynchronous, but this avoids scheduling its setup inside
       a hot render callback on browsers that do some stream work on main. */
    await waitForIdle();
    const data = await decodeAsset(item, packed, installedBytes);
    if (data.byteLength !== installedBytes) {
      throw new Error(`Installed size mismatch for ${item.content_id}: expected ${installedBytes}, got ${data.byteLength}`);
    }

    /* Emscripten 3.1.57 MEMFS supports writeFile(..., {canOwn:true}). For a
       standalone Uint8Array this transfers ownership of the decoded buffer to
       the file node instead of allocating and memcpy'ing a second equally large
       ArrayBuffer. We never mutate `data` after this call, which satisfies the
       canOwn contract. Keep the idle turn so even open/close/bookkeeping lands
       outside a hot render turn. */
    await waitForIdle();
    FS.writeFile(target, data, { canOwn: true });
    await sleep(INTER_ITEM_YIELD_MS);
    return { id: item.content_id, state: 'installed', installed_bytes: data.byteLength, target, zero_copy_memfs: true };
  };

  const installBundledContent = async (FS) => {
    const manifest = await getManifest();
    const items = orderedItems(manifest.items);
    window.__openttdBundledAddonsProgress = { total: items.length, completed: 0, current: null };

    const results = new Array(items.length);
    for (let index = 0; index < items.length; index++) {
      const item = items[index];
      window.__openttdBundledAddonsProgress.current = item.content_id;

      primePackedAsset(item, false);
      for (let ahead = 1; ahead <= NETWORK_PREFETCH_AHEAD; ahead++) {
        const nextItem = items[index + ahead];
        if (nextItem) primePackedAsset(nextItem, true);
      }

      try {
        results[index] = await installOne(FS, item);
      } catch (error) {
        results[index] = { id: item?.content_id || String(index), state: 'failed', error: String(error) };
      } finally {
        window.__openttdBundledAddonsProgress.completed += 1;
      }
    }

    window.__openttdBundledAddonsProgress.current = null;
    const failed = results.filter((row) => row?.state === 'failed');
    shutdownDecompressionWorker();
    window.__openttdBundledAddonsStatus = {
      manifest_version: manifest.manifest_version,
      installed: results.filter((row) => row?.state === 'installed').length,
      cached: results.filter((row) => row?.state === 'cached').length,
      failed,
      results,
      persistent: false,
      paced_writes: true,
      zero_copy_memfs: true,
      low_priority_network: true,
      network_prefetch_ahead: NETWORK_PREFETCH_AHEAD,
      adaptive_fetch_timeout: true,
      worker_decompression: true,
      worker_available: networkStats.workerAvailable,
      worker_inflates: networkStats.workerInflates,
      worker_fallbacks: networkStats.workerFallbacks,
      worker_terminated_after_install: networkStats.workerTerminatedAfterInstall,
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
        shutdownDecompressionWorker();
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
      // individual decompression/publication is additionally placed in idle.
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
