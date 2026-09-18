export type ImageView = { zoom: number; x: number; y: number };
export const initialView: ImageView = { zoom: 1, x: 0, y: 0 };
export function boundView(view: ImageView): ImageView {
  const zoom = Math.max(1, Math.min(3, view.zoom));
  if (zoom === 1) return { ...initialView };
  const edge = (zoom - 1) / 2;
  return { zoom, x: Math.max(-edge, Math.min(edge, view.x)), y: Math.max(-edge, Math.min(edge, view.y)) };
}
