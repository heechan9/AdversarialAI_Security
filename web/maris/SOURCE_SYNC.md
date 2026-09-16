# MARIS source synchronization

The initial import preserves the deployed v4 source (Sites commit `689e83c708816a904d60d91141c1a4381efaa8dc`), excluding provider-specific hosting configuration. Existing comparison PNGs were reused without modification.

The current update corresponds to Sites source `7e9a13f9982059acccf2468aa657632fd2eaf148` (saved version 5). It adds settled experiment scope, implementation/experiment progress, and recorded Gaussian defense results. Scope agreement is separate from official result adoption; FGSM remains provisional and defense remains experimental.

Defense summary is copied from `results/defenses/experimental/gaussian_run_01/summary.json` at research commit `324a53566760f47d707ab5ca8e6fa91cb6d84c16`. The adjacent web evidence provenance JSON records its SHA-256. The UI derives the eight model/epsilon rows from this snapshot and keeps the defense ASR denominator distinct from the original classifier denominator.

Validation: frozen dependency installation, production build, evidence snapshot/image integrity tests and six rejected mutations, synthetic interaction tests including 30 image viewport boundary cases, and eight defense-row count/rate consistency checks passed. These are not physical mobile-device or GPU/browser-rendering verification. Research Python tests and audits were not rerun for this web-only update. No model, canonical result, experiment contract, or original checkpoint was changed.

The web is recorded evidence replay, not live inference or autonomous navigation simulation. Defense-aware single-step FGSM results are not a general defense guarantee.
