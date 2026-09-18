import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
import * as THREE from 'three';

async function loadTS(path) {
  let code = ts.transpileModule(fs.readFileSync(new URL(path, import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 }
  }).outputText;
  code = code.replace(/from "(three[^"]*)"/g, (_, specifier) => `from ${JSON.stringify(import.meta.resolve(specifier))}`);
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const { createShipControls, resetShipControls, setShipView } = await loadTS('../lib/ship-controls.ts');
const { boundView } = await loadTS('../lib/image-view.ts');
class Surface extends EventTarget {
  style = {}; clientWidth = 390; clientHeight = 275;
  ownerDocument = new EventTarget();
  getRootNode() { return this.ownerDocument; }
  setPointerCapture() {} releasePointerCapture() {}
  getBoundingClientRect() { return { x: 0, y: 0, left: 0, top: 0, width: 390, height: 275 }; }
}
const surface = new Surface();
const camera = new THREE.PerspectiveCamera(37, 390/275, .1, 900);
const controls = createShipControls(camera, surface);
const startPosition = camera.position.clone(), startTarget = controls.target.clone();
const starts = [];
controls.addEventListener('start', () => { controls.autoRotate = false; starts.push(true); });
function pointer(type, id, x, y, pointerType = 'touch') {
  const event = new Event(type, { cancelable: true });
  Object.assign(event, { pointerId: id, pointerType, pageX: x, pageY: y, clientX: x, clientY: y, button: 0 });
  (type === 'pointerdown' ? surface : surface.ownerDocument).dispatchEvent(event);
}
// Tests use the installed OrbitControls event handlers, not a reimplementation.
controls.autoRotate = true;
const angle = controls.getAzimuthalAngle();
pointer('pointerdown', 1, 140, 130);
pointer('pointermove', 1, 230, 150);
assert.equal(controls.autoRotate, false);
assert.notEqual(controls.getAzimuthalAngle(), angle);
assert.ok(starts.length);
pointer('pointerup', 1, 230, 150);
// Reset immediately while damping still has residual movement.
resetShipControls(controls);
for (let i = 0; i < 90; i++) controls.update(1/60);
assert.ok(camera.position.distanceTo(startPosition) < 1e-9);
assert.ok(controls.target.distanceTo(startTarget) < 1e-9);
// Two-finger pinch changes distance, not target; min/max keep camera outside hull.
pointer('pointerdown', 2, 150, 140); pointer('pointerdown', 3, 240, 140);
const beforePinch = controls.getDistance();
pointer('pointermove', 3, 310, 140);
assert.ok(controls.getDistance() < beforePinch);
pointer('pointermove', 3, 100000, 140);
assert.ok(Math.abs(controls.getDistance() - controls.minDistance) < 1e-9);
pointer('pointermove', 3, 150.01, 140);
assert.ok(Math.abs(controls.getDistance() - controls.maxDistance) < 1e-9);
assert.ok(controls.target.distanceTo(startTarget) < 1e-9);
pointer('pointerup', 2, 150, 140); pointer('pointerup', 3, 150.01, 140);
assert.equal(surface.style.touchAction, 'none');
for (const aspect of [1, 1.5, 2.4]) {
  camera.aspect = aspect;
  for (const view of ['bow', 'side', 'deck']) {
    setShipView(controls, camera, view);
    assert.ok(controls.getDistance() >= controls.minDistance && controls.getDistance() <= controls.maxDistance);
    assert.ok(controls.target.distanceTo(startTarget) < 1e-9);
    resetShipControls(controls);
    assert.ok(camera.position.distanceTo(startPosition) < 1e-9);
  }
}
controls.dispose();
// Shared comparison viewport never reveals other panels/text outside its crop.
for (const zoom of [.2, 1, 1.5, 2, 3, 99]) for (const x of [-90, -.4, 0, .4, 90]) {
  const v = boundView({ zoom, x, y: -x });
  assert.ok(v.zoom >= 1 && v.zoom <= 3);
  assert.ok(v.x - v.zoom/2 <= -.5 && v.x + v.zoom/2 >= .5);
  assert.ok(v.y - v.zoom/2 <= -.5 && v.y + v.zoom/2 >= .5);
}
assert.deepEqual(boundView({ zoom: 1, x: 5, y: -5 }), { zoom: 1, x: 0, y: 0 });
console.log('PASS: touch rotation, auto-stop event, reset during inertia, two-touch pinch, camera limits, fixed target, 30 image viewport boundary cases, 9 preset/aspect/reset combinations. Synthetic input harness; not physical-device QA.');
