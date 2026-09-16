import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

// Only the explanatory model camera is controlled here; no research input changes.
export function createShipControls(camera: THREE.PerspectiveCamera, element: HTMLElement) {
  // A closer, broader view exposes the deck while keeping the whole model in
  // the mobile viewport. Reset saves this same view; orbit limits are unchanged.
  camera.position.set(18, 17, 28);
  const controls = new OrbitControls(camera, element);
  controls.target.set(0, 2, 0);
  controls.enablePan = false;
  controls.enableDamping = true;
  controls.dampingFactor = 0.09;
  controls.minDistance = 28;
  controls.maxDistance = 88;
  controls.minPolarAngle = 0.25;
  controls.maxPolarAngle = Math.PI / 2 - 0.08;
  controls.rotateSpeed = 0.65;
  controls.zoomSpeed = 0.7;
  controls.autoRotateSpeed = 0.55;
  controls.touches.ONE = THREE.TOUCH.ROTATE;
  controls.touches.TWO = THREE.TOUCH.DOLLY_PAN;
  controls.update();
  controls.saveState();
  return controls;
}

export function resetShipControls(controls: OrbitControls) {
  // Drain pending damping before restoring saved camera/target; otherwise a reset
  // during a drag's inertia would immediately rotate away from the saved view.
  const damping = controls.enableDamping;
  controls.autoRotate = false;
  controls.enableDamping = false;
  controls.update();
  controls.reset();
  controls.enableDamping = damping;
}
