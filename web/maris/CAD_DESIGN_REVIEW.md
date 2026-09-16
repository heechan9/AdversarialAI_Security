# MARIS CAD-style explanatory view

Reviewed 2026-09-16. The supplied screenshots are visual references for matte gray
surfaces, fine edge lines and a neutral modeling workspace. No supplied or linked
image/model is embedded, traced, downloaded into the app, or used as research data.

## Reference review

- [Gstar page](https://gstarcad.co.kr/product/view/std.php): the served page describes
  3D FastView, including model viewing and custom views. Reuse the general idea of
  inspecting structure; MARIS does not implement CAD editing, measurement, sections,
  CAD import/export, or dimensionally accurate engineering.
- [Free3D container ship](https://free3d.com/ko/3d-model/container-ship-1834.html):
  a paid asset with licensing conditions, not an unrestricted free model. The
  [license](https://free3d.com/royalty-free-license), section II.7, restricts exposed
  open-format assets in software. No asset was purchased or included in public Git
  or the public site. Source review is not a clearance for future asset reuse.
- [Knock Nevis drawings](https://www.aukevisser.nl/supertankers/id462.htm): Blender
  work credited to Anton Gisslén, with explicit image copyright notices. It informs
  the neutral study presentation only; no right to redistribute was established.

## Decision and scope

Add a mode within the existing first-screen viewer, preserving the image comparison
entry point. Use the existing original procedural ship, not another ship dataset.
Both visual modes share bounded orbit controls and the same camera and geometry.
Gray material/outline selection identifies external model groups only. It is not an
AI attention map, attack trace, physical patch, sensor feed, or defense visualization.
The grid has no real-world unit. No displacement, collision, navigation, internal
compartments, real ship specifications, or attack-induced motion is invented.

Edges are computed once and batched into three structural groups. No new package,
external texture, downloaded mesh, dynamic research request, or second canvas is
added. WebGL depth-tests edges; SVG fallback uses painter ordering and may show
rear edges through surfaces. It is an outline aid, not a validated occlusion model.
