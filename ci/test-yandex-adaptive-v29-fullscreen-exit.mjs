#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const dist = path.resolve(process.argv[2] || '.');
const viewportPath = path.join(dist, 'openttd-full-viewport.js');
if (!fs.existsSync(viewportPath)) throw new Error(`missing ${viewportPath}`);
const source = fs.readFileSync(viewportPath, 'utf8');
if (!source.includes('V29: Yandex can fullscreen the parent element')) {
  throw new Error('not a V29 viewport script');
}

let raw = { width: 1600, height: 840 };
let focused = true;
const hostOuter = { width: 1600, height: 900 };
let timerId = 0;
const timers = new Map();
const listeners = new Map();
const docListeners = new Map();
const nativeResizeCalls = [];
const jsResizeCalls = [];
let nativeScreen = { width: 1600, height: 840 };

const styleStore = () => {
  const values = new Map();
  return {
    setProperty(name, value) { values.set(name, String(value)); },
    getPropertyValue(name) { return values.get(name) || ''; },
  };
};

const canvas = { width: 1600, height: 840, style: styleStore() };
const background = { style: styleStore() };
const probe = {
  id: 'openttd-viewport-probe',
  style: styleStore(),
  setAttribute() {},
  getBoundingClientRect() { return { width: raw.width, height: raw.height, left: 0, top: 0 }; },
};
const root = { style: styleStore(), appendChild() {} };
const body = { style: styleStore(), appendChild() {} };

const documentMock = {
  documentElement: root,
  body,
  hidden: false,
  fullscreenElement: null,
  webkitFullscreenElement: null,
  hasFocus: () => focused,
  getElementById(id) {
    if (id === 'openttd-viewport-probe') return probe;
    if (id === 'canvas') return canvas;
    return null;
  },
  createElement(tag) {
    if (tag === 'div') return probe;
    throw new Error(`unexpected createElement(${tag})`);
  },
  querySelector(selector) { return selector === 'div.background' ? background : null; },
  addEventListener(type, fn) {
    if (!docListeners.has(type)) docListeners.set(type, []);
    docListeners.get(type).push(fn);
  },
};

const Module = {
  calledRun: true,
  canvas,
  setCanvasSize(width, height) {
    jsResizeCalls.push([width, height]);
    canvas.width = width;
    canvas.height = height;
  },
  _em_openttd_force_window_resize(width, height) {
    nativeResizeCalls.push([width, height]);
    nativeScreen = { width, height };
    canvas.width = width;
    canvas.height = height;
    return 1;
  },
  _em_openttd_screen_width() { return nativeScreen.width; },
  _em_openttd_screen_height() { return nativeScreen.height; },
};

const context = {
  console, Math, Number, Object, Array, Map, Promise, Date, Module,
  document: documentMock,
  CSS: { supports: () => true },
  ResizeObserver: class { observe() {} disconnect() {} },
  CustomEvent: class { constructor(type, init = {}) { this.type = type; this.detail = init.detail; } },
  setTimeout(fn, delay = 0) {
    const id = ++timerId;
    if (delay === 0) fn(); else timers.set(id, { fn, delay });
    return id;
  },
  clearTimeout(id) { timers.delete(id); },
  requestAnimationFrame(fn) { fn(); return ++timerId; },
  cancelAnimationFrame() {},
};
context.window = context;
context.visualViewport = null;
context.openttdMobileProfile = { touchUi: false };
Object.defineProperty(context, 'outerWidth', { configurable: true, get: () => hostOuter.width });
Object.defineProperty(context, 'outerHeight', { configurable: true, get: () => hostOuter.height });
Object.defineProperty(context, 'innerWidth', { configurable: true, get: () => raw.width });
Object.defineProperty(context, 'innerHeight', { configurable: true, get: () => raw.height });
Object.defineProperty(root, 'clientWidth', { configurable: true, get: () => raw.width });
Object.defineProperty(root, 'clientHeight', { configurable: true, get: () => raw.height });
Object.defineProperty(body, 'clientWidth', { configurable: true, get: () => raw.width });
Object.defineProperty(body, 'clientHeight', { configurable: true, get: () => raw.height });
context.addEventListener = (type, fn) => {
  if (!listeners.has(type)) listeners.set(type, []);
  listeners.get(type).push(fn);
};
context.dispatchEvent = event => {
  for (const fn of listeners.get(event.type) || []) fn(event);
};

