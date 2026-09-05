#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const dist = path.resolve(process.argv[2] || '.');
const viewportPath = path.join(dist, 'openttd-full-viewport.js');
if (!fs.existsSync(viewportPath)) throw new Error(`missing ${viewportPath}`);
const source = fs.readFileSync(viewportPath, 'utf8');
if (!source.includes('Adaptive V27 host-aware native-framebuffer recovery.')) {
  throw new Error('not a V27 viewport script');
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
    _values: values,
  };
};

const canvas = {
  width: 1600,
  height: 840,
  style: styleStore(),
};
const background = { style: styleStore() };
const probe = {
  id: 'openttd-viewport-probe',
  style: styleStore(),
  setAttribute() {},
  getBoundingClientRect() { return { width: raw.width, height: raw.height, left: 0, top: 0 }; },
};
const root = {
  clientWidth: raw.width,
  clientHeight: raw.height,
  style: styleStore(),
  appendChild() {},
};
const body = {
  clientWidth: raw.width,
  clientHeight: raw.height,
  style: styleStore(),
  appendChild() {},
};

const documentMock = {
  documentElement: root,
  body,
  hidden: false,
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
  querySelector(selector) {
    if (selector === 'div.background') return background;
    return null;
  },
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
  console,
  Math,
  Number,
  Object,
  Array,
  Map,
  Promise,
  Date,
  Module,
  document: documentMock,
  CSS: { supports: () => true },
  ResizeObserver: class {
    constructor(cb) { this.cb = cb; }
    observe() {}
    disconnect() {}
  },
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

const fire = type => {
  for (const fn of listeners.get(type) || []) fn({ type, isTrusted: true });
};

vm.createContext(context);
vm.runInContext(source, context, { filename: viewportPath });

const state0 = context.openttdGetAdaptiveHostResizeState();
if (!state0.baseline) throw new Error('healthy baseline was not captured');
if (state0.baseline.rawHeight !== 840) throw new Error(`unexpected baseline height ${state0.baseline.rawHeight}`);

// Simulate docked DevTools. The game frame is genuinely smaller and loses focus,
// so V27 must follow the real 520 px child height instead of "recovering" it.
focused = false;
raw = { width: 1600, height: 520 };
fire('resize');
if (nativeScreen.height !== 520 || canvas.height !== 520) {
  throw new Error(`DevTools-open resize failed: native=${nativeScreen.height}, canvas=${canvas.height}`);
}

// Simulate the exact Firefox/Yandex failure seen by the user: DevTools closes and
// focus returns, outer host height is healthy again, but child viewport remains
// stale at 520. V27 must infer 840 and resize the *native* SDL framebuffer.
focused = true;
fire('focus');
const state1 = context.openttdGetAdaptiveHostResizeState();
if (!state1.mismatch) throw new Error('stale DevTools-close height was not detected');
if (nativeScreen.height !== 840 || canvas.height !== 840) {
  throw new Error(`DevTools-close recovery failed: native=${nativeScreen.height}, canvas=${canvas.height}`);
}
if (canvas.style.getPropertyValue('height') !== '840px') {
  throw new Error(`CSS canvas height not recovered: ${canvas.style.getPropertyValue('height')}`);
}
const lastNative = nativeResizeCalls.at(-1);
if (!lastNative || lastNative[0] !== 1600 || lastNative[1] !== 840) {
  throw new Error(`wrong final native resize call: ${JSON.stringify(lastNative)}`);
}
if (jsResizeCalls.length !== 0) {
  throw new Error(`desktop recovery used JS-only canvas resizing: ${JSON.stringify(jsResizeCalls)}`);
}

// Touch/mobile remains on the verified 1:1 visual-viewport path and must not use
// the desktop host-geometry recovery or native desktop resize bridge.
const nativeCountBeforeTouch = nativeResizeCalls.length;
context.openttdMobileProfile.touchUi = true;
context.visualViewport = { width: 390, height: 844, offsetLeft: 0, offsetTop: 0, addEventListener() {} };
raw = { width: 390, height: 844 };
fire('openttd-mobile-profile');
if (canvas.width !== 390 || canvas.height !== 844) {
  throw new Error(`touch resize regressed: ${canvas.width}x${canvas.height}`);
}
if (nativeResizeCalls.length !== nativeCountBeforeTouch) {
  throw new Error('touch mode unexpectedly used desktop native resize bridge');
}

console.log('V27_DEVTOOLS_CLOSE_REGRESSION=PASS');
console.log(`healthy=1600x840 docked=1600x520 recovered=${nativeScreen.width}x${nativeScreen.height}`);
console.log(`native_resize_calls=${JSON.stringify(nativeResizeCalls)}`);
