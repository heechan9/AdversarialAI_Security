"use client";
import { useEffect, useRef, useState } from "react";
import { concepts, diagnosis, publicFacts, scenarios, sources, type Choice, type Locale } from "./content";
import { conceptRecords, emptySession, minimalMap, reduceSession, type Action } from "./state";
import { clearSession, loadSession, saveSession, type StoragePort } from "./storage";
import "./learning-panel.css";

export type EvidenceLearningProps = { locale?: Locale; storage?: StoragePort };
export default function EvidenceLearningPanel({ locale = "ko", storage }: EvidenceLearningProps) {
  const en = locale === "en", t = (ko: string, english: string) => en ? english : ko;
  const [opened, setOpened] = useState(false), [state, setState] = useState(emptySession);
  const [persistent, setPersistent] = useState(false), [notice, setNotice] = useState<{ko: string; en: string} | null>(null);
  const notify = (ko: string, en: string) => setNotice({ ko, en });
  const [focusVersion, setFocusVersion] = useState(0);
  const focusRef = useRef<HTMLHeadingElement>(null);
  const entryRef = useRef<HTMLButtonElement>(null), wasOpen = useRef(false);
  const scenario = scenarios[state.scenarioIndex], progress = state.progress[scenario.id];
  const key = `${state.stage}:${state.scenarioIndex}:${progress.phase}:${progress.checked}`;
  useEffect(() => {
    if (opened) { focusRef.current?.focus({ preventScroll: true }); focusRef.current?.scrollIntoView({ behavior: "instant", block: "center" }); wasOpen.current = true; }
    else if (wasOpen.current) { entryRef.current?.focus({ preventScroll: true }); entryRef.current?.scrollIntoView({ behavior: "instant", block: "center" }); wasOpen.current = false; }
  }, [opened, key, focusVersion]);
  // Save only from explicit UI events; no initial storage access or effect loop.
  function saveSelected(next: ReturnType<typeof emptySession>) {
    try { saveSession(storage ?? window.localStorage, next); return true; }
    catch { setPersistent(false); notify("기기 저장에 실패했습니다. 휘발성으로 계속하며 이전 저장본은 남아 있을 수 있습니다.", "Device save failed. Progress continues in memory; an older saved copy may remain."); return false; }
  }
  function dispatch(action: Action) {
    const next = reduceSession(state, action);
    setState(next);
    if (persistent) saveSelected(next);
  }
  function toggleSaving(enabled: boolean) {
    setPersistent(enabled);
    if (enabled) { if (!saveSelected(state)) return; notify("선택한 항목 ID만 이 기기에 저장합니다.", "Only selected option IDs are saved on this device."); return; }
    try { clearSession(storage ?? window.localStorage); notify("기기 저장본을 삭제했습니다. 진행은 휘발성으로 유지합니다.", "The device copy was deleted. Progress remains in memory."); }
    catch { notify("기기 저장본 삭제에 실패했습니다. 현재 진행은 휘발성입니다.", "The device copy could not be deleted. Current progress is in memory."); }
  }
  function restore() {
    try {
      const saved = loadSession(storage ?? window.localStorage);
      if (!saved) { notify("이 기능의 기기 저장본이 없습니다.", "There is no device record for this feature."); return; }
      setState(saved); setPersistent(true); setOpened(true); setFocusVersion(n => n + 1);
      notify("선택한 기기 기록을 불러왔습니다. 숙달·독립 검증 판정이 아닙니다.", "The selected device record was restored. This is not a mastery or independent-verification judgment.");
    } catch { notify("저장본의 형식·버전을 확인할 수 없어 불러오지 않았습니다. 초기화로 이 기능의 기록만 삭제할 수 있습니다.", "The record format or version is invalid, so it was not loaded. Reset deletes only this feature's record."); }
  }
  function reset() {
    setPersistent(false); setState(emptySession()); setFocusVersion(n => n + 1);
    try { clearSession(storage ?? window.localStorage); notify("이 학습의 기록을 초기화했습니다. 기기 저장도 꺼졌습니다.", "This learning record was reset. Device saving is off."); }
    catch { notify("화면 기록은 초기화했지만 기기 저장본 삭제는 실패했습니다.", "In-memory progress was reset, but deleting the device copy failed."); }
  }
  function options(name: string, legend: string, choices: Choice[], selected: string | null, onChoose: (id: string) => void, disabled = false) {
    return <fieldset className="pg-learning-options" disabled={disabled}><legend>{legend}</legend>{choices.map(option => <label key={option.id}>
      <input type="radio" name={name} value={option.id} checked={selected === option.id} onChange={() => onChoose(option.id)}/><span>{option.label[locale]}</span>
    </label>)}</fieldset>;
  }
  function sourceList(ids: string[]) {
    return <ul className="pg-learning-sources">{ids.map(id => { const source = sources.find(s => s.id === id); return source ? <li key={id}>{source.url ? <a href={source.url} target="_blank" rel="noopener noreferrer">{source.title[locale]} ↗</a> : source.title[locale]}</li> : null; })}</ul>;
  }
  const statusName: Record<string, string> = {
    "check-matched": t("새 조건 확인문항 일치", "New-condition check matched"), review: t("복습 필요", "Review needed"),
    "explanation-seen": t("해설 열람 · 확인 전", "Explanation viewed · not checked"), "diagnosis-matched": t("초기 문항 일치", "Initial item matched"), unconfirmed: t("미확인", "Unconfirmed"),
  };
  const misconceptionLabel = (id: string) => {
    const all = [...diagnosis.flatMap(q => q.choices), ...scenarios.flatMap(s => [...s.predictions, ...s.reasons, ...s.check.choices])];
    return all.find(o => o.misconception === id)?.label[locale] ?? id;
  };
  const currentTitle = state.stage === "diagnosis" ? t("어디부터 확인할까요?", "Where should we begin?") : state.stage === "map" ? t("필요한 개념만 연결하기", "Connect only the concepts you need") : state.stage === "summary" ? t("개념과 근거를 이어가기", "Carry concepts and evidence forward") : scenario.title[locale];
  return <section className="pg-learning" id="evidence-learning" lang={locale} aria-labelledby="pg-learning-title">
    <header className="pg-learning-header"><p className="pg-learning-kicker">{t("선택형 학습 · 저장 근거 해석", "OPTIONAL LEARNING · INTERPRETING EVIDENCE")}</p><h2 id="pg-learning-title">{t("검증 결과를 어디까지 말할 수 있을까요?", "How far does the verification evidence reach?")}</h2>
      <p>{t("이미지 맞히기 미션과 별개로, 결과의 의미와 한계를 연습합니다. 합성 예시와 공개 저장 기록만 사용합니다.", "Separate from the image-guessing mission, practice interpreting results and their limits. Only synthetic examples and public saved records are used.")}</p></header>
    <aside className="pg-learning-boundary" aria-label={t("항상 유지되는 연구 범위", "Preserved research scope")}>
      <strong>{t("외부 Stage B: FAIL · 생성 원인: UNRESOLVED", "External Stage B: FAIL · Generation cause: UNRESOLVED")}</strong>
      <p>{t("선택4장·5조건의 4/4칸과 같은 배열 라벨10/10쌍은 전체 정확도·독립 재현 PASS가 아닙니다. 라벨 일치는 확률 일치와 다릅니다. 필터·적대적 학습은 모든 공격의 안전을 보장하지 않습니다.", "4/4 matrix cells and 10/10 same-array label pairs cover four selected images and five conditions; they are not full accuracy or independent reproduction PASS. Label agreement differs from probability equality. Filters and adversarial training do not guarantee safety against every attack.")}</p>
    </aside>
    {!opened ? <div className="pg-learning-actions"><button ref={entryRef} onClick={() => setOpened(true)}>{t("학습 열기 / 이어가기", "Open / continue learning")}</button><button onClick={() => notify("학습은 선택 사항입니다. 기존 결과는 그대로 볼 수 있습니다.", "Learning is optional. Existing results remain available.")}>{t("학습 건너뛰기", "Skip learning")}</button></div> : <>
      <div className="pg-learning-toolbar"><button onClick={() => setOpened(false)}>{t("학습 닫기 · 휘발성 진행 유지", "Close learning · keep in-memory progress")}</button><button onClick={reset}>{t("전체 초기화 · 이 기능의 저장본 삭제", "Reset all · delete this feature's saved copy")}</button></div>
      <nav className="pg-learning-scenario-nav" aria-label={t("학습 시나리오 선택", "Learning scenario selection")}>{scenarios.map((s, index) => <button key={s.id} aria-current={state.stage === "learn" && index === state.scenarioIndex ? "step" : undefined} onClick={() => dispatch({ type: "scenario", index })}>{index + 1}. {s.title[locale]}</button>)}</nav>
      <h3 className="pg-learning-focus" ref={focusRef} tabIndex={-1}>{currentTitle}</h3>
      {state.stage === "diagnosis" && <div>
        <p>{t("3문항은 안내 경로를 고를 뿐, 능력·숙달을 평가하지 않습니다. 모르면 진단을 건너뛰어도 됩니다.", "Three items select a guidance path, not an ability or mastery rating. You can skip the diagnostic.")}</p>
        {diagnosis.map(q => <div key={q.id}>{options(q.id, q.prompt[locale], q.choices, state.diagnosis[q.id], choice => dispatch({ type: "diagnosis", id: q.id, choice }))}</div>)}
        <div className="pg-learning-actions"><button disabled={diagnosis.some(q => !state.diagnosis[q.id])} onClick={() => dispatch({ type: "diagnosis-done" })}>{t("선택으로 개념 지도 만들기", "Build a map from my selections")}</button><button onClick={() => dispatch({ type: "skip-diagnosis" })}>{t("진단 건너뛰기", "Skip diagnostic")}</button></div>
      </div>}
      {state.stage === "map" && <div>
        <p>{t("틀리거나 미응답한 문항에 필요한 선행개념만 안내합니다. 맞힌 초기 문항의 개념은 생략하며 언제든 아래 기록에서 다시 볼 수 있습니다.", "Guidance includes only prerequisites for incorrect or unanswered items. Concepts matched in the initial items are omitted and remain available in the record below.")}</p>
        {minimalMap(state).length ? <ol className="pg-learning-map">{minimalMap(state).map(id => { const c = concepts.find(c => c.id === id)!; return <li key={id}><h4>{c.title[locale]}</h4><p>{c.explanation[locale]}</p><small>{t("선행개념: ", "Prerequisites: ")}{c.prerequisites.map(id => concepts.find(c => c.id === id)!.title[locale]).join(" → ") || t("없음", "None")}</small></li>; })}</ol> : <p>{t("초기 3문항이 모두 일치해 선행 설명을 생략합니다. 새 조건에서도 이해가 이어지는지 확인해 보세요.", "All three initial items matched, so prerequisite explanations are omitted. Check whether the understanding transfers to new conditions.")}</p>}
        <button onClick={() => dispatch({ type: "start" })}>{t("시나리오로 확인하기", "Check with the scenarios")}</button>
      </div>}
      {state.stage === "learn" && <article className="pg-learning-scenario" data-scenario={scenario.id} data-phase={progress.phase}>
        <p className="pg-learning-kind">{scenario.kind[locale]} · {state.scenarioIndex + 1} / {scenarios.length}</p><p>{scenario.setup[locale]}</p>
        {progress.phase === "predict" && <>
          <p>{t("결과를 열기 전에 예상과 그 근거를 각각 선택하세요. 해설 바로 보기도 가능합니다.", "Select a prediction and a reason before opening the result. You may also open the explanation directly.")}</p>
          {options(scenario.id + "-prediction", scenario.question[locale], scenario.predictions, progress.prediction, choice => dispatch({ type: "choose", field: "prediction", choice }))}
          {options(scenario.id + "-reason", t("그렇게 예상한 근거는?", "What supports your prediction?"), scenario.reasons, progress.reason, choice => dispatch({ type: "choose", field: "reason", choice }))}
          <div className="pg-learning-actions"><button disabled={progress.hint >= scenario.hints.length} onClick={() => dispatch({ type: "hint" })}>{t("작은 힌트", "Small hint")} ({progress.hint}/{scenario.hints.length})</button><button disabled={!progress.prediction || !progress.reason} onClick={() => dispatch({ type: "reveal" })}>{t("예상·근거 확인하고 결과 열기", "Open result with prediction and reason")}</button><button onClick={() => dispatch({ type: "direct" })}>{t("해설 바로 보기", "Show explanation now")}</button></div>
          <div className="pg-learning-hints" aria-live="polite">{scenario.hints.slice(0, progress.hint).map((hint, i) => <p key={i}>{i + 1}. {hint[locale]}</p>)}</div>
        </>}
        {["explain", "check", "done"].includes(progress.phase) && <div className="pg-learning-explanation">
          <h4>{t("관측 결과와 해설", "Observation and explanation")}</h4>
          <p>{progress.bypassed ? t("예상 제출 없이 해설을 열었습니다. 정답 확인 기록으로 세지 않습니다.", "The explanation was opened without submitting predictions. This does not count as a matched check.") : progress.prediction === scenario.predictionCorrect && progress.reason === scenario.reasonCorrect ? t("예상과 근거가 이 문항의 해석에 일치했습니다.", "Your prediction and reason matched this item's interpretation.") : t("예상 또는 근거가 달랐습니다. 아래에서 조건과 분모를 나눠 확인하세요.", "Your prediction or reason differed. Separate conditions and denominators in the explanation below.")}</p>
          <p>{scenario.explanation[locale]}</p>{sourceList(scenario.evidence)}
          {progress.phase === "explain" && <button onClick={() => dispatch({ type: "check-stage" })}>{t("새 조건에서 이해 확인", "Check understanding in a new condition")}</button>}
        </div>}
        {progress.phase === "check" && <div className="pg-learning-check">
          {options(scenario.check.id, scenario.check.prompt[locale], scenario.check.choices, progress.check, choice => dispatch({ type: "choose", field: "check", choice }), progress.checked)}
          {!progress.checked ? <button disabled={!progress.check} onClick={() => dispatch({ type: "submit-check" })}>{t("이해 확인 결과 보기", "Check my selection")}</button> : <>
            <div role="status"><strong>{progress.check === scenario.check.correct ? t("이 새 조건 문항에 일치했습니다.", "This new-condition item matched.") : t("복습이 필요합니다.", "Review is needed.")}</strong><p>{scenario.check.explanation[locale]}</p><p>{t("선택형 문항 하나의 확인이며 숙달·실험 승인 판정이 아닙니다.", "This checks one multiple-choice item; it is not mastery or experiment approval.")}</p></div>
            <div className="pg-learning-actions"><button onClick={() => dispatch({ type: "retry-check" })}>{t("확인 문항 다시 보기", "Retry the check item")}</button><button onClick={() => dispatch({ type: "next" })}>{t("다음 시나리오 / 기록 보기", "Next scenario / view record")}</button></div>
          </>}
        </div>}
        {["done", "skipped"].includes(progress.phase) && <p>{progress.phase === "done" ? t("이 시나리오의 확인을 마쳤습니다. 확인 범위는 아래 기록을 보세요.", "This scenario's check is complete. See the record below for its scope.") : t("건너뛴 시나리오입니다. 확인 완료로 세지 않습니다.", "This scenario was skipped. It does not count as checked.")}</p>}
        <div className="pg-learning-actions"><button onClick={() => dispatch({ type: "skip" })}>{t("이 시나리오 건너뛰기", "Skip this scenario")}</button>{["done", "skipped"].includes(progress.phase) && <button onClick={() => dispatch({ type: "next" })}>{t("다음으로", "Continue")}</button>}</div>
      </article>}
      {state.stage === "summary" && <p>{t("예상·해설·새 조건 확인의 상태를 아래에서 다시 볼 수 있습니다. 기록의 일치는 실제 학습 효과나 연구 승인 증거가 아닙니다. 확인하지 않은 시나리오는 메뉴에서 이어가세요.", "Review prediction, explanation and new-condition check states below. Matching records do not demonstrate learning efficacy or research approval. Continue any unconfirmed scenario from the menu.")}</p>}
      <details className="pg-learning-record"><summary>{t("개념·선행개념·관측 근거·오개념·출처·확인 상태", "Concepts · prerequisites · observations · misconceptions · sources · check status")}</summary>
        <p>{t("오개념 항목은 선택지와 연결한 복습 단서입니다. 자유서술 사고과정이나 개인 능력 평가를 수집하지 않습니다.", "Misconceptions are review cues attached to selected options. Free-form thinking and personal ability ratings are not collected.")}</p>
        <div className="pg-learning-record-grid">{conceptRecords(state).map(record => { const concept = concepts.find(c => c.id === record.concept)!; return <article key={record.concept}><h4>{concept.title[locale]}</h4><p className="pg-learning-status">{statusName[record.status]}</p><dl>
          <dt>{t("선행개념", "Prerequisites")}</dt><dd>{record.prerequisites.map(id => concepts.find(c => c.id === id)!.title[locale]).join(" → ") || t("없음", "None")}</dd>
          <dt>{t("관측 근거 연결", "Observed evidence links")}</dt><dd>{record.observations.map(id => scenarios.find(s => s.id === id)!.title[locale]).join("; ") || t("아직 해설을 확인하지 않음", "No explanation observed yet")}</dd>
          <dt>{t("복습할 선택", "Selections to review")}</dt><dd>{record.misconceptions.map(misconceptionLabel).join("; ") || t("기록된 오선택 없음 · 숙달 증거 아님", "No recorded misconception selection · not mastery evidence")}</dd>
        </dl>{sourceList(record.sources)}</article>; })}</div>
      </details>
    </>}
    <footer className="pg-learning-storage"><label><input type="checkbox" checked={persistent} onChange={event => toggleSaving(event.target.checked)}/>{t("선택한 기록을 이 기기에 저장", "Save selected records on this device")}</label><p>{t("기본은 휘발성입니다. 저장을 선택해도 항목 ID와 단계만 남기며, 불러오기도 직접 선택합니다. 이 기능은 외부 API·분석·텔레메트리를 호출하지 않습니다.", "The default is in-memory progress. Opt-in saving keeps only option IDs and steps; loading is also an explicit choice. This feature calls no external API, analytics or telemetry.")}</p><div className="pg-learning-actions"><button onClick={restore}>{t("이 기능의 기기 기록 불러오기", "Load this feature's device record")}</button>{!opened && <button onClick={reset}>{t("이 기능의 기록 초기화", "Reset this feature's record")}</button>}</div></footer>
    <p role="status" aria-live="polite" className="pg-learning-notice">{notice?.[locale] ?? ""}</p>
    <details className="pg-learning-facts"><summary>{t("보존한 공개 수치와 분모", "Preserved public counts and denominators")}</summary><p>{t("MobileNetV2·Gaussian·ε=.01: 정상 / 공격 / 전달+필터 / 방어 인지+필터", "MobileNetV2 · Gaussian · ε=.01: clean / attack / transfer+filter / adaptive+filter")}</p><p>{publicFacts.gaussian.correct.map(n => `${n}/${publicFacts.gaussian.denominator}`).join(" · ")}</p><p>ASR: {publicFacts.gaussian.adaptiveSuccess}/{publicFacts.gaussian.adaptiveDenominator}</p><p>{t("정확도는 전체781장, 이 ASR은 필터 정상 정답648장 기준입니다. 선택 진단 표본을 더하지 않습니다.", "Accuracy uses all 781 files; this ASR uses 648 correctly classified filtered clean inputs. Selected diagnostic samples are not added.")}</p>{sourceList(["public-filter", "public-matrix"])}</details>
  </section>;
}
