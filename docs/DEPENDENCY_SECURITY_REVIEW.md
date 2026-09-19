# Dependency security review — 2026-09-20

Base: personal `main` at `c9109af4cb1fdc501d647ca51e865c0d00025421`. This is a known-vulnerability database check, separate from the local source-security scan. Counts below are scanner advisory records, not confirmed exploitable application flaws.

## Scope and results

- `pnpm audit --json` used the committed MARIS lockfile: **36 records (20 high, 12 moderate, 4 low)**; 0 critical. Some advisories appear for multiple installed version ranges.
- `pnpm audit --prod --json`: **4 records (2 high, 1 moderate, 1 low)** through Next/styled-jsx/Babel/Browserslist/baseline-browser-mapping. Production dependency classification does not establish that the vulnerable code executes per web request.
- `pip-audit --path <adversarial_ai site-packages> --format json` read the existing Windows Conda environment (Python 3.11.15) without upgrading it: **9 records across 4 packages, 8 distinct advisory IDs**. `PYSEC-2026-3721` appears twice for pip.
- The Python audit covers 149 installed distribution records in that environment, including notebook/developer tools. It is not a resolved deployment lockfile. No distributions were skipped.
- No advisory was returned for installed TensorFlow 2.21.0 or Keras 3.15.1. This is not a guarantee of absence of undisclosed vulnerabilities.
- Neither package manifests/lockfile nor the Conda environment were upgraded in this change.

## Web advisory inventory

