#!/usr/bin/env python3
"""Add adaptive mobile/tablet support to the verified Yandex publication package.

The mobile layer keeps desktop behavior intact and uses Yandex SDK deviceInfo as
its primary device-category signal. Exact handset model detection is optional
and never required for layout decisions.
"""
from __future__ import annotations

import argparse
from pathlib import Path

MOBILE_JS = r'''(() => {
  'use strict';
  if (window.__openttdYandexMobileInstalled) return;
  window.__openttdYandexMobileInstalled = true;

  const CONFIG_NAME = 'openttd-mobile.cfg';
  const CONFIG_PATH = '/home/web_user/.openttd/' + CONFIG_NAME;
  window.openttdConfigFilename = CONFIG_NAME;

  /* Keep mobile presentation settings separate from the desktop profile while
     sharing the same save directory. OpenTTD supports an explicit -c config. */
  window.Module = window.Module || {};
  window.Module.arguments = Array.isArray(window.Module.arguments) ? window.Module.arguments : [];
  if (!window.Module.arguments.includes('-c')) window.Module.arguments.push('-c', CONFIG_PATH);

  const media = query => {
    try { return !!window.matchMedia(query).matches; } catch (_) { return false; }
  };

  const initialMobileHint = () => {
    const uaMobile = navigator.userAgentData && typeof navigator.userAgentData.mobile === 'boolean'
      ? navigator.userAgentData.mobile : false;
    const touch = Number(navigator.maxTouchPoints || 0) > 0;
    const coarse = media('(pointer: coarse)') || media('(any-pointer: coarse)');
    const noHover = media('(hover: none)');
    return !!(uaMobile || (touch && coarse && noHover));
  };

  let sdkDeviceType = '';
  let sdkDeviceReady = false;
  const profile = {
    deviceType: initialMobileHint() ? 'mobile' : 'desktop',
    model: '',
    platform: navigator.userAgentData?.platform || navigator.platform || '',
    mobileHint: initialMobileHint(),
    maxTouchPoints: Number(navigator.maxTouchPoints || 0),
    coarsePointer: media('(pointer: coarse)') || media('(any-pointer: coarse)'),
    hoverNone: media('(hover: none)'),
    dpr: Number(window.devicePixelRatio || 1),
  };
  window.openttdMobileProfile = profile;

  const publishProfile = () => {
    const type = sdkDeviceReady && sdkDeviceType ? sdkDeviceType : profile.deviceType;
    profile.deviceType = type;
    profile.isMobile = type === 'mobile';
    profile.isTablet = type === 'tablet';
    profile.isDesktop = type === 'desktop';
    profile.isTV = type === 'tv';
    profile.touchUi = profile.isMobile || profile.isTablet || (profile.mobileHint && profile.maxTouchPoints > 0);
    const shortSide = Math.min(window.visualViewport?.width || innerWidth || 0, window.visualViewport?.height || innerHeight || 0);
    profile.guiScale = profile.touchUi ? (shortSide < 360 ? 150 : shortSide < 520 ? 175 : 200) : 100;
    window.openttdRecommendedGuiScale = profile.guiScale;
    document.documentElement.classList.toggle('openttd-touch-ui', !!profile.touchUi);
    document.documentElement.classList.toggle('openttd-mobile', !!profile.isMobile);
    document.documentElement.classList.toggle('openttd-tablet', !!profile.isTablet);
    window.dispatchEvent(new CustomEvent('openttd-mobile-profile', { detail: { ...profile } }));
  };

  publishProfile();

  Promise.resolve(window.yandexGamesSDKReady).then(async ysdk => {
    try {
      const info = ysdk && ysdk.deviceInfo;
      if (info) {
        sdkDeviceType = String(info.type || '');
        if (!sdkDeviceType) {
          if (typeof info.isMobile === 'function' && info.isMobile()) sdkDeviceType = 'mobile';
          else if (typeof info.isTablet === 'function' && info.isTablet()) sdkDeviceType = 'tablet';
          else if (typeof info.isTV === 'function' && info.isTV()) sdkDeviceType = 'tv';
          else if (typeof info.isDesktop === 'function' && info.isDesktop()) sdkDeviceType = 'desktop';
        }
        sdkDeviceReady = true;
        publishProfile();
      }
    } catch (error) {
      console.warn('[OpenTTD mobile] Yandex deviceInfo unavailable', error);
    }

    /* Browser high-entropy hints may expose an Android model. iOS generally
       does not expose an exact model; layout never depends on this field. */
    try {
      if (navigator.userAgentData?.getHighEntropyValues) {
        const hints = await navigator.userAgentData.getHighEntropyValues(['model', 'platform', 'platformVersion']);
        profile.model = String(hints.model || '');
        profile.platform = String(hints.platform || profile.platform || '');
        profile.platformVersion = String(hints.platformVersion || '');
        publishProfile();
      }
    } catch (_) {}
  });

  const addMobileCss = () => {
    const style = document.createElement('style');
    style.id = 'openttd-mobile-adaptive-style';
    style.textContent = `
      html, body { margin: 0 !important; padding: 0 !important; width: 100%; height: 100%; overflow: hidden !important; overscroll-behavior: none !important; }
      html.openttd-touch-ui, html.openttd-touch-ui body { touch-action: none !important; -webkit-text-size-adjust: 100%; }
      html.openttd-touch-ui canvas.emscripten { touch-action: none !important; -webkit-user-select: none !important; user-select: none !important; -webkit-touch-callout: none !important; }
    `;
    document.head.appendChild(style);
  };
  addMobileCss();

  const safeAreaProbe = () => {
    let probe = document.getElementById('openttd-safe-area-probe');
    if (!probe) {
      probe = document.createElement('div');
      probe.id = 'openttd-safe-area-probe';
      probe.setAttribute('aria-hidden', 'true');
      probe.style.cssText = 'position:absolute;visibility:hidden;pointer-events:none;padding-top:env(safe-area-inset-top);padding-right:env(safe-area-inset-right);padding-bottom:env(safe-area-inset-bottom);padding-left:env(safe-area-inset-left);';
      document.documentElement.appendChild(probe);
    }
    const cs = getComputedStyle(probe);
    const px = value => Math.max(0, parseFloat(value) || 0);
    return { top: px(cs.paddingTop), right: px(cs.paddingRight), bottom: px(cs.paddingBottom), left: px(cs.paddingLeft) };
  };
  window.openttdGetSafeAreaInsets = safeAreaProbe;

  const updateDynamicProfile = () => {
    profile.dpr = Number(window.devicePixelRatio || 1);
    profile.screen = { width: Number(screen.width || 0), height: Number(screen.height || 0) };
    profile.viewport = {
      width: Number(window.visualViewport?.width || innerWidth || 0),
      height: Number(window.visualViewport?.height || innerHeight || 0),
      offsetLeft: Number(window.visualViewport?.offsetLeft || 0),
      offsetTop: Number(window.visualViewport?.offsetTop || 0),
    };
    profile.orientation = profile.viewport.width >= profile.viewport.height ? 'landscape' : 'portrait';
    profile.safeArea = safeAreaProbe();
    publishProfile();
  };
  window.addEventListener('resize', updateDynamicProfile, { passive: true });
  window.visualViewport?.addEventListener('resize', updateDynamicProfile, { passive: true });
  window.visualViewport?.addEventListener('scroll', updateDynamicProfile, { passive: true });
  screen.orientation?.addEventListener?.('change', updateDynamicProfile, { passive: true });
  updateDynamicProfile();

  /* Ask Yandex fullscreen on the first deliberate touch. Browsers that forbid
     the transition simply reject it; Yandex's own fullscreen control remains. */
  let fullscreenAttempted = false;
  const requestFullscreenOnGesture = async event => {
    if (fullscreenAttempted || !event.isTrusted || !profile.touchUi) return;
    fullscreenAttempted = true;
    try {
      const ysdk = await window.yandexGamesSDKReady;
      const fullscreen = ysdk?.screen?.fullscreen;
      if (fullscreen && fullscreen.status !== fullscreen.STATUS_ON && typeof fullscreen.request === 'function') {
        await fullscreen.request();
      }
    } catch (_) {}
  };
  window.addEventListener('pointerup', requestFullscreenOnGesture, { capture: true, passive: true, once: false });

  const mouseEvent = (canvas, type, x, y, button = 0, buttons = 0) => {
    canvas.dispatchEvent(new MouseEvent(type, {
      bubbles: true, cancelable: true, view: window,
      clientX: x, clientY: y, screenX: x, screenY: y,
      button, buttons,
    }));
  };

  const wheelEvent = (canvas, x, y, deltaY) => {
    canvas.dispatchEvent(new WheelEvent('wheel', {
      bubbles: true, cancelable: true, view: window,
      clientX: x, clientY: y, deltaY, deltaMode: WheelEvent.DOM_DELTA_PIXEL,
    }));
  };

  const installTouchBridge = () => {
    const canvas = document.getElementById('canvas');
    if (!canvas || canvas.__openttdTouchBridgeInstalled) return;
    canvas.__openttdTouchBridgeInstalled = true;

    const pointers = new Map();
    let primaryId = null;
    let down = null;
    let dragging = false;
    let longPressTimer = 0;
    let longPressFired = false;
    let pinchDistance = 0;
    const DRAG_THRESHOLD = 7;
    const LONG_PRESS_MS = 520;

    const clearLongPress = () => {
      if (longPressTimer) clearTimeout(longPressTimer);
      longPressTimer = 0;
    };

    const point = e => ({ x: e.clientX, y: e.clientY, t: performance.now() });
    const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
    const center = (a, b) => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 });

    const beginLongPress = () => {
      clearLongPress();
      longPressTimer = setTimeout(() => {
        if (!down || dragging || pointers.size !== 1) return;
        longPressFired = true;
        mouseEvent(canvas, 'mousemove', down.x, down.y, 0, 0);
        mouseEvent(canvas, 'mousedown', down.x, down.y, 2, 2);
        mouseEvent(canvas, 'mouseup', down.x, down.y, 2, 0);
      }, LONG_PRESS_MS);
    };

    const stopNativeTouch = e => {
      if (!profile.touchUi || (e.pointerType !== 'touch' && e.pointerType !== 'pen')) return false;
      e.preventDefault();
      e.stopImmediatePropagation();
      return true;
    };

    canvas.addEventListener('pointerdown', e => {
      if (!stopNativeTouch(e)) return;
      try { canvas.setPointerCapture(e.pointerId); } catch (_) {}
      pointers.set(e.pointerId, point(e));
      if (pointers.size === 1) {
        primaryId = e.pointerId;
        down = point(e);
        dragging = false;
        longPressFired = false;
        pinchDistance = 0;
        beginLongPress();
      } else if (pointers.size === 2) {
        clearLongPress();
        if (dragging && down) mouseEvent(canvas, 'mouseup', e.clientX, e.clientY, 0, 0);
        dragging = false;
        const pts = [...pointers.values()];
        pinchDistance = distance(pts[0], pts[1]);
      }
    }, { capture: true, passive: false });

    canvas.addEventListener('pointermove', e => {
      if (!stopNativeTouch(e) || !pointers.has(e.pointerId)) return;
      const p = point(e);
      pointers.set(e.pointerId, p);

      if (pointers.size >= 2) {
        clearLongPress();
        const pts = [...pointers.values()].slice(0, 2);
        const nextDistance = distance(pts[0], pts[1]);
        if (pinchDistance > 0 && Math.abs(nextDistance - pinchDistance) >= 10) {
          const c = center(pts[0], pts[1]);
          wheelEvent(canvas, c.x, c.y, nextDistance > pinchDistance ? -100 : 100);
          pinchDistance = nextDistance;
        }
        return;
      }

      if (e.pointerId !== primaryId || !down || longPressFired) return;
      const moved = Math.hypot(p.x - down.x, p.y - down.y);
      if (!dragging && moved >= DRAG_THRESHOLD) {
        clearLongPress();
        dragging = true;
        mouseEvent(canvas, 'mousemove', down.x, down.y, 0, 0);
        mouseEvent(canvas, 'mousedown', down.x, down.y, 0, 1);
      }
      if (dragging) mouseEvent(canvas, 'mousemove', p.x, p.y, 0, 1);
    }, { capture: true, passive: false });

    const finishPointer = e => {
      if (!stopNativeTouch(e)) return;
      const p = point(e);
      const wasPrimary = e.pointerId === primaryId;
      pointers.delete(e.pointerId);
      try { canvas.releasePointerCapture(e.pointerId); } catch (_) {}
      clearLongPress();

      if (wasPrimary && down) {
        if (dragging) {
          mouseEvent(canvas, 'mousemove', p.x, p.y, 0, 1);
          mouseEvent(canvas, 'mouseup', p.x, p.y, 0, 0);
        } else if (!longPressFired && pointers.size === 0) {
          mouseEvent(canvas, 'mousemove', p.x, p.y, 0, 0);
          mouseEvent(canvas, 'mousedown', p.x, p.y, 0, 1);
          mouseEvent(canvas, 'mouseup', p.x, p.y, 0, 0);
        }
      }

      if (pointers.size === 0) {
        primaryId = null;
        down = null;
        dragging = false;
        longPressFired = false;
        pinchDistance = 0;
      } else if (pointers.size === 1) {
        const [id, remaining] = pointers.entries().next().value;
        primaryId = id;
        down = { ...remaining };
        dragging = false;
        longPressFired = false;
        pinchDistance = 0;
        beginLongPress();
      }
    };

    canvas.addEventListener('pointerup', finishPointer, { capture: true, passive: false });
    canvas.addEventListener('pointercancel', finishPointer, { capture: true, passive: false });
    canvas.addEventListener('contextmenu', e => e.preventDefault(), { capture: true });
    canvas.addEventListener('touchstart', e => { if (profile.touchUi) e.preventDefault(); }, { passive: false, capture: true });
    canvas.addEventListener('touchmove', e => { if (profile.touchUi) e.preventDefault(); }, { passive: false, capture: true });

    console.info('[OpenTTD mobile] Touch bridge installed', profile);
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', installTouchBridge, { once: true });
  else installTouchBridge();
  const touchStartup = setInterval(() => {
    const canvas = document.getElementById('canvas');
    if (canvas?.__openttdTouchBridgeInstalled) clearInterval(touchStartup);
    else installTouchBridge();
  }, 250);
})();
'''

