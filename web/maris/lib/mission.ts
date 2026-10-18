import type { Sample } from "./evidence";

export type MissionGuess = "same" | "changed";
export type MissionStep = 0 | 1 | 2 | 3;
export type MissionState = { step: MissionStep; epsilon: number; guess: MissionGuess | null };
export type MissionAction =
  | { type: "next" }
  | { type: "back" }
  | { type: "condition"; epsilon: number }
  | { type: "guess"; guess: MissionGuess }
  | { type: "reveal" }
  | { type: "reset" };

export function initialMission(sample: Sample): MissionState {
  return { step: 0, epsilon: sample.epsilon, guess: null };
}

// Individual image evidence exists only for the clean input and this sample's
// recorded attack. Aggregate epsilon rows must never become case predictions.
export function caseConditions(sample: Sample) {
  return [...new Set([0, sample.epsilon])];
}

export function reduceMission(sample: Sample, state: MissionState, action: MissionAction): MissionState {
  switch (action.type) {
    case "reset": return initialMission(sample);
    case "next": return state.step < 2 ? { ...state, step: (state.step + 1) as MissionStep } : state;
    case "back": return state.step > 0 ? { ...state, step: (state.step - 1) as MissionStep, guess: null } : state;
    case "condition": return caseConditions(sample).includes(action.epsilon)
      ? { step: 1, epsilon: action.epsilon, guess: null } : state;
    case "guess": return state.step === 2 ? { ...state, guess: action.guess } : state;
    case "reveal": return state.step === 2 && state.guess !== null ? { ...state, step: 3 } : state;
  }
}

export function recordedCaseOutcome(sample: Sample, epsilon: number, guess: MissionGuess | null) {
  if (!caseConditions(sample).includes(epsilon)) throw new Error("No recorded individual prediction for this epsilon");
  const prediction = epsilon === 0 ? sample.cleanPrediction : sample.attackPrediction;
  const changed = prediction !== sample.cleanPrediction;
  return { prediction, changed, matches: guess === null ? null : guess === (changed ? "changed" : "same") };
}
