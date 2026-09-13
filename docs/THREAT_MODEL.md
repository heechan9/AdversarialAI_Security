# Maritime Image-Classifier Red-Team Threat Model

## Purpose and evidence boundary

This document structures the existing Clean and FGSM evaluation as a small,
model-level maritime AI red-team exercise. It is informed by the University of
Plymouth RED-AI approach, which begins by defining scope, gathering system
information and developing a threat model before evaluating attacks and their
possible impact.

The evaluated system in this repository is **not** a Maritime Autonomous Surface
Ship (MASS), navigation controller, collision-avoidance system, sensor-fusion
stack, remote operations centre or shipboard IT/OT testbed. The measured result
is limited to adversarial robustness of two ship-image classifiers on the fixed
781-image test manifest.

Primary references:

- Walter, Barrett and Tam, *A Red Teaming Framework for Securing AI in Maritime
  Autonomous Systems*: https://doi.org/10.48550/arXiv.2312.11500
- University of Plymouth, SAIMAS: https://www.plymouth.ac.uk/research/saimas
- University of Plymouth, SeXTANt: https://www.plymouth.ac.uk/research/sextant
- University of Plymouth, Cyber-SHIP Lab:
  https://www.plymouth.ac.uk/facilities/cyber-ship-lab

The repository does not claim to implement or validate Plymouth's complete
RED-AI framework.

## Evaluation scope

| Element | In-scope statement |
| --- | --- |
| Protected function | CNN and MobileNetV2 classification of ship images |
| Protected assets | Model behaviour, model weights, input/result integrity and reproducible evidence |
| Attacker objective | Cause a clean-correct image to be misclassified after perturbation |
| Attacker knowledge | White-box access to model gradients and the true label |
| Attacker access | Direct digital manipulation of the normalized image tensor |
| Attack surface | Model image input after the documented preprocessing path |
| Evaluated attack | One-step untargeted FGSM under the recorded epsilon sweep |
| Input constraint | `[0,1]` clipping and `L-infinity <= epsilon + 1e-6` |
| Primary outcomes | Robust accuracy, clean-correct ASR, class-level clean-correct ASR, confusion matrices |
| Integrity controls | Epsilon-zero invariants, model-weight immutability, manifest/model hashes and evidence audits |

Targeted FGSM support, when present in attack code, is not an official result
unless it has a separately fixed contract, canonical artifacts and audit trail.

## Attack-to-consequence chain

| Stage | Status in this project | Permitted interpretation |
| --- | --- | --- |
| Digital image perturbation | Experimentally applied | The input tensor was changed within the stated norm and clipping constraints |
| Classifier prediction change | Experimentally measured | A clean-correct sample may become misclassified |
| Vessel-recognition failure | Measured only at image-classification level | The classifier failed to return the manifest label |
| Situational-awareness degradation | Plausible scenario, not tested | A downstream system could receive incorrect class information |
| Navigation or collision-avoidance impact | Not tested | No operational or causal claim is permitted |
| Physical harm or accident reduction | Not tested | No safety-effectiveness claim is permitted |

The last three stages must not be collapsed into the measured classifier result.
The dataset does not contain an operational decision loop, vessel dynamics,
operator response or incident outcome.

## Assumptions and limitations

- The attacker is stronger than a typical remote observer because gradients and
  true labels are available.
- The perturbation is digital. Printability, camera distance, view angle,
  illumination, weather, water reflection, lens contamination and compression
  are not evaluated.
- Images are independent test samples rather than a time-synchronised camera
  stream.
- AIS, GNSS, radar and other sensors are absent.
- A class-level ASR denominator contains only samples of that class that the
  corresponding model classified correctly before attack.
- A class with no clean-correct samples has undefined ASR, not zero ASR.
- Small class denominators limit generalisation; ASR must be reported with its
  success count and denominator.
- The provisional FGSM artifacts remain provisional until the official
  experiment and evidence-freezing process is complete.

## Out-of-scope threat surfaces

The following are research extensions rather than evaluated capabilities:

- poisoning, backdoors, extraction and model-stealing attacks;
- adversarial patches or other physical-world perturbations;
- camera, AIS, GNSS and radar fusion;
- attacks on networks, remote operations centres and shipboard IT/OT;
- autonomous navigation decisions and closed-loop vessel control;
- human-autonomy teaming and operator workload;
- real-world attack likelihood, collision probability or accident reduction.

## Future validation gates

1. Freeze and independently audit the official digital FGSM artifacts.
2. Report model- and class-level robustness with denominators and limitations.
3. Define a separate physical-attack contract before testing adversarial patches.
4. Establish time alignment, provenance and independent sensor baselines before
   adding camera/AIS/GNSS/radar data.
5. Use simulation or a safety-controlled testbed before evaluating downstream
   navigation decisions.
6. Only after those gates, consider system-level maritime cyber-physical red
   teaming.

Each gate requires its own threat assumptions, success criteria and audit
artifacts. Passing an earlier gate is not evidence that a later gate is secure.

## Defense evaluation and operational comparison

The experimental Gaussian comparison evaluates both base-model FGSM transferred
through preprocessing and adaptive FGSM through the full differentiable f(D(x)).
Report defended-clean degradation, pipeline-specific clean-correct denominators
and attack-conditioned accuracy together. One-step adaptive evaluation does not
establish worst-case robustness or prove gradient masking. A small L-infinity
budget does not establish perceptual invisibility without a separate assessment.

Operational object detection, tracking, range estimation, latency, false alarms
and operator response are not measured by this static classification benchmark.
ASR is conditional on the evaluator's access assumptions and clean-correct set;
it is not the probability of a successful real-world intrusion or an accident.
See [practice gap review](MARITIME_PRACTICE_GAP_REVIEW.md) for source boundaries.