VIEWPORT_JS = r'''/* Adaptive OpenTTD canvas sizing for Yandex desktop + mobile.
 * Desktop retains the moderation-safe 2:1 maximum active-field ratio.
 * Mobile/tablet uses the real visual viewport and safe-area insets so the game
 * fills the usable screen without stretching or drawing controls under a notch.
 */
(() => {
  'use strict';
  if (window.__openttdAdaptiveViewportInstalled) return;
  window.__openttdAdaptiveViewportInstalled = true;

  const MAX_DESKTOP_ASPECT_RATIO = 2;

  const viewportRect = () => {
    const vv = window.visualViewport;
    const width = Math.max(64, Math.round(vv?.width || innerWidth || document.documentElement.clientWidth || 1280));
    const height = Math.max(64, Math.round(vv?.height || innerHeight || document.documentElement.clientHeight || 720));
    const offsetLeft = Math.max(0, Math.round(vv?.offsetLeft || 0));
    const offsetTop = Math.max(0, Math.round(vv?.offsetTop || 0));
    return { width, height, offsetLeft, offsetTop };
  };

  const layout = () => {
    const viewport = viewportRect();
    const profile = window.openttdMobileProfile || {};
    const touchUi = !!profile.touchUi;
    const safe = touchUi && typeof window.openttdGetSafeAreaInsets === 'function'
      ? window.openttdGetSafeAreaInsets() : { top: 0, right: 0, bottom: 0, left: 0 };

    let cssWidth = Math.max(64, Math.round(viewport.width - safe.left - safe.right));
    let cssHeight = Math.max(64, Math.round(viewport.height - safe.top - safe.bottom));
    let left = viewport.offsetLeft + Math.round(safe.left);
    let top = viewport.offsetTop + Math.round(safe.top);

    if (!touchUi) {
      if (cssWidth / cssHeight > MAX_DESKTOP_ASPECT_RATIO) {
        const next = Math.round(cssHeight * MAX_DESKTOP_ASPECT_RATIO);
        left += Math.round((cssWidth - next) / 2);
        cssWidth = next;
      }
      if (cssHeight / cssWidth > MAX_DESKTOP_ASPECT_RATIO) {
        const next = Math.round(cssWidth * MAX_DESKTOP_ASPECT_RATIO);
        top += Math.round((cssHeight - next) / 2);
        cssHeight = next;
      }
    }

    return { viewport, safe, touchUi, width: cssWidth, height: cssHeight, left, top };
  };

  window.openttdComputeAdaptiveLayout = layout;
  let raf = 0;
  let last = '';

  const apply = () => {
    raf = 0;
    try {
      if (typeof Module === 'undefined' || Module.calledRun !== true || typeof Module.setCanvasSize !== 'function') return false;
      const canvas = Module.canvas || document.getElementById('canvas');
      if (!canvas) return false;
      const box = layout();
      const key = [box.width, box.height, box.left, box.top, box.touchUi].join(':');
      if (canvas.width !== box.width || canvas.height !== box.height) Module.setCanvasSize(box.width, box.height);
      if (key !== last) {
        canvas.style.setProperty('position', 'fixed', 'important');
        canvas.style.setProperty('inset', 'auto', 'important');
        canvas.style.setProperty('width', `${box.width}px`, 'important');
        canvas.style.setProperty('height', `${box.height}px`, 'important');
        canvas.style.setProperty('left', `${box.left}px`, 'important');
        canvas.style.setProperty('top', `${box.top}px`, 'important');
        canvas.style.setProperty('right', 'auto', 'important');
        canvas.style.setProperty('bottom', 'auto', 'important');
        canvas.style.setProperty('max-width', 'none', 'important');
        canvas.style.setProperty('max-height', 'none', 'important');
        canvas.style.setProperty('touch-action', box.touchUi ? 'none' : 'auto', 'important');
        last = key;
      }
      return true;
    } catch (error) {
      console.warn('[OpenTTD] Adaptive viewport resize failed', error);
      return false;
    }
  };

  const schedule = () => {
    if (raf) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => { if (!apply()) setTimeout(apply, 50); });
  };

  window.addEventListener('resize', schedule, { passive: true });
  window.addEventListener('orientationchange', schedule, { passive: true });
  window.addEventListener('openttd-mobile-profile', schedule, { passive: true });
  window.visualViewport?.addEventListener('resize', schedule, { passive: true });
  window.visualViewport?.addEventListener('scroll', schedule, { passive: true });
  document.addEventListener('fullscreenchange', schedule, { passive: true });

  let attempts = 0;
  const startup = setInterval(() => {
    attempts += 1;
    if (apply() || attempts >= 160) clearInterval(startup);
  }, 100);
})();
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f'{label}: expected one occurrence, found {text.count(old)}')
    return text.replace(old, new, 1)


def patch_index(path: Path) -> None:
    text = path.read_text(encoding='utf-8')
    if 'name="viewport"' not in text and 'name=viewport' not in text:
        text = replace_once(text, '<meta charset=utf-8>', '<meta charset=utf-8><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover"><meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes">', 'viewport meta')
    boot = '<script src="yandex-bootstrap.js"></script>'
    tag = '<script src="openttd-yandex-mobile.js"></script>'
    if tag not in text:
        text = replace_once(text, boot, boot + tag, 'mobile script insertion')
    path.write_text(text, encoding='utf-8')


def config_path_expr() -> str:
    return "personalDir + '/' + (window.openttdConfigFilename || 'openttd.cfg')"


def patch_config_users(dist: Path) -> None:
    bridge = dist / 'yandex-bridge.js'
    text = bridge.read_text(encoding='utf-8')
    text = replace_once(text, "const CLOUD_CONFIG_KEY = 'openttdConfigV1';", "const CLOUD_CONFIG_KEY = 'openttdMobileConfigV1';", 'mobile cloud config key')
    text = replace_once(text, "FS.readFile(personalDir + '/openttd.cfg', { encoding: 'utf8' })", f"FS.readFile({config_path_expr()}, {{ encoding: 'utf8' }})", 'bridge read config')
    text = replace_once(text, "const configPath = personalDir + '/openttd.cfg';", f"const configPath = {config_path_expr()};", 'bridge restore config')
    bridge.write_text(text, encoding='utf-8')

    fixes = dist / 'openttd-yandex-fixes.js'
    text = fixes.read_text(encoding='utf-8')
    text = replace_once(text, "const path = personalDir + '/openttd.cfg';", f"const path = {config_path_expr()};", 'platform config path')

    anchor = """    if (/^language\\s*=.*$/m.test(config)) {\n      config = config.replace(/^language\\s*=.*$/m, 'language = ' + language);\n    } else if (/^\\[misc\\]\\s*$/m.test(config)) {\n      config = config.replace(/^\\[misc\\]\\s*$/m, '[misc]\\nlanguage = ' + language);\n    } else {\n      config = '[misc]\\nlanguage = ' + language + '\\n\\n' + config;\n    }\n\n\n"""
    addition = anchor + """    const guiScale = Number(window.openttdRecommendedGuiScale || 175);\n    const setGlobal = (key, value) => {\n      const rx = new RegExp('^' + key + '\\\\s*=.*$', 'm');\n      if (rx.test(config)) config = config.replace(rx, key + ' = ' + value);\n      else if (/^\\[misc\\]\\s*$/m.test(config)) config = config.replace(/^\\[misc\\]\\s*$/m, '[misc]\\n' + key + ' = ' + value);\n      else config = '[misc]\\n' + key + ' = ' + value + '\\n' + config;\n    };\n    const setGui = (key, value) => {\n      const rx = new RegExp('^' + key + '\\\\s*=.*$', 'm');\n      if (rx.test(config)) { config = config.replace(rx, key + ' = ' + value); return; }\n      if (/^\\[gui\\]\\s*$/m.test(config)) config = config.replace(/^\\[gui\\]\\s*$/m, '[gui]\\n' + key + ' = ' + value);\n      else config += (config.endsWith('\\n') ? '' : '\\n') + '\\n[gui]\\n' + key + ' = ' + value + '\\n';\n    };\n    if (window.openttdMobileProfile?.touchUi) {\n      setGlobal('gui_scale', Math.max(100, Math.min(250, guiScale)));\n      setGui('osk_activation', 'immediately');\n      setGui('scroll_mode', '3');\n      setGui('scrollwheel_scrolling', '0');\n      setGui('hover_delay_ms', '0');\n      setGui('toolbar_pos', '1');\n      setGui('statusbar_pos', '1');\n    }\n\n"""
    if text.count(anchor) != 1:
        raise SystemExit('mobile settings anchor missing in openttd-yandex-fixes.js')
    text = text.replace(anchor, addition, 1)
    fixes.write_text(text, encoding='utf-8')

    migration = dist / 'openttd-vanilla-migration.js'
    text = migration.read_text(encoding='utf-8')
    text = replace_once(text, "const configPath = personalDir + '/openttd.cfg';", f"const configPath = {config_path_expr()};", 'migration config path')
    migration.write_text(text, encoding='utf-8')

    runtime = dist / 'openttd-runtime.js'
    text = runtime.read_text(encoding='utf-8')
    old = 'const A=personal_dir+"/openttd.cfg";'
    new = 'const A=personal_dir+"/"+(window.openttdConfigFilename||"openttd.cfg");'
    text = replace_once(text, old, new, 'runtime locale config path')
    runtime.write_text(text, encoding='utf-8')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()
    required = [
        'index.html', 'openttd-runtime.js', 'openttd-full-viewport.js',
        'yandex-bootstrap.js', 'yandex-bridge.js', 'openttd-yandex-fixes.js',
        'openttd-vanilla-migration.js', 'openttd-classic-ai.js',
    ]
    for name in required:
        if not (dist / name).is_file():
            raise SystemExit(f'Missing package file: {name}')

    patch_config_users(dist)
    (dist / 'openttd-yandex-mobile.js').write_text(MOBILE_JS, encoding='utf-8')
    (dist / 'openttd-full-viewport.js').write_text(VIEWPORT_JS, encoding='utf-8')
    patch_index(dist / 'index.html')

    unpacked = sum(p.stat().st_size for p in dist.rglob('*') if p.is_file())
    if unpacked >= 100_000_000:
        raise SystemExit(f'Yandex package too large: {unpacked}')
    print(f'Adaptive Yandex mobile patch applied: unpacked_bytes={unpacked}')

if __name__ == '__main__':
    main()
