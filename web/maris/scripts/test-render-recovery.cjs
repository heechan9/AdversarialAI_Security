/* eslint-disable @typescript-eslint/no-require-imports, @typescript-eslint/no-this-alias -- Node CommonJS renderer harness. */
// Executes the actual Ocean effect with real Three geometry and a controlled renderer.
// Synthetic context events verify lifecycle logic, not GPU driver restoration.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ts = require('typescript');
const THREE = require('three');
const source = fs.readFileSync(process.env.OCEAN_SOURCE || path.join(__dirname, '../app/ocean.tsx'), 'utf8');
const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText;
let assertions = 0;
function check(actual, expected, label) { assertions++; assert.equal(actual, expected, label); }
async function scenario(software) {
  const frames = new Map(), effects = [], failures = [];
  let next = 0, clock = 0, renderer, resize, intersect, hidden = false;
  class Surface extends EventTarget { setAttribute() {} remove() {} }
  class Canvas extends Surface {}
  const host = { clientWidth: 640, clientHeight: 360, appendChild() {}, querySelector() { return renderer?.domElement; } };
  class Renderer {
    constructor() { renderer = this; this.domElement = software ? new Surface() : new Canvas(); this.shadowMap = {}; this.renders = 0; }
    setPixelRatio() {} setPrecision() {} setClearColor() {} setSize(w,h) { assert.ok(w > 0 && h > 0); }
    render() { this.renders++; } dispose() { this.disposed = true; }
    getContext() { return { isContextLost: () => false }; }
  }
  class WebGL extends Renderer { constructor() { if (software) throw Error('synthetic fallback'); super(); } }
  class SVG extends Renderer {}
  const controls = { getDistance: () => 20, target: new THREE.Vector3(), update() {}, addEventListener() {}, removeEventListener() {}, dispose() {} };
  const React = {
    useRef: initial => ({ current: initial === null ? host : initial }),
    useState: () => [false, value => failures.push(value)],
    useEffect: effect => effects.push(effect),
  };
  const exports = {};
  const context = {
    exports, console, performance: { now: () => clock }, devicePixelRatio: 1,
    matchMedia: () => ({ matches: false }), HTMLCanvasElement: Canvas,
    document: { get hidden() { return hidden; }, createElement() { return { getContext: () => ({ drawImage() {}, getImageData: () => ({ data: new Uint8ClampedArray(256*144*4) }) }) }; } },
    ResizeObserver: class { constructor(fn) { resize = fn; } observe() {} disconnect() {} },
    IntersectionObserver: class { constructor(fn) { intersect = fn; } observe() {} disconnect() {} },
    requestAnimationFrame: fn => { frames.set(++next, fn); return next; },
    cancelAnimationFrame: id => frames.delete(id),
    require: name => {
      if (name === 'react') return React;
      if (name === 'react/jsx-runtime') return { jsx: () => null, jsxs: () => null };
      if (name === 'three') return { ...THREE, WebGLRenderer: WebGL };
      if (name.includes('SVGRenderer')) return { SVGRenderer: SVG };
      if (name.includes('locale-provider')) return { useLocale: () => ({ t: s => s }) };
      if (name.includes('ship-controls')) return { createShipControls: () => controls, resetShipControls() {}, setShipView() {} };
      if (name.includes('ship-cad')) return { createCadDisplay: () => ({ set() {}, dispose() {} }) };
      throw Error('Unexpected import '+name);
    },
  };
  vm.runInNewContext(code, context, { filename: 'ocean.js' });
  const captureRef = { current: null };
  exports.default({ playing: false, command: { id: 0, kind: 'reset' }, mode: 'ocean', selection: 'all', onInteract() {}, onZoom() {}, captureRef });
  const cleanups = effects.map(fn => fn()).filter(Boolean);
  const cleanup = cleanups.at(-1);
  const tick = () => { clock += 100; const scheduled = [...frames]; frames.clear(); scheduled.forEach(([,fn]) => fn(clock)); };
  const event = type => renderer.domElement.dispatchEvent(new Event(type, { cancelable: true }));
  tick(); check(renderer.renders, 1, 'initial draw');
  const savedCapture = captureRef.current;
  const queuedBeforeLoss = [...frames.values()][0];
  check(event('webglcontextlost'), false, 'loss prevented to allow restoration');
  check(frames.size, 0, 'loss cancels RAF'); check(failures.at(-1), true, 'failure visible');
  queuedBeforeLoss(clock + 100); check(frames.size, 0, 'stale RAF cannot revive lost context');
  await assert.rejects(savedCapture(), /Context lost/); assertions++;
  check(renderer.renders, 1, 'lost capture cannot render');
  event('webglcontextrestored'); check(failures.at(-1), false, 'failure cleared');
  check(frames.size, 1, 'restoration schedules one RAF');
  event('webglcontextrestored'); check(frames.size, 1, 'duplicate restore does not fork loop');
  tick(); check(renderer.renders, 2, 'paused scene redrawn after restore');
  if (!software) { check(renderer.shadowMap.needsUpdate, true, 'shadow cache invalidated'); const result = await savedCapture(); check(result.source, '3d-webgl', 'capture recovers'); }
  for (const gate of ['hidden', 'zero', 'offscreen']) {
    event('webglcontextlost'); event('webglcontextlost');
    if (gate === 'hidden') hidden = true;
    if (gate === 'zero') { host.clientHeight = 0; resize(); }
    if (gate === 'offscreen') intersect([{ isIntersecting: false }]);
    const before = renderer.renders;
    event('webglcontextrestored'); tick();
    check(renderer.renders, before, gate+' remains gated'); check(frames.size, 1, gate+' has one loop');
    hidden = false; host.clientHeight = 360; resize(); intersect([{ isIntersecting: true }]);
    tick(); check(renderer.renders, before + 1, gate+' redraws on return');
  }
  const queuedBeforeUnmount = [...frames.values()][0];
  cleanup(); check(frames.size, 0, 'unmount cancels RAF'); check(captureRef.current, null, 'capture detached');
  const stateCount = failures.length;
  event('webglcontextrestored'); event('webglcontextlost'); queuedBeforeUnmount(clock + 100);
  check(frames.size, 0, 'unmounted callbacks cannot schedule'); check(failures.length, stateCount, 'no state update after unmount');
  await assert.rejects(savedCapture(), /Scene disposed/); assertions++;
}
(async () => {
  await scenario(false); await scenario(true);
  const pkg = JSON.parse(fs.readFileSync(path.join(__dirname, '../package.json')));
  check(pkg.scripts['test:ui'].includes('npm run test:pixels'), true, 'pixel suite wired');
  check(pkg.scripts['test:ui'].includes('npm run test:render-recovery'), true, 'recovery suite wired');
  console.log(`PASS: ${assertions} synthetic lifecycle assertions (WebGL/SVG branches); no actual GPU verification.`);
})().catch(error => { console.error(error); process.exitCode = 1; });
