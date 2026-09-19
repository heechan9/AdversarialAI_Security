# Dependency security review — 2026-09-20

Base: personal `main` at `c9109af4cb1fdc501d647ca51e865c0d00025421`. This is a known-vulnerability database check, separate from the local source-security scan. Counts below are scanner advisory records, not confirmed exploitable application flaws. The initial inventory below is historical; see the remediation follow-up at the end for the updated state.

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

## Remediation follow-up — 2026-09-20

The updated MARIS lockfile returns **0 known advisories** in both full and production-only `pnpm audit --json` runs. React/React DOM/RSC move together to 19.2.8, Vite to 8.0.16, Vinext to beta.6 with plugin-rsc 0.5.34, and the stable Cloudflare plugin/Wrangler pair to 1.42.0/4.102.0. Targeted transitive overrides cover the affected Babel, YAML, glob expansion, browser-target mapping, compression, HTTP client and esbuild packages. The seven-day release-age policy and approved build-script policy remain enabled.

Vinext beta.6 removes the vulnerable image-size dependency. The alternative image-size 2.0.3 override was rejected by the release-age policy, so it was not retained. The original advisory's Babel lower bound 7.29.1 is not a published version; the candidate uses published 7.29.7 instead. The forced esbuild consumers were checked with both the application build and a disposable SQLite/Drizzle schema-generation smoke test.

The original `adversarial_ai` Conda environment remains unchanged (all 149 recorded distribution versions compared). A separate clone upgrades `httpx2` to 2.12.0, its `httpcore2` dependency to 2.12.0, Jupyter Server to 2.21.0, pip to 26.2, and Tornado to 6.5.8. The clone passes `pip check`; a fresh `pip-audit --path <clone>/Lib/site-packages --format json` reports **0 known advisories**. This does not erase the historical environment's warnings. Use the validated clone for future work; retain the old environment solely as the reproducibility snapshot.

### Verification and limits

- pnpm 11.25.0 frozen installation, TypeScript check, Vinext/Cloudflare production build: passed.
- Existing evidence hashes/four image hashes/six rejected mutations, defense comparison invariants, and synthetic controls checks: passed. Original Git evidence blobs were restored after Windows automatic CRLF conversion caused initial hash failures. `.gitattributes` now preserves those JSON bytes; no numeric records were changed.
- Disposable Drizzle SQLite schema generation: passed; no production database was accessed.
- Updated Python clone: `PYTHONPATH=src python -X utf8 -m pytest -q` passed with **309 passed, 5 skipped, 4 existing Keras/NumPy deprecation warnings**. The first attempt lacked `PYTHONPATH=src` and stopped at collection; correcting that invocation resolved it. Research Evidence audit also passed. Raw image/model binary verification remains unavailable in this checkout, as before.
- Browser against the updated local Worker build: data loaded; CAD toggle and Gaussian epsilon-zero controls worked, with 504/781 clean, 445/781 defended and ASR 0/445.
- Lint is **not clean**: two pre-existing `react-hooks/set-state-in-effect` errors in `app/image-comparison.tsx` and `app/page.tsx`, and one `no-img-element` warning. These files and the relevant ESLint/plugin versions are unchanged; no rule was disabled.
- Known-advisory database checks do not prove absence of undisclosed vulnerabilities or establish every advisory's exploitability.

### Deployment boundary

Sites confirms MARIS is public and its existing saved version 10 (`33f0a9efd3223b35ae79ef0e4389be8fdbcac6ee`) deployed successfully. An ordinary browser loads the public site and its epsilon-zero control works. A separate unauthenticated scripted HTTP request received a Cloudflare challenge (403), not application content; its challenge-page headers are not evidence of the application's header configuration.

The actual Sites source repository was retrieved and its hosting configuration confirms no D1 or R2 binding. A successful local build alone is not a production update. The deployment follow-up report records whether the patched source is published; do not infer that live version 10 has the patched lockfile.

### Reproduce the optional Python tool update

Keep the historical experiment environment. Clone it to a separate destination and use that clone's Python explicitly:

```text
conda create --name adversarial_ai_security --clone adversarial_ai
conda run -n adversarial_ai_security python -m pip install --upgrade httpx2==2.12.0 jupyter-server==2.21.0 pip==26.2 tornado==6.5.8
conda run -n adversarial_ai_security python -m pip check
```

Run the repository tests with `PYTHONPATH` pointing to its `src` directory and UTF-8 enabled. These optional notebook/developer tools are not added to the core TensorFlow/Keras requirements. The exact verified clone inventory and scanner JSON are preserved in the local audit artifacts.
