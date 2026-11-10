import type { Sample } from "./evidence";
import { recordedCaseOutcome, type MissionState } from "./mission";

// This is a view of one saved image record, never a detector or inference loop.
// Hide the selected output until the mission explicitly reveals it.
export function evidenceHudState(sample: Sample, state: MissionState) {
  const outcome = recordedCaseOutcome(sample, state.epsilon, state.guess);
  const revealed = state.step === 3;
  const inputEpsilon = state.step === 0 ? 0 : state.epsilon;
  return {
    revealed,
    inputEpsilon,
    imagePart: inputEpsilon === 0 ? 0 : 1,
    prediction: revealed ? outcome.prediction : null,
    changed: revealed ? outcome.changed : null,
    // Attack scores were not saved. Never substitute the clean score.
    score: revealed && inputEpsilon === 0 ? sample.cleanScore : null,
  };
}
