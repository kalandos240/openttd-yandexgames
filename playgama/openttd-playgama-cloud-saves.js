/* Playgama-native cloud saves for the OpenTTD browser port.
 *
 * Replaces the legacy Yandex Player-data snapshot with Bridge v2
 * platform_internal storage. Saves are split into bounded text chunks and
 * written to alternating A/B slots. Slot metadata is committed only after all
 * chunks are present, so an interrupted upload leaves the previous cloud save
 * intact. Local IDBFS remains authoritative when it is newer.
 */
(() => {
  'use strict';
  if (window.__openttdPlaygamaCloudSavesInstalled) return;
  window.__openttdPlaygamaCloudSavesInstalled = true;

  const CLOUD_VERSION = 2;
  const CONFIG_KEY = 'openttdConfigV2';
  const LEGACY_CONFIG_KEY = 'openttdConfigV1';
  const LEGACY_SAVE_KEY = 'openttdSaveV1';
  const SLOT_META = {
    a: 'openttdSaveMetaV2A',
    b: 'openttdSaveMetaV2B',
  };
  const CHUNK_PREFIX = {
    a: 'openttdSaveChunkV2A_',
    b: 'openttdSaveChunkV2B_',
  };
  const CHUNK_CHARS = 64 * 1024;
  const READ_BATCH = 16;
  const WRITE_BATCH = 4;
  const MAX_SAVE_BYTES = 64 * 1024 * 1024; // browser safety guard, not a platform quota
  const CLOUD_DEBOUNCE_MS = 2500;
  const CLOUD_MIN_WRITE_MS = 10000;
  const RESTORE_STARTUP_BUDGET_MS = 6500;
  const STORAGE_REQUEST_TIMEOUT_MS = 5000;

  let cloudTimer = 0;
  let cloudWriteInFlight = false;
  let cloudWriteQueued = false;
  let lastCloudWriteAt = 0;
  let storageInfoPromise = null;
  let latestRemoteMeta = null;

  const bridgeReady = window.playgamaBridgeReady || Promise.resolve(window.bridge || null);

  function deadlinePromise(promise, timeoutMs) {
    let timeoutId;
    return Promise.race([
      Promise.resolve(promise),
      new Promise((_, reject) => {
        timeoutId = setTimeout(() => reject(new Error('Playgama storage request timeout')), Math.max(1, timeoutMs));
      }),
    ]).finally(() => clearTimeout(timeoutId));
  }

  function remainingBudget(deadline) {
    const left = deadline - Date.now();
    if (left <= 0) throw new Error('Playgama cloud restore exceeded startup budget');
    return Math.min(left, STORAGE_REQUEST_TIMEOUT_MS);
  }

  function ensureDir(FS, path) {
    let current = '';
    for (const part of String(path).split('/').filter(Boolean)) {
      current += '/' + part;
      try { FS.mkdir(current); } catch (_) {}
    }
  }

  function statTime(stat) {
    try {
      if (!stat || stat.mtime == null) return 0;
      return Number(stat.mtime) || 0;
    } catch (_) {
      return 0;
    }
  }

  function listFilesRecursive(FS, root, output = []) {
    let entries;
    try { entries = FS.readdir(root); } catch (_) { return output; }
    for (const name of entries) {
      if (name === '.' || name === '..') continue;
      const path = root.replace(/\/$/, '') + '/' + name;
      let stat;
      try { stat = FS.stat(path); } catch (_) { continue; }
      if (FS.isDir(stat.mode)) listFilesRecursive(FS, path, output);
      else if (FS.isFile(stat.mode)) output.push({ path, stat });
    }
    return output;
  }

  function newestSave(FS, personalDir) {
    const candidates = listFilesRecursive(FS, personalDir + '/save')
      .filter((item) => /\.sav$/i.test(item.path))
      .sort((a, b) => statTime(b.stat) - statTime(a.stat));
    return candidates[0] || null;
  }

  function bytesToBase64(bytes) {
    let binary = '';
    const step = 0x8000;
    for (let i = 0; i < bytes.length; i += step) {
      binary += String.fromCharCode(...bytes.subarray(i, Math.min(bytes.length, i + step)));
    }
    return btoa(binary);
  }

  function base64ToBytes(value) {
    const binary = atob(String(value || ''));
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes;
  }

  function crc32(bytes) {
    let crc = 0xFFFFFFFF;
    for (let i = 0; i < bytes.length; i++) {
      crc ^= bytes[i];
      for (let bit = 0; bit < 8; bit++) {
        crc = (crc >>> 1) ^ ((crc & 1) ? 0xEDB88320 : 0);
      }
    }
    return ((crc ^ 0xFFFFFFFF) >>> 0).toString(16).padStart(8, '0');
  }

  function safeSaveName(name) {
    const cleaned = String(name || 'cloud-save.sav').replace(/[^A-Za-z0-9_. ()\-]/g, '_');
    return /\.sav$/i.test(cleaned) ? cleaned : cleaned + '.sav';
  }

  function sanitizeConfig(config) {
    return String(config || '');
  }

  function readConfig(FS, personalDir) {
    try { return sanitizeConfig(FS.readFile(personalDir + '/openttd.cfg', { encoding: 'utf8' })); }
    catch (_) { return ''; }
  }

  async function resolveStorageInfo() {
    if (storageInfoPromise) return storageInfoPromise;
    storageInfoPromise = (async () => {
      const bridge = await bridgeReady;
      if (!bridge?.storage) return null;

      const internalType = bridge.STORAGE_TYPE?.PLATFORM_INTERNAL || 'platform_internal';
      let supported = true;
      let available = true;
      try {
        if (typeof bridge.storage.isSupported === 'function') {
          supported = (await Promise.resolve(bridge.storage.isSupported(internalType))) !== false;
        }
      } catch (_) { supported = false; }
      try {
        if (typeof bridge.storage.isAvailable === 'function') {
          available = (await Promise.resolve(bridge.storage.isAvailable(internalType))) !== false;
        }
      } catch (_) { available = false; }

      if (!supported || !available) {
        console.info('[Playgama/OpenTTD] platform_internal storage is unavailable; using local IndexedDB saves only.');
        return null;
      }
      return { bridge, type: internalType };
    })();
    return storageInfoPromise;
  }

  // Bridge v2 requires array arguments even for a single key. A rejected
  // read/write is NEVER a successful cloud save: keep the last committed slot.
  async function storageGet(keys, deadline) {
    const info = await resolveStorageInfo();
    if (!info) return Array.isArray(keys) ? [] : null;
    const requested = (Array.isArray(keys) ? keys : [keys]).map(String);
    if (!requested.length) return Array.isArray(keys) ? [] : null;
    const timeout = deadline ? remainingBudget(deadline) : STORAGE_REQUEST_TIMEOUT_MS;
    const values = await deadlinePromise(
      info.bridge.storage.get(requested, info.type), timeout);
    if (!Array.isArray(values) || values.length !== requested.length) {
      throw new Error('Playgama storage returned a malformed result');
    }
    return Array.isArray(keys) ? values : values[0];
  }

  async function storageSet(keys, values) {
    const info = await resolveStorageInfo();
    if (!info) return false;
    const keyList = (Array.isArray(keys) ? keys : [keys]).map(String);
    const valueList = Array.isArray(keys) ? values : [values];
    if (keyList.length !== valueList.length) throw new Error('Cloud storage key/value length mismatch');
    if (!keyList.length) return true;
    await deadlinePromise(
      info.bridge.storage.set(keyList, valueList, info.type),
      STORAGE_REQUEST_TIMEOUT_MS);
    return true;
  }

  async function readSlotMetas(deadline) {
    const values = await storageGet([SLOT_META.a, SLOT_META.b], deadline);
    const metas = [];
    for (let i = 0; i < 2; i++) {
      const slot = i === 0 ? 'a' : 'b';
      const meta = Array.isArray(values) ? values[i] : null;
      if (!meta || Number(meta.version) !== CLOUD_VERSION || meta.slot !== slot) continue;
      const chunks = Number(meta.chunks);
      const size = Number(meta.size);
      if (!Number.isInteger(chunks) || chunks <= 0 || !Number.isFinite(size) || size <= 0 || size > MAX_SAVE_BYTES) continue;
      metas.push(meta);
    }
    metas.sort((x, y) => Number(y.mtime || y.updatedAt || 0) - Number(x.mtime || x.updatedAt || 0));
    latestRemoteMeta = metas[0] || null;
    return metas;
  }

  function metaMatchesLocal(meta, save, bytesLength) {
    if (!meta || !save) return false;
    const localName = save.path.split('/').pop();
    const localMtime = statTime(save.stat);
    return meta.name === localName && Number(meta.size) === Number(bytesLength) &&
      Number(meta.mtime) === Number(localMtime) && meta.crc32 === crc32(save.bytes);
  }

  async function readSlotBytes(meta, deadline) {
    const keys = [];
    for (let i = 0; i < meta.chunks; i++) {
      keys.push(CHUNK_PREFIX[meta.slot] + String(i).padStart(4, '0'));
    }

    const chunks = new Array(keys.length);
    for (let start = 0; start < keys.length; start += READ_BATCH) {
      const batchKeys = keys.slice(start, start + READ_BATCH);
      const values = await storageGet(batchKeys, deadline);
      const batchValues = Array.isArray(values) ? values : [values];
      for (let i = 0; i < batchKeys.length; i++) {
        if (typeof batchValues[i] !== 'string' || !batchValues[i].length) {
          throw new Error(`Missing cloud chunk ${batchKeys[i]}`);
        }
        chunks[start + i] = batchValues[i];
      }
    }

    const base64 = chunks.join('');
    if (Number(meta.base64Length) && base64.length !== Number(meta.base64Length)) {
      throw new Error(`Cloud base64 length mismatch: expected ${meta.base64Length}, got ${base64.length}`);
    }
    const bytes = base64ToBytes(base64);
    if (bytes.length !== Number(meta.size)) {
      throw new Error(`Cloud save size mismatch: expected ${meta.size}, got ${bytes.length}`);
    }
    if (meta.crc32 && crc32(bytes) !== String(meta.crc32)) {
      throw new Error('Cloud save CRC32 mismatch');
    }
    return bytes;
  }

  async function restoreV2Save(FS, personalDir, metas, deadline) {
    const localSave = newestSave(FS, personalDir);
    const localMtime = localSave ? statTime(localSave.stat) : 0;

    for (const meta of metas) {
      const cloudMtime = Number(meta.mtime || meta.updatedAt || 0);
      if (localSave && localMtime >= cloudMtime) return false;
      try {
        const bytes = await readSlotBytes(meta, deadline);
        remainingBudget(deadline); // Never write a late cloud restore into a live game.
        const saveDir = personalDir + '/save';
        ensureDir(FS, saveDir);
        const name = safeSaveName(meta.name);
        const savePath = saveDir + '/' + name;
        FS.writeFile(savePath, bytes);
        try {
          const date = new Date(cloudMtime || Date.now());
          FS.utime(savePath, date, date);
        } catch (_) {}
        latestRemoteMeta = meta;
        console.info(`[Playgama/OpenTTD] Restored cloud save ${name} (${bytes.length} bytes, slot ${meta.slot.toUpperCase()}).`);
        return true;
      } catch (error) {
        console.warn(`[Playgama/OpenTTD] Cloud slot ${meta.slot.toUpperCase()} is invalid; trying fallback slot.`, error);
      }
    }
    return false;
  }

  function restoreLegacySave(FS, personalDir, legacy, deadline) {
    if (!legacy || Number(legacy.version) !== 1 || !legacy.data || !legacy.name) return false;
    try {
      const localSave = newestSave(FS, personalDir);
      const localMtime = localSave ? statTime(localSave.stat) : 0;
      const cloudMtime = Number(legacy.mtime || legacy.updatedAt || 0);
      if (localSave && localMtime >= cloudMtime) return false;
      const bytes = base64ToBytes(legacy.data);
      if (!bytes.length || bytes.length > MAX_SAVE_BYTES) return false;
      remainingBudget(deadline);
      const saveDir = personalDir + '/save';
      ensureDir(FS, saveDir);
      const name = safeSaveName(legacy.name);
      const savePath = saveDir + '/' + name;
      FS.writeFile(savePath, bytes);
      try {
        const date = new Date(cloudMtime || Date.now());
        FS.utime(savePath, date, date);
      } catch (_) {}
      console.info(`[Playgama/OpenTTD] Migrated legacy cloud save ${name} (${bytes.length} bytes).`);
      return true;
    } catch (error) {
      console.warn('[Playgama/OpenTTD] Legacy cloud save restore failed.', error);
      return false;
    }
  }

  function restoreConfig(FS, personalDir, config) {
    const text = config && typeof config.config === 'string' ? config.config : null;
    if (text == null) return false;
    const path = personalDir + '/openttd.cfg';
    let local = '';
    try { local = FS.readFile(path, { encoding: 'utf8' }); } catch (_) {}
    if (local.trim()) return false;
    try {
      FS.writeFile(path, sanitizeConfig(text));
      return true;
    } catch (_) {
      return false;
    }
  }

  async function writeConfig(FS, personalDir) {
    const config = {
      version: CLOUD_VERSION,
      updatedAt: Date.now(),
      config: readConfig(FS, personalDir),
    };
    await storageSet(CONFIG_KEY, config);
  }

  async function writeSave(FS, personalDir) {
    const save = newestSave(FS, personalDir);
    if (!save) return { state: 'no-save' };

    let bytes;
    try { bytes = FS.readFile(save.path); }
    catch (error) { throw new Error(`Could not read local save: ${error}`); }
    if (!bytes?.length) return { state: 'empty-save' };
    if (bytes.length > MAX_SAVE_BYTES) {
      console.warn(`[Playgama/OpenTTD] Save is ${bytes.length} bytes; cloud upload skipped above ${MAX_SAVE_BYTES} byte browser safety guard.`);
      return { state: 'too-large', bytes: bytes.length };
    }

    const metas = await readSlotMetas();
    const current = metas[0] || latestRemoteMeta;
    if (metaMatchesLocal(current, { ...save, bytes }, bytes.length)) {
      return { state: 'unchanged', bytes: bytes.length };
    }

    const targetSlot = current?.slot === 'a' ? 'b' : 'a';
    const base64 = bytesToBase64(bytes);
    const chunks = [];
    for (let i = 0; i < base64.length; i += CHUNK_CHARS) chunks.push(base64.slice(i, i + CHUNK_CHARS));
    if (!chunks.length) return { state: 'empty-save' };

    for (let start = 0; start < chunks.length; start += WRITE_BATCH) {
      const keys = [];
      const values = [];
      for (let i = start; i < Math.min(chunks.length, start + WRITE_BATCH); i++) {
        keys.push(CHUNK_PREFIX[targetSlot] + String(i).padStart(4, '0'));
        values.push(chunks[i]);
      }
      await storageSet(keys, values);
    }

    const meta = {
      version: CLOUD_VERSION,
      slot: targetSlot,
      updatedAt: Date.now(),
      name: save.path.split('/').pop(),
      mtime: statTime(save.stat) || Date.now(),
      size: bytes.length,
      base64Length: base64.length,
      chunks: chunks.length,
      chunkChars: CHUNK_CHARS,
      crc32: crc32(bytes),
    };

    /* Commit metadata last. If a chunk write fails, the previous slot remains
       the newest valid generation and restore never points at the partial data. */
    await storageSet(SLOT_META[targetSlot], meta);
    latestRemoteMeta = meta;
    console.info(`[Playgama/OpenTTD] Cloud save uploaded: ${meta.name}, ${meta.size} bytes, ${meta.chunks} chunks, slot ${targetSlot.toUpperCase()}.`);
    return { state: 'uploaded', bytes: bytes.length, chunks: chunks.length, slot: targetSlot };
  }

  function persistRestoredStateAfterStartup(FS) {
    const persist = () => {
      const module = window.Module;
      if (!module || module.calledRun !== true) {
        setTimeout(persist, 100);
        return;
      }
      const flush = () => {
        try {
          if (typeof FS.syncfs !== 'function') return;
          FS.syncfs(false, (error) => {
            if (error) console.warn('[Playgama/OpenTTD] Deferred cloud restore persistence failed.', error);
          });
        } catch (error) {
          console.warn('[Playgama/OpenTTD] Deferred cloud restore persistence threw.', error);
        }
      };
      if (typeof window.requestIdleCallback === 'function') {
        window.requestIdleCallback(flush, { timeout: 5000 });
      } else {
        setTimeout(flush, 500);
      }
    };

    const module = window.Module;
    if (module && module.calledRun === true) {
      setTimeout(persist, 0);
    } else if (module && Array.isArray(module.postRun)) {
      module.postRun.push(persist);
    } else {
      setTimeout(persist, 0);
    }
  }

  window.yandexRestoreOpenTTDCloud = async function(FS, personalDir) {
    const deadline = Date.now() + RESTORE_STARTUP_BUDGET_MS;
    try {
      const info = await deadlinePromise(resolveStorageInfo(), remainingBudget(deadline));
      if (!info) {
        window.__openttdPlaygamaCloudStatus = { available: false, reason: 'platform_internal unavailable; local IDBFS active' };
        return;
      }
      const configValues = await storageGet(
        [CONFIG_KEY, LEGACY_CONFIG_KEY, 'openttdMobileConfigV1'], deadline);
      if (Array.isArray(configValues)) {
        restoreConfig(FS, personalDir, configValues[0]);
        if (!configValues[0]) restoreConfig(FS, personalDir, configValues[2] || configValues[1]);
      }

      const metas = await readSlotMetas(deadline);
      let restored = false;
      if (metas.length) restored = await restoreV2Save(FS, personalDir, metas, deadline);

      if (!restored && !metas.length) {
        const legacy = await storageGet(LEGACY_SAVE_KEY, deadline);
        restored = restoreLegacySave(FS, personalDir, legacy, deadline);
      }

      if (restored) {
        // MEMFS contains the restored save; flush only after native OpenTTD
        // starts so a second IDBFS operation cannot block cold startup.
        persistRestoredStateAfterStartup(FS);
      }
      window.__openttdPlaygamaCloudStatus = {
        available: true, restored, version: CLOUD_VERSION, latest: latestRemoteMeta,
      };
    } catch (error) {
      window.__openttdPlaygamaCloudStatus = { available: false, restored: false, error: String(error) };
      console.warn('[Playgama/OpenTTD] Cloud restore skipped; local IndexedDB save remains intact.', error);
    }
  };

  async function flushCloud(FS, personalDir) {
    if (window.yandexCloudSyncSuspended) {
      cloudWriteQueued = true;
      return;
    }
    if (cloudWriteInFlight) {
      cloudWriteQueued = true;
      return;
    }

    const wait = CLOUD_MIN_WRITE_MS - (Date.now() - lastCloudWriteAt);
    if (wait > 0) {
      clearTimeout(cloudTimer);
      cloudTimer = setTimeout(() => flushCloud(FS, personalDir), wait);
      return;
    }

    cloudWriteInFlight = true;
    try {
      const info = await resolveStorageInfo();
      if (!info) return;
      await writeConfig(FS, personalDir);
      const result = await writeSave(FS, personalDir);
      lastCloudWriteAt = Date.now();
      window.__openttdPlaygamaCloudStatus = {
        available: true,
        version: CLOUD_VERSION,
        backup: result,
        latest: latestRemoteMeta,
      };
    } catch (error) {
      window.__openttdPlaygamaCloudStatus = { available: true, version: CLOUD_VERSION, error: String(error) };
      console.warn('[Playgama/OpenTTD] Cloud backup failed; local IndexedDB save remains intact.', error);
    } finally {
      cloudWriteInFlight = false;
      if (cloudWriteQueued) {
        cloudWriteQueued = false;
        clearTimeout(cloudTimer);
        cloudTimer = setTimeout(() => flushCloud(FS, personalDir), CLOUD_DEBOUNCE_MS);
      }
    }
  }

  window.yandexBackupOpenTTDCloud = function(FS, personalDir) {
    clearTimeout(cloudTimer);
    cloudTimer = setTimeout(() => flushCloud(FS, personalDir), CLOUD_DEBOUNCE_MS);
  };

  window.__openttdPlaygamaCloudDebug = {
    version: CLOUD_VERSION,
    chunkChars: CHUNK_CHARS,
    maxSaveBytes: MAX_SAVE_BYTES,
    forceBackup(FS, personalDir) { lastCloudWriteAt = 0; return flushCloud(FS, personalDir); },
    restore(FS, personalDir) { return window.yandexRestoreOpenTTDCloud(FS, personalDir); },
  };

  console.info('[Playgama/OpenTTD] Native chunked cloud saves v2 installed.');
})();