const fireWindow = type => {
  for (const fn of listeners.get(type) || []) fn({ type, isTrusted: true });
};
const fireDocument = type => {
  for (const fn of docListeners.get(type) || []) fn({ type, isTrusted: true });
};
const assertSize = (width, height, label) => {
  if (nativeScreen.width !== width || nativeScreen.height !== height ||
      canvas.width !== width || canvas.height !== height) {
    throw new Error(`${label}: native=${nativeScreen.width}x${nativeScreen.height}, canvas=${canvas.width}x${canvas.height}`);
  }
  if (canvas.style.getPropertyValue('height') !== `${height}px`) {
    throw new Error(`${label}: CSS height=${canvas.style.getPropertyValue('height')}`);
  }
};
const assertCanvasSize = (width, height, label) => {
  if (canvas.width !== width || canvas.height !== height) {
    throw new Error(`${label}: canvas=${canvas.width}x${canvas.height}`);
  }
  if (canvas.style.getPropertyValue('height') !== `${height}px`) {
    throw new Error(`${label}: CSS height=${canvas.style.getPropertyValue('height')}`);
  }
};

vm.createContext(context);
vm.runInContext(source, context, { filename: viewportPath });

const initial = context.openttdGetAdaptiveHostResizeState();
if (initial.baseline?.rawHeight !== 840 || initial.baseline?.deltaHeight !== 60) {
  throw new Error(`wrong initial windowed baseline: ${JSON.stringify(initial.baseline)}`);
}

// Yandex fullscreen is initiated by the parent shell. The iframe's document
// has no fullscreenElement, so V29 must recognize the zero-delta host geometry.
hostOuter.width = 1920;
hostOuter.height = 1080;
raw = { width: 1920, height: 1080 };
fireWindow('resize');
assertSize(1920, 1080, 'Yandex parent fullscreen entry');
const inParentFullscreen = context.openttdGetAdaptiveHostResizeState();
if (inParentFullscreen.baseline.rawHeight !== 840 || inParentFullscreen.baseline.deltaHeight !== 60) {
  throw new Error(`parent fullscreen poisoned baseline: ${JSON.stringify(inParentFullscreen.baseline)}`);
}

// Exit must restore the exact native framebuffer/canvas/CSS height, which keeps
// OpenTTD's bottom status bar inside the visible game area.
hostOuter.width = 1600;
hostOuter.height = 900;
raw = { width: 1600, height: 840 };
fireWindow('resize');
assertSize(1600, 840, 'Yandex parent fullscreen exit');

// Direct Fullscreen API path is guarded independently of geometry heuristics.
documentMock.fullscreenElement = canvas;
hostOuter.width = 1900;
hostOuter.height = 1060;
raw = { width: 1888, height: 1030 };
fireDocument('fullscreenchange');
assertSize(1888, 1030, 'document fullscreen entry');
const inDocumentFullscreen = context.openttdGetAdaptiveHostResizeState();
if (inDocumentFullscreen.baseline.rawHeight !== 840) {
  throw new Error(`document fullscreen poisoned baseline: ${JSON.stringify(inDocumentFullscreen.baseline)}`);
}
documentMock.fullscreenElement = null;
hostOuter.width = 1600;
hostOuter.height = 900;
raw = { width: 1600, height: 840 };
fireDocument('fullscreenchange');
assertSize(1600, 840, 'document fullscreen exit');

// Preserve V27's stale-child recovery after a fullscreen round-trip.
focused = false;
raw = { width: 1600, height: 520 };
fireWindow('resize');
assertSize(1600, 520, 'docked DevTools');
focused = true;
fireWindow('focus');
assertSize(1600, 840, 'DevTools-close recovery');
if (!context.openttdGetAdaptiveHostResizeState().mismatch) {
  throw new Error('V27 stale-child recovery was lost');
}

// Mobile remains on the verified visualViewport/JS-only path.
const nativeCountBeforeTouch = nativeResizeCalls.length;
context.openttdMobileProfile.touchUi = true;
context.visualViewport = { width: 390, height: 844, offsetLeft: 0, offsetTop: 0, addEventListener() {} };
raw = { width: 390, height: 844 };
fireWindow('openttd-mobile-profile');
assertCanvasSize(390, 844, 'touch resize');
if (nativeResizeCalls.length !== nativeCountBeforeTouch) {
  throw new Error('touch mode unexpectedly used desktop native resize bridge');
}
if (jsResizeCalls.at(-1)?.[0] !== 390 || jsResizeCalls.at(-1)?.[1] !== 844) {
  throw new Error(`touch mode did not use JS canvas resize: ${JSON.stringify(jsResizeCalls)}`);
}

console.log('V29_FULLSCREEN_EXIT_REGRESSION=PASS');
console.log('yandex_parent_fullscreen=PASS');
console.log('document_fullscreen=PASS');
console.log('windowed_native_canvas_css=1600x840');
console.log('bottom_status_bar_viewport=preserved');
console.log('v27_devtools_recovery=preserved');
console.log('mobile_visual_viewport=preserved');
