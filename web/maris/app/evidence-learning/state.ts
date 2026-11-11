import { CONTENT_VERSION, concepts, diagnosis, scenarios } from "./content";
export type Phase = "predict" | "explain" | "check" | "done" | "skipped";
export type Progress = { prediction: string | null; reason: string | null; hint: number; phase: Phase; bypassed: boolean; check: string | null; checked: boolean; explanationSeen: boolean };
export type Session = { version: 1; contentVersion: string; stage: "diagnosis" | "map" | "learn" | "summary"; scenarioIndex: number; diagnosis: Record<string, string | null>; progress: Record<string, Progress> };
export const blankProgress = (): Progress => ({ prediction: null, reason: null, hint: 0, phase: "predict", bypassed: false, check: null, checked: false, explanationSeen: false });
export const emptySession = (): Session => ({ version: 1, contentVersion: CONTENT_VERSION, stage: "diagnosis", scenarioIndex: 0, diagnosis: Object.fromEntries(diagnosis.map(q => [q.id, null])), progress: Object.fromEntries(scenarios.map(s => [s.id, blankProgress()])) });
export type Action =
  | { type: "diagnosis"; id: string; choice: string }
  | { type: "diagnosis-done" | "skip-diagnosis" | "start" | "hint" | "reveal" | "direct" | "check-stage" | "submit-check" | "retry-check" | "next" | "skip" }
  | { type: "choose"; field: "prediction" | "reason" | "check"; choice: string }
  | { type: "scenario"; index: number };
