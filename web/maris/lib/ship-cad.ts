import * as THREE from "three";

export type ShipPart = "hull" | "deck" | "upper";
export type CadSelection = "all" | ShipPart;
export type SceneMode = "sea" | "cad";

/** A display-only overlay on our procedural model, never an experimental input. */
export function createCadDisplay(ship: THREE.Group) {
  const overlay = new THREE.Group();
  overlay.name = "illustrative-cad-outlines";
  overlay.visible = false;
  const parts: ShipPart[] = ["hull", "deck", "upper"];
  const positions: Record<ShipPart, number[]> = {hull: [], deck: [], upper: []};
  const meshes: {object: THREE.Mesh; original: THREE.Material | THREE.Material[]; part: ShipPart}[] = [];
  const lines: {object: THREE.Line; visible: boolean}[] = [];
  const fills = Object.fromEntries(parts.map(part => [part, new THREE.MeshStandardMaterial({
    color: 0x707477, roughness: .92, metalness: .05, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1,
  })])) as Record<ShipPart, THREE.MeshStandardMaterial>;
  ship.updateWorldMatrix(true, true);
  const inverse = ship.matrixWorld.clone().invert();
  // Bake outlines once into only three draw calls, including the railings.
  ship.traverse(object => {
    if (!(object instanceof THREE.Mesh) && !(object instanceof THREE.Line)) return;
    const part = object.userData.shipPart as ShipPart;
    if (!parts.includes(part)) throw new Error("Every illustrative ship component must declare its structure group");
    const matrix = new THREE.Matrix4().multiplyMatrices(inverse, object.matrixWorld);
    const edges = object instanceof THREE.Mesh ? new THREE.EdgesGeometry(object.geometry, 28) : object.geometry.clone();
    edges.applyMatrix4(matrix);
    const attr = edges.getAttribute("position");
    for (let i = 0; i < attr.count; i++) positions[part].push(attr.getX(i), attr.getY(i), attr.getZ(i));
    edges.dispose();
    if (object instanceof THREE.Mesh) meshes.push({object, original: object.material, part});
    else lines.push({object, visible: object.visible});
  });
  const edges = parts.map(part => {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions[part], 3));
    const material = new THREE.LineBasicMaterial({color: 0xe9edef, transparent: true, opacity: .8});
    const line = new THREE.LineSegments(geometry, material);
    line.name = part;
    line.renderOrder = 1;
    overlay.add(line);
    return {part, geometry, material};
  });
  ship.add(overlay);

  function set(mode: SceneMode, selection: CadSelection) {
    const enabled = mode === "cad";
    overlay.visible = enabled;
    meshes.forEach(({object, original, part}) => {object.material = enabled ? fills[part] : original;});
    lines.forEach(({object, visible}) => {object.visible = enabled ? false : visible;});
    for (const part of parts) {
      const selected = selection === part, muted = selection !== "all" && !selected;
      fills[part].color.setHex(selected ? 0x939a9e : muted ? 0x555b60 : 0x707477);
      const edge = edges.find(e => e.part === part)!;
      edge.material.color.setHex(selected ? 0xffffff : muted ? 0x8d969b : 0xe9edef);
      edge.material.opacity = muted ? .45 : .9;
    }
  }
  return {set, overlay, dispose() {
    set("sea", "all");
    ship.remove(overlay);
    edges.forEach(({geometry, material}) => {geometry.dispose(); material.dispose();});
    Object.values(fills).forEach(material => material.dispose());
  }};
}
