#!/usr/bin/env python3
from pathlib import Path

path = Path('ci/yandex-bridge.js')
text = path.read_text()

old = """  let pageVisible = !document.hidden;
  let yandexPauseEventActive = false;
  let platformGameplayStarted = false;
"""
new = """  let pageVisible = !document.hidden;
  let yandexPauseEventActive = false;
  let yandexPauseEventsBound = false;
  let platformGameplayStarted = false;
"""
if old not in text:
    raise SystemExit('Could not find Yandex pause state declarations')
text = text.replace(old, new, 1)

old = """  function platformPauseEvent() {
    yandexPauseEventActive = true;
    updatePlatformPause();
    setPlatformGameplay(false);
    suspendAudio();
  }

  function platformResumeEvent() {
    yandexPauseEventActive = false;
    pageVisible = !document.hidden;
    updatePlatformPause();
    resumeAudio();
    setPlatformGameplay(gameplayActive);
  }
"""
new = """  function platformPauseEvent() {
    yandexPauseEventActive = true;
    updatePlatformPause();
    suspendAudio();
    /* The Yandex platform itself temporarily applies GameplayAPI.stop() for
       game_api_pause and restores the previous markup state on resume. Do not
       send a duplicate stop/start pair here. */
  }

  function platformResumeEvent() {
    yandexPauseEventActive = false;
    pageVisible = !document.hidden;
    updatePlatformPause();
    resumeAudio();
    /* GameplayAPI state is restored by the platform for this event pair. */
  }
"""
if old not in text:
    raise SystemExit('Could not find Yandex pause/resume handlers')
text = text.replace(old, new, 1)

old = """  sdkReady.then(ysdk => {
    if (!ysdk || typeof ysdk.on !== 'function') return;
    try {
      ysdk.on('game_api_pause', platformPauseEvent);
      ysdk.on('game_api_resume', platformResumeEvent);
    } catch (e) {
      console.warn('Yandex pause/resume event subscription failed', e);
    }
  });
"""
new = """  sdkReady.then(ysdk => {
    if (!ysdk || typeof ysdk.on !== 'function') return;
    try {
      ysdk.on('game_api_pause', platformPauseEvent);
      ysdk.on('game_api_resume', platformResumeEvent);
      yandexPauseEventsBound = true;
    } catch (e) {
      console.warn('Yandex pause/resume event subscription failed', e);
    }

    /* When an anonymous player later signs in, Yandex can show the account
       selection dialog. Stop writes while it is open, then reload after the
       player has selected the authoritative progress track so the Player
       object and cloud snapshot are fetched again from a clean startup. */
    try {
      if (ysdk.EVENTS && ysdk.EVENTS.ACCOUNT_SELECTION_DIALOG_OPENED && ysdk.EVENTS.ACCOUNT_SELECTION_DIALOG_CLOSED) {
        ysdk.on(ysdk.EVENTS.ACCOUNT_SELECTION_DIALOG_OPENED, () => {
          window.yandexCloudSyncSuspended = true;
        });
        ysdk.on(ysdk.EVENTS.ACCOUNT_SELECTION_DIALOG_CLOSED, () => {
          window.yandexCloudSyncSuspended = false;
          playerPromise = null;
          setTimeout(() => location.reload(), 100);
        });
      }
    } catch (e) {
      console.warn('Yandex account selection event subscription failed', e);
    }
  });
"""
if old not in text:
    raise SystemExit('Could not find SDK event subscription block')
text = text.replace(old, new, 1)

old = """  async function flushCloud(FS, personalDir) {
    if (cloudWriteInFlight) {
"""
new = """  async function flushCloud(FS, personalDir) {
    if (window.yandexCloudSyncSuspended) {
      cloudWriteQueued = true;
      return;
    }
    if (cloudWriteInFlight) {
"""
if old not in text:
    raise SystemExit('Could not find cloud flush function')
text = text.replace(old, new, 1)

old = """  document.addEventListener('visibilitychange', () => {
    pageVisible = !document.hidden;
    updatePlatformPause();
    if (!pageVisible) {
      setPlatformGameplay(false);
      suspendAudio();
    } else {
      resumeAudio();
      setPlatformGameplay(gameplayActive);
    }
  });

  window.addEventListener('blur', () => {
    pageVisible = false;
    updatePlatformPause();
    setPlatformGameplay(false);
    suspendAudio();
  });

  window.addEventListener('focus', () => {
    pageVisible = !document.hidden;
    updatePlatformPause();
    resumeAudio();
    setPlatformGameplay(gameplayActive);
  });
"""
new = """  document.addEventListener('visibilitychange', () => {
    pageVisible = !document.hidden;
    updatePlatformPause();
    if (!pageVisible) {
      if (!yandexPauseEventsBound) setPlatformGameplay(false);
      suspendAudio();
    } else {
      resumeAudio();
      if (!yandexPauseEventsBound) setPlatformGameplay(gameplayActive);
    }
  });

  window.addEventListener('blur', () => {
    pageVisible = false;
    updatePlatformPause();
    if (!yandexPauseEventsBound) setPlatformGameplay(false);
    suspendAudio();
  });

  window.addEventListener('focus', () => {
    pageVisible = !document.hidden;
    updatePlatformPause();
    resumeAudio();
    if (!yandexPauseEventsBound) setPlatformGameplay(gameplayActive);
  });
"""
if old not in text:
    raise SystemExit('Could not find visibility/focus fallback handlers')
text = text.replace(old, new, 1)

path.write_text(text)
print('Yandex SDK pause/account-selection event handling patched.')
