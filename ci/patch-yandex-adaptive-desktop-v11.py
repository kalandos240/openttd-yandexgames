#!/usr/bin/env python3
"""V11 desktop polish for the adaptive Yandex package.

- Pin desktop OpenTTD GUI scale to 100% so fullscreen does not enlarge the UI.
- Ask the Yandex Games SDK to hide sticky banners while gameplay is active.
  This is authoritative when Developer Console sticky banners are configured
  for API control; otherwise the parent Yandex page may still reserve/show the
  sticky rail and the game iframe cannot remove it itself.
"""
from __future__ import annotations
import argparse
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected one occurrence, found {count}')
    return text.replace(old, new, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()

    fixes = dist / 'openttd-yandex-fixes.js'
    bridge = dist / 'yandex-bridge.js'
    if not fixes.is_file() or not bridge.is_file():
        raise SystemExit('Missing adaptive V10 package files')

    f = fixes.read_text(encoding='utf-8')
    old = """    if (window.openttdMobileProfile?.touchUi) {
      setGlobal('gui_scale', Math.max(100, Math.min(500, guiScale)));
      setGui('osk_activation', 'immediately');
      setGui('left_mouse_btn_scrolling', '1');
      setGui('scroll_mode', '1');
      setGui('hover_delay_ms', '0');
      setGui('toolbar_pos', '1');
      setGui('statusbar_pos', '1');
    }
"""
    new = """    /* V11: touch keeps adaptive scaling; desktop is pinned to OpenTTD's
       native 100% minimum so fullscreen does not enlarge the toolbar. */
    if (window.openttdMobileProfile?.touchUi) {
      setGlobal('gui_scale', Math.max(100, Math.min(500, guiScale)));
      setGui('osk_activation', 'immediately');
      setGui('left_mouse_btn_scrolling', '1');
      setGui('scroll_mode', '1');
      setGui('hover_delay_ms', '0');
      setGui('toolbar_pos', '1');
      setGui('statusbar_pos', '1');
    } else {
      setGlobal('gui_scale', 100);
    }
"""
    f = replace_once(f, old, new, 'desktop gui scale block')
    fixes.write_text(f, encoding='utf-8')

    b = bridge.read_text(encoding='utf-8')
    anchor = """  function platformPauseEvent() {
"""
    sticky = r'''  /* V11: OpenTTD monetizes with fullscreen ads, so do not reserve a
     desktop/mobile sticky-banner rail around active gameplay. Yandex requires
     Developer Console -> Ads -> Sticky banners -> Use API for sticky banner
     before hideBannerAdv() is authoritative. */
  const __openttdStickySuppressionV11 = true;
  let stickyHideRetryTimer = 0;
  async function hideStickyBanner(reason = 'runtime') {
    try {
      const ysdk = await sdkReady;
      const adv = ysdk?.adv;
      if (!adv || typeof adv.hideBannerAdv !== 'function') {
        window.__openttdStickyBannerState = { hidden: false, reason: 'api-unavailable', trigger: reason };
        return false;
      }
      const result = await adv.hideBannerAdv();
      const hidden = result?.stickyAdvIsShowing === false;
      window.__openttdStickyBannerState = { hidden, trigger: reason, result };
      if (hidden) console.info('[Yandex/OpenTTD] Sticky banner hidden', reason);
      return hidden;
    } catch (error) {
      window.__openttdStickyBannerState = { hidden: false, reason: 'hide-error', trigger: reason };
      console.warn('[Yandex/OpenTTD] Sticky banner hide failed', reason, error);
      return false;
    }
  }
  window.yandexHideStickyBanner = hideStickyBanner;

  sdkReady.then(() => {
    hideStickyBanner('sdk-ready');
    let attempts = 0;
    stickyHideRetryTimer = setInterval(async () => {
      attempts++;
      if (await hideStickyBanner('startup-retry-' + attempts) || attempts >= 12) {
        clearInterval(stickyHideRetryTimer);
        stickyHideRetryTimer = 0;
      }
    }, 1000);
  });

  const hideStickyForViewport = () => hideStickyBanner('viewport-change');
  window.addEventListener('resize', hideStickyForViewport, { passive: true });
  document.addEventListener('fullscreenchange', hideStickyForViewport, { passive: true });

'''
    if '__openttdStickySuppressionV11' not in b:
        if b.count(anchor) != 1:
            raise SystemExit(f'sticky insertion anchor count={b.count(anchor)}')
        b = b.replace(anchor, sticky + anchor, 1)

    resume_old = """  function platformResumeEvent() {
    yandexPauseEventActive = false;
"""
    resume_new = """  function platformResumeEvent() {
    hideStickyBanner('game-api-resume');
    yandexPauseEventActive = false;
"""
    b = replace_once(b, resume_old, resume_new, 'resume sticky hide')
    bridge.write_text(b, encoding='utf-8')

    unpacked = sum(p.stat().st_size for p in dist.rglob('*') if p.is_file())
    if unpacked >= 100_000_000:
        raise SystemExit(f'Yandex package too large: {unpacked}')
    print(f'Adaptive V11 desktop/sticky fixes applied: unpacked_bytes={unpacked}')


if __name__ == '__main__':
    main()