| Package | Locked version(s) | Advisory | Severity | Advisory-listed fixed range |
|---|---|---|---|---|
| `esbuild` | 0.18.20 | [GHSA-67mh-4wv8-2f99](https://github.com/advisories/GHSA-67mh-4wv8-2f99) | moderate | `>=0.24.3` |
| `ws` | 8.18.0 | [GHSA-58qx-3vcg-4xpx](https://github.com/advisories/GHSA-58qx-3vcg-4xpx) | moderate | `>=8.20.1` |
| `esbuild` | 0.27.3, 0.28.0 | [GHSA-g7r4-m6w7-qqqr](https://github.com/advisories/GHSA-g7r4-m6w7-qqqr) | low | `>=0.28.1` |
| `vite` | 8.0.13 | [GHSA-v6wh-96g9-6wx3](https://github.com/advisories/GHSA-v6wh-96g9-6wx3) | moderate | `>=8.0.16` |
| `undici` | 7.24.8 | [GHSA-vmh5-mc38-953g](https://github.com/advisories/GHSA-vmh5-mc38-953g) | high | `>=7.28.0` |
| `undici` | 7.24.8 | [GHSA-p88m-4jfj-68fv](https://github.com/advisories/GHSA-p88m-4jfj-68fv) | moderate | `>=7.28.0` |
| `undici` | 7.24.8 | [GHSA-vxpw-j846-p89q](https://github.com/advisories/GHSA-vxpw-j846-p89q) | high | `>=7.28.0` |
| `undici` | 7.24.8 | [GHSA-hm92-r4w5-c3mj](https://github.com/advisories/GHSA-hm92-r4w5-c3mj) | high | `>=7.28.0` |
| `undici` | 7.24.8 | [GHSA-g8m3-5g58-fq7m](https://github.com/advisories/GHSA-g8m3-5g58-fq7m) | low | `>=7.28.0` |
| `undici` | 7.24.8 | [GHSA-pr7r-676h-xcf6](https://github.com/advisories/GHSA-pr7r-676h-xcf6) | moderate | `>=7.28.0` |
| `js-yaml` | 4.1.1 | [GHSA-h67p-54hq-rp68](https://github.com/advisories/GHSA-h67p-54hq-rp68) | moderate | `>=4.1.2` |
| `ws` | 8.18.0 | [GHSA-96hv-2xvq-fx4p](https://github.com/advisories/GHSA-96hv-2xvq-fx4p) | high | `>=8.21.0` |
| `vite` | 8.0.13 | [GHSA-fx2h-pf6j-xcff](https://github.com/advisories/GHSA-fx2h-pf6j-xcff) | high | `>=8.0.16` |
| `@babel/core` | 7.29.0 | [GHSA-4x5r-pxfx-6jf8](https://github.com/advisories/GHSA-4x5r-pxfx-6jf8) | low | `>=7.29.1` |
| `brace-expansion` | 1.1.14 | [GHSA-3jxr-9vmj-r5cp](https://github.com/advisories/GHSA-3jxr-9vmj-r5cp) | high | `>=1.1.16` |
| `brace-expansion` | 5.0.6 | [GHSA-3jxr-9vmj-r5cp](https://github.com/advisories/GHSA-3jxr-9vmj-r5cp) | high | `>=5.0.7` |
| `js-yaml` | 4.1.1 | [GHSA-52cp-r559-cp3m](https://github.com/advisories/GHSA-52cp-r559-cp3m) | high | `>=4.3.0` |
| `react-server-dom-webpack` | 19.2.6 | [GHSA-wx67-qw84-cm4g](https://github.com/advisories/GHSA-wx67-qw84-cm4g) | high | `>=19.2.8` |
| `brace-expansion` | 1.1.14 | [GHSA-mh99-v99m-4gvg](https://github.com/advisories/GHSA-mh99-v99m-4gvg) | high | `>=1.1.17` |
| `brace-expansion` | 5.0.6 | [GHSA-mh99-v99m-4gvg](https://github.com/advisories/GHSA-mh99-v99m-4gvg) | high | `>=5.0.8` |
| `undici` | 7.24.8 | [GHSA-8xcm-r25x-g524](https://github.com/advisories/GHSA-8xcm-r25x-g524) | moderate | `>=7.29.0` |
| `undici` | 7.24.8 | [GHSA-4cwx-7wf7-3272](https://github.com/advisories/GHSA-4cwx-7wf7-3272) | high | `>=7.29.0` |
| `undici` | 7.24.8 | [GHSA-m8rv-5g2x-5cg5](https://github.com/advisories/GHSA-m8rv-5g2x-5cg5) | moderate | `>=7.29.0` |
| `undici` | 7.24.8 | [GHSA-jr45-8vmc-qm54](https://github.com/advisories/GHSA-jr45-8vmc-qm54) | moderate | `>=7.29.0` |
| `undici` | 7.24.8 | [GHSA-v3r7-h72x-cjcm](https://github.com/advisories/GHSA-v3r7-h72x-cjcm) | moderate | `>=7.29.0` |
| `brace-expansion` | 5.0.6 | [GHSA-rgw5-rvv9-x895](https://github.com/advisories/GHSA-rgw5-rvv9-x895) | high | `>=5.0.9` |
| `brace-expansion` | 1.1.14 | [GHSA-rgw5-rvv9-x895](https://github.com/advisories/GHSA-rgw5-rvv9-x895) | high | `>=1.1.18` |
| `undici` | 7.24.8 | [GHSA-35p6-xmwp-9g52](https://github.com/advisories/GHSA-35p6-xmwp-9g52) | low | `>=7.28.0` |
| `js-yaml` | 4.1.1 | [GHSA-5p4m-2wfm-xmqj](https://github.com/advisories/GHSA-5p4m-2wfm-xmqj) | high | `>=4.3.1` |
| `image-size` | 2.0.2 | [GHSA-w3rx-r6r6-pgpr](https://github.com/advisories/GHSA-w3rx-r6r6-pgpr) | high | `>=2.0.3` |
| `image-size` | 2.0.2 | [GHSA-5p2g-fcmc-qvqq](https://github.com/advisories/GHSA-5p2g-fcmc-qvqq) | high | `>=2.0.3` |
| `browserslist` | 4.28.2 | [GHSA-c83g-rgw3-j3cx](https://github.com/advisories/GHSA-c83g-rgw3-j3cx) | high | `>=4.28.7` |
| `browserslist` | 4.28.2 | [GHSA-73wf-gq98-2v4g](https://github.com/advisories/GHSA-73wf-gq98-2v4g) | high | `>=4.28.7` |
| `fflate` | 0.7.4 | [GHSA-px8p-9vwx-vf98](https://github.com/advisories/GHSA-px8p-9vwx-vf98) | moderate | `>=0.7.5` |
| `baseline-browser-mapping` | 2.10.30 | [GHSA-w5vr-8v7q-w6rv](https://github.com/advisories/GHSA-w5vr-8v7q-w6rv) | moderate | `>=2.11.0` |
| `js-yaml` | 4.1.1 | [GHSA-2883-xcg3-v3hh](https://github.com/advisories/GHSA-2883-xcg3-v3hh) | high | `>=4.3.2` |

## Existing Python environment

| Package | Installed | Advisory | Fixed version(s) |
|---|---|---|---|
| `httpx2` | 2.10.0 | [PYSEC-2026-3849](https://github.com/advisories/GHSA-pf96-p4fj-6566) | 2.11.0 |
| `httpx2` | 2.10.0 | [PYSEC-2026-3848](https://github.com/advisories/GHSA-h4x7-gw46-3wm6) | 2.11.0 |
| `httpx2` | 2.10.0 | [PYSEC-2026-3846](https://github.com/advisories/GHSA-8xx6-hgc6-gc2m) | 2.12.0 |
| `jupyter-server` | 2.20.0 | [CVE-2026-86049](https://github.com/advisories/GHSA-c3mw-737p-c7g2) | 2.21.0 |
| `pip` | 26.1.2 | [PYSEC-2026-3721](https://github.com/advisories/GHSA-qwm4-qh6w-59xr) | 26.2 |
| `tornado` | 6.5.7 | [PYSEC-2026-3928](https://github.com/advisories/GHSA-mpf4-983q-p7j4) | 6.5.8 |
| `tornado` | 6.5.7 | [GHSA-wwv5-g3v4-889x](https://github.com/advisories/GHSA-wwv5-g3v4-889x) | 6.5.8 |
| `tornado` | 6.5.7 | [GHSA-8423-8fgw-73vq](https://github.com/advisories/GHSA-8423-8fgw-73vq) | 6.5.8 |

## Exposure assessment and follow-up

1. **Vite development server:** locked Vite 8.0.13 matches Windows filesystem-deny bypass and launch-editor advisories. The [maintainer advisory](https://github.com/vitejs/vite/security/advisories/GHSA-fx2h-pf6j-xcff) requires a network-exposed development server and sensitive files within allowed directories. Actual deployment/listener configuration was not checked. Prefer a compatible patched Vite (at least 8.0.16 for these reported advisories), then verify the Vinext/Cloudflare build and local preview.
2. **Build and development dependencies:** many records are in Wrangler/Miniflare, Drizzle tooling, Babel and parser utilities. Package presence is established; public attacker reachability is not. Update affected parents/transitive ranges in a separate tested lockfile change. Avoid a forced whole-tree major upgrade.
3. **MARIS production graph:** the four remaining records involve compilation/browser-target helpers. Current page code replays committed JSON and does not accept user source or browserslist queries. This reduces the demonstrated application attack surface but does not remove the need to update compatible versions.
4. **Python notebook/tool environment:** httpx2, jupyter-server, pip and tornado are installed but not imported by the inspected research implementation. Whether a notebook server is currently exposed is unknown. Test upgrades in a cloned environment first: httpx2 >=2.12.0, jupyter-server >=2.21.0, pip >=26.2.0, tornado >=6.5.8, subject to environment compatibility.
5. **Reproducibility:** requirements.txt pins TensorFlow/Keras but leaves other packages unpinned. Preserve the original experiment environment and records before creating a separately validated lockfile.
6. **Deployment verification remains open:** actual hosting configuration and ingress controls were not supplied. A clean dependency scan would not replace that check.

The raw scanner JSON and exact installed-version inventory are saved with the local audit artifacts. Source-review limitations and numerical/model validation limits continue to apply.
