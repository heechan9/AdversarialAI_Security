# Apache 2.0 source-code scope

## What is licensed

Only the original project-owned software source code in the exact files listed
in [LICENSED_CODE.txt](LICENSED_CODE.txt) is licensed under the
[Apache License, Version 2.0](LICENSE).

This is a source-code grant, not a license for the repository as a whole.
The list contains literal repository-relative paths, not wildcard patterns.
An unlisted file is not covered by this grant. New paths require an explicit
scope review and list update. Existing ownership and contributor attribution
are unchanged.

Any third-party material in a listed file remains subject to its applicable
license and notices; this grant does not replace those terms or claim ownership
of it. Dependencies installed separately retain their own licenses.
The scope rules identify the covered work; they do not add restrictions to
Apache 2.0 for that covered work.

## Material outside this grant

This change does not license datasets, input images, comparison images, artwork,
screenshots, model weights or checkpoints, saved predictions, experiment
results, reports, manuscripts, handoff archives or ZIP contents under Apache 2.0.
In particular, `data/`, `results/`, `docs/`, `web/`, `notebooks/`, and unlisted
files under `research/` retain their existing status and applicable terms.
The README files, configuration/data manifests and research documentation are
not automatically included merely because they accompany the code.

Exclusion from this grant neither revokes an existing license nor creates a
new restriction. Where permission has not been established, repository
visibility, download availability, attribution or a checksum is not permission.
A code license does not supply permission to use or redistribute its input
data, trained models or protected outputs. No dataset condition is assumed
to transfer automatically to every independent statistic or original program.

## 한국어 요약

[정확한 파일 목록](LICENSED_CODE.txt)에 있는 프로젝트 자체 소스코드에만
[Apache 2.0](LICENSE)을 적용합니다. 저장소 전체, 데이터·이미지·가중치·연구
결과·문서·웹 및 아래 별도 항목까지 일괄 허가하는 것이 아닙니다.
기존 제3자 조건과 기여자 표기는 유지하며, 목록 밖 파일에 새로운 허가나
제한을 부여하지 않습니다.

## Preserved boundaries and notices

### Square Attack

`src/adversarial_ai/attacks/square.py` is excluded from the Apache list.
It adapts
[max-andr/square-attack](https://github.com/max-andr/square-attack/tree/ea95eebb5aca62ec790a927b5aa985ba4e87245c)
and retains the [BSD-3-Clause notice](docs/licenses/square-attack.txt).
The original copyright, redistribution conditions and disclaimer remain
applicable. This change does not relabel that file as Apache-only.

### SurFree

[Upstream SurFree](https://github.com/t-maho/SurFree/blob/c9920f2c289a4ad3c2d8d203006bb5964bf71816/LICENSE)
is GPL version 2 or any later version. The following local integration and
related audit files are outside this initial Apache grant:

- `src/adversarial_ai/attacks/surfree_adapter.py`
- `src/adversarial_ai/evaluation/surfree_evaluation.py`
- `verification/surfree_saved_audit.py`
- `verification/blackbox_series_summary.py`
- `verification/blackbox_subset_sensitivity.py`
- `tests/test_surfree_adapter.py`
- `tests/test_surfree_evidence.py`

The adapter imports an external checkout in the same Python process.
A separate checkout does not establish that a combined distribution is
Apache-only. This change grants no new license for that integration or the
upstream GPL code and does not decide the license of any combined work.
See the [integration protocol](docs/TRAINED_BLACKBOX.md).
This conservative scope choice is not a finding of a license violation.

### Images, models and web material

- [Reproducibility limits](docs/REPRODUCIBILITY.md) and unresolved source
  permissions for test images and models are unchanged.
- Comparison PNGs under `results/attacks/provisional/samples/` and their copies
  under `web/maris/public/evidence/images/` are outside this grant, including
  the photographed input content. [Image provenance](web/maris/public/evidence/provenance.json)
  records identity, not a new reuse license.
- The experimental defense ZIPs and their saved CSV/JSON results remain
  outside the source-code grant.
- The excluded web tree contains separately noticed
  [OpenAI Sites Vite plugin code](web/maris/build/sites-vite-plugin.LICENSE)
  and [shadcn CSS](web/maris/vendor/shadcn-tailwind-4.13.0.LICENSE.md)
  under MIT. Their notices are unchanged.
- Team-authored review CSVs, reports and research documents are not included
  merely because the project code is now licensed.

Initial path selection is based on main
`2ed69b00faa3dce098a6a78888032746b6b35d43`.
This license-only change does not change source code, results, image/model
files, existing notices, attribution or release assets.
