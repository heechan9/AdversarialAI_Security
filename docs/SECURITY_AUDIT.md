# Codex Security Audit

Audit date: 2026-09-06
Scope: research-evidence audit code and repository automation surfaces on the
`main` commit produced by PR #17.

## Claim boundary

This audit changes validation code, tests, and documentation only. It does not
change model binaries or weights, preprocessing, `configs/test_manifest.json`,
canonical Clean evidence, provisional FGSM evidence, the FGSM implementation,
epsilon values, or paper-facing research claims. Passing these checks establishes
internal consistency of the checked artifacts; it does not independently rerun
model inference when the raw images and `.h5` files are unavailable.

## Findings addressed

- **Path containment:** manifest, Clean, FGSM, and model metadata paths now reject
  absolute paths, drive-qualified paths, traversal components, duplicates, and
  symlink-based escape from the declared evidence root.
- **Complete local verification:** when a dataset directory is supplied, every
  one of the 781 manifest entries must exist and match its SHA-256. A partial
  directory can no longer be reported as verified.
- **Strict parsing:** evidence booleans accept only explicit `True`/`False`, and
  numeric attack fields reject non-numeric, non-finite, and out-of-range values.
- **Canonical FGSM binding:** each attack CSV must retain the Clean baseline path
  order, true labels, clean predictions, exact schema, and filename epsilon.
- **Canonical Clean binding:** both Clean evaluation CSVs must retain the
  manifest's complete path order and true labels, and requested summary JSON
  files may not silently disappear.
- **Derived-artifact verification:** FGSM classification reports, confusion
  matrices, and per-model summary CSVs are now recalculated from sample-level
  evidence. Missing or altered artifacts fail the audit.
- **Required provenance and documents:** `PROVENANCE.json`, `README.md`, and the
  provisional FGSM result document are mandatory. Provenance status and bundle
  SHA-256 format are validated rather than accepted by truthiness.
- **Fail-closed source identity:** failure to resolve a valid Git commit SHA now
  fails the research-evidence audit instead of emitting `unknown` in a passing
  report.

Mutation tests cover the identified bypasses, including truthy strings, path
traversal, partial datasets, invalid L-infinity values, epsilon substitution,
FGSM row reordering, missing evidence, altered report/summary/matrix artifacts,
and Git SHA lookup failure.

## Read-only checks

- No tracked private-key or common GitHub/AWS token patterns were found.
- No `pickle.load`, `joblib.load`, unsafe `yaml.load`, dynamic `eval`/`exec`,
  `shell=True`, or `os.system` use was found.
- The only subprocess invocation uses the fixed argument vector
  `git rev-parse HEAD`, a repository working directory, a five-second timeout,
  and checked exit status.
- No GitHub Actions workflow exists, so there is currently no workflow-token
  permission or third-party action-pin exposure to review.
- The installed environment reports no broken package requirements via
  `python -m pip check`.

## Residual risks

- Several secondary dependencies in `requirements.txt` are not version-pinned.
  They were not changed here because dependency upgrades could alter numerical
  research behavior. A separately reviewed lockfile should address this.
- There is no CI workflow enforcing the audit and test suite on pull requests.
- Clean checkouts intentionally lack the raw image dataset and `.h5` model files;
  their content hashes remain unverified until a local full-data audit is run.
- No dedicated dependency vulnerability scanner was installed in the audit
  environment, so `pip check` confirms consistency but not absence of published
  CVEs.