export function reduceSession(state: Session, action: Action): Session {
  if (action.type === "diagnosis") {
    const question = diagnosis.find(q => q.id === action.id);
    if (state.stage !== "diagnosis" || !question?.choices.some(c => c.id === action.choice)) return state;
    return { ...state, diagnosis: { ...state.diagnosis, [action.id]: action.choice } };
  }
  if (action.type === "diagnosis-done" || action.type === "skip-diagnosis") {
    if (state.stage !== "diagnosis" || (action.type === "diagnosis-done" && diagnosis.some(q => !state.diagnosis[q.id]))) return state;
    return { ...state, stage: "map" };
  }
  if (action.type === "start") return state.stage === "map" ? { ...state, stage: "learn" } : state;
  if (action.type === "scenario") return Number.isInteger(action.index) && action.index >= 0 && action.index < scenarios.length ? { ...state, stage: "learn", scenarioIndex: action.index } : state;
  if (state.stage !== "learn") return state;
  const scenario = scenarios[state.scenarioIndex], before = state.progress[scenario.id];
  const update = (change: Partial<Progress>): Session => ({ ...state, progress: { ...state.progress, [scenario.id]: { ...before, ...change } } });
  const advance = (next: Session): Session => state.scenarioIndex + 1 < scenarios.length ? { ...next, scenarioIndex: state.scenarioIndex + 1 } : { ...next, stage: "summary" };
  switch (action.type) {
    case "choose": {
      const choices = action.field === "prediction" ? scenario.predictions : action.field === "reason" ? scenario.reasons : scenario.check.choices;
      if (!choices.some(c => c.id === action.choice)) return state;
      if (action.field === "check") return before.phase === "check" && !before.checked ? update({ check: action.choice }) : state;
      return before.phase === "predict" ? update({ [action.field]: action.choice }) : state;
    }
    case "hint": return before.phase === "predict" ? update({ hint: Math.min(scenario.hints.length, before.hint + 1) }) : state;
    case "reveal": return before.phase === "predict" && before.prediction && before.reason ? update({ phase: "explain", explanationSeen: true }) : state;
    case "direct": return before.phase === "predict" ? update({ phase: "explain", bypassed: true, explanationSeen: true }) : state;
    case "check-stage": return before.phase === "explain" ? update({ phase: "check" }) : state;
    case "submit-check": return before.phase === "check" && before.check ? update({ checked: true }) : state;
    case "retry-check": return before.phase === "check" && before.checked ? update({ checked: false, check: null }) : state;
    case "next": return before.phase === "check" && before.checked ? advance(update({ phase: "done" })) : before.phase === "done" || before.phase === "skipped" ? advance(state) : state;
    case "skip": return advance(before.checked ? update({ phase: "done" }) : update({ phase: "skipped", checked: false, check: null }));
    default: return state;
  }
}
export function minimalMap(state: Session): string[] {
  const initiallyMatched = new Set(diagnosis.filter(q => state.diagnosis[q.id] === q.correct).flatMap(q => q.concepts));
  const required = new Set<string>();
  const add = (id: string) => {
    if (required.has(id) || initiallyMatched.has(id)) return;
    const concept = concepts.find(c => c.id === id);
    if (!concept) return;
    concept.prerequisites.forEach(add); required.add(id);
  };
  diagnosis.filter(q => state.diagnosis[q.id] !== q.correct).forEach(q => q.concepts.forEach(add));
  return [...required];
}
export function conceptRecords(state: Session) {
  return concepts.map(concept => {
    const related = scenarios.filter(s => s.concepts.includes(concept.id));
    const checks = related.filter(s => state.progress[s.id].checked);
    const matched = checks.some(s => state.progress[s.id].check === s.check.correct);
    const revealed = related.some(s => state.progress[s.id].explanationSeen);
    const diagnosed = diagnosis.some(q => q.concepts.includes(concept.id) && state.diagnosis[q.id] === q.correct);
    const misconceptions = new Set<string>();
    diagnosis.filter(q => q.concepts.includes(concept.id)).forEach(q => { const answer = q.choices.find(c => c.id === state.diagnosis[q.id]); if (answer?.misconception) misconceptions.add(answer.misconception); });
    related.forEach(s => {
      const p = state.progress[s.id];
      for (const option of [s.predictions.find(c => c.id === p.prediction), s.reasons.find(c => c.id === p.reason), ...(p.checked ? [s.check.choices.find(c => c.id === p.check)] : [])]) if (option?.misconception) misconceptions.add(option.misconception);
    });
    const status = matched ? "check-matched" : checks.length ? "review" : revealed ? "explanation-seen" : diagnosed ? "diagnosis-matched" : "unconfirmed";
    return { concept: concept.id, prerequisites: concept.prerequisites, observations: related.filter(s => state.progress[s.id].explanationSeen).map(s => s.id), misconceptions: [...misconceptions], sources: concept.evidence, status };
  });
}
function object(value: unknown): value is Record<string, unknown> { return !!value && typeof value === "object" && !Array.isArray(value); }
function exactKeys(value: Record<string, unknown>, expected: string[]): boolean { return Object.keys(value).length === expected.length && expected.every(k => Object.hasOwn(value, k)); }
export function parseSession(raw: string): Session {
  if (raw.length > 14000) throw Error("record too large");
  const data: unknown = JSON.parse(raw), blank = emptySession();
  if (!object(data) || !exactKeys(data, Object.keys(blank)) || data.version !== 1 || data.contentVersion !== CONTENT_VERSION || !["diagnosis", "map", "learn", "summary"].includes(String(data.stage)) || !Number.isInteger(data.scenarioIndex) || Number(data.scenarioIndex) < 0 || Number(data.scenarioIndex) >= scenarios.length) throw Error("invalid record");
  if (!object(data.diagnosis) || !exactKeys(data.diagnosis, diagnosis.map(q => q.id)) || !object(data.progress) || !exactKeys(data.progress, scenarios.map(s => s.id))) throw Error("invalid record fields");
  const diagnosticChoices = data.diagnosis;
  for (const q of diagnosis) if (diagnosticChoices[q.id] !== null && !q.choices.some(c => c.id === diagnosticChoices[q.id])) throw Error("invalid diagnostic choice");
  for (const s of scenarios) {
    const p = data.progress[s.id];
    if (!object(p) || !exactKeys(p, Object.keys(blankProgress())) || !["predict", "explain", "check", "done", "skipped"].includes(String(p.phase)) || !Number.isInteger(p.hint) || Number(p.hint) < 0 || Number(p.hint) > s.hints.length || typeof p.bypassed !== "boolean" || typeof p.checked !== "boolean" || typeof p.explanationSeen !== "boolean") throw Error("invalid progress");
    for (const [field, choices] of [["prediction", s.predictions], ["reason", s.reasons], ["check", s.check.choices]] as const) if (p[field] !== null && !choices.some(c => c.id === p[field])) throw Error("invalid selected ID");
    if (p.checked && (!p.check || !["check", "done"].includes(String(p.phase)))) throw Error("invalid check state");
    if (["explain", "check", "done"].includes(String(p.phase)) && !p.bypassed && (!p.prediction || !p.reason)) throw Error("missing prediction and reason");
    if (p.phase === "predict" && (p.checked || p.check || p.bypassed || p.explanationSeen)) throw Error("unrevealed state carries future answers");
    if (["explain", "check", "done"].includes(String(p.phase)) && !p.explanationSeen) throw Error("unseen explanation");
    if (p.phase === "done" && !p.checked) throw Error("unchecked completion");
  }
  // Rebuild a fresh object: no unknown keys, text fields, timestamps or identity.
  return JSON.parse(JSON.stringify(data)) as Session;
}
