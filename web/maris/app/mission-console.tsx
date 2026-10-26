"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { ArrowLeft, ArrowRight, Check, ChevronRight, Crosshair, Eye, LockKeyhole, Play, Radio, RotateCcw, Shield, Zap } from "lucide-react";
import { useLocale } from "./locale-provider";
import { Panel } from "./image-comparison";
import { ko, modelName, pct } from "@/lib/display";
import { caseConditions, initialMission, recordedCaseOutcome, reduceMission, type MissionGuess } from "@/lib/mission";
import type { Evidence, Sample } from "@/lib/evidence";
import defense from "../public/evidence/defense-comparison.json";

type Props = {
  data: Evidence | null;
  sample?: Sample;
  error?: string;
  onRetry?: () => void;
  onChoose: (sample: Sample) => void;
  onOpenEvidence: () => void;
  children: (props: { stageOverlay: ReactNode }) => ReactNode;
};

export function MissionReadout({ sample, epsilon, guess }: { sample: Sample; epsilon: number; guess: MissionGuess | null }) {
  const { t } = useLocale();
  const outcome = recordedCaseOutcome(sample, epsilon, guess);
  return <div className={`mission-readout ${outcome.changed ? "changed" : "retained"}`} data-case-outcome={outcome.changed ? "changed" : "same"}>
    <div className="mission-answer"><span>{outcome.matches ? <Check size={19}/> : <Eye size={19}/>} {outcome.matches ? t("예상과 일치했어요") : t("기록은 예상과 달랐어요")}</span><strong>{outcome.changed ? t("AI의 분류가 바뀌었습니다.") : t("AI의 분류가 유지됐습니다.")}</strong></div>
    <div className="mission-image-pair"><figure><Panel sample={sample} part={0}/><figcaption>{t("원본 사진")}<b>{t(ko(sample.cleanPrediction))}</b></figcaption></figure><ArrowRight size={18}/><figure><Panel sample={sample} part={epsilon === 0 ? 0 : 1}/><figcaption>{epsilon === 0 ? t("대조군 · ε 0") : t("공격 기록 · ε {epsilon}", { epsilon })}<b>{t(ko(outcome.prediction))}</b></figcaption></figure></div>
    <p>{t("실제 정답: {truth} · {model} · 필터 없음", { truth: t(ko(sample.truth)), model: modelName(sample.model) })}</p>
    <a href={sample.sourceUrl} target="_blank" rel="noreferrer">{t("이 사례의 원기록 ↗")}</a>
  </div>;
}

export function MissionDefense({ sample, epsilon }: { sample: Sample; epsilon: number }) {
  const { t } = useLocale();
  const [method, setMethod] = useState("mean");
  const group = defense.methods.find(entry => entry.id === method);
  const row = group?.results.find(entry => entry.model === sample.model && entry.epsilon === epsilon);
  if (!group || !row) return null;
  const a = row.overall.accuracy, n = row.overall.samples;
  return <details className="mission-defense"><summary><Shield size={17}/>{t("필터 적용 후 전체 분류 결과 보기")}<ChevronRight size={17}/></summary><div>
    <h3>{t("전체 평가 결과 · {n}장", { n })}</h3><p className="mission-scope">{t("선택한 한 장의 방어 결과가 아닙니다. 아래는 같은 모델·강도의 전체 평가 기록입니다.")}</p>
    <div role="group" aria-label={t("미션 후 전체 평가 필터 선택")} className="mission-filter-options">{defense.methods.map(entry => <button key={entry.id} aria-pressed={entry.id === method} onClick={() => setMethod(entry.id)}>{t(entry.name)}</button>)}</div>
    <p className="mission-filter-condition">{modelName(sample.model)} · ε {epsilon} · {t(group.name)}</p>
    <div className={`mission-defense-records ${epsilon === 0 ? "control" : ""}`} aria-live="polite">{(epsilon === 0 ? [
      { label: t("정상 입력 · 필터 없음"), value: a.clean },
      { label: t("정상 입력 + 필터"), value: a.defended_clean },
    ] : [
      { label: t("필터 없는 공격"), value: a.attacked },
      { label: t("같은 공격 + 필터"), value: a.transfer_defended },
      { label: t("방어 인지 공격 + 필터"), value: a.adaptive_defended },
    ]).map(record => <div key={record.label}><span>{record.label}</span><b>{pct(record.value)}</b><small>{t("{correct} / {n}장 정답", { correct: Math.round(record.value * n), n })}</small></div>)}</div>
    <p>{t("정상 정확도: {before} → 필터 적용 {after}", { before: pct(a.clean), after: pct(a.defended_clean) })}</p>
    <p>{epsilon === 0 ? t("공격 강도 0에서는 필터 자체의 영향을 봅니다.") : t("방어 인지 공격은 필터를 알고 새로 만든 별도 공격 기록입니다. 실제 운항 안전을 뜻하지 않습니다.")}</p><a href="#defense">{t("전체 방어 실험과 분모 확인하기")} <ArrowRight size={14}/></a>
  </div></details>;
}

function LoadedMission({ data, sample, onChoose, onOpenEvidence, children }: Props & { data: Evidence; sample: Sample }) {
  const { t } = useLocale();
  const [session, setSession] = useState(() => ({ sampleId: sample.id, state: initialMission(sample) }));
  const state = session.sampleId === sample.id ? session.state : initialMission(sample);
  // Reset a new case before rendering it; do not remount the illustrative scene
  // or allow an old revealed result to reappear when returning to a case.
  if (session.sampleId !== sample.id) setSession({ sampleId: sample.id, state });
  const dispatch = (action: Parameters<typeof reduceMission>[2]) => setSession(current => ({
    sampleId: sample.id,
    state: reduceMission(sample, current.sampleId === sample.id ? current.state : initialMission(sample), action),
  }));
  const controlRef = useRef<HTMLDivElement>(null);
  const previousStep = useRef({ step: state.step, sampleId: sample.id });
  useEffect(() => {
    if (previousStep.current.sampleId === sample.id && previousStep.current.step !== state.step) controlRef.current?.focus({ preventScroll: true });
    previousStep.current = { step: state.step, sampleId: sample.id };
  }, [state.step, sample.id]);
  const steps = [t("사례 선택"), t("공격 설정"), t("판단 예상"), t("결과 공개")];
  const number = data.samples.findIndex(entry => entry.id === sample.id) + 1;
  const revealed = state.step === 3;
  const outcome = recordedCaseOutcome(sample, state.epsilon, state.guess);
  const stageOverlay = <div className={`mission-stage-overlay ${state.step > 0 && state.epsilon > 0 ? "armed" : ""} ${revealed ? "revealed" : ""}`} aria-hidden="true">
    <div className="mission-reticle"><i/><i/><i/><i/><Crosshair size={28}/></div>
    <div className="mission-scan"/>
    <div className="mission-stage-status"><span><Radio size={13}/>{revealed ? "RECORD REVEALED" : state.step > 0 ? "CONDITION ARMED" : "SELECT YOUR CASE"}</span><b>{modelName(sample.model)} · CASE {String(number).padStart(2, "0")}</b><small>{t("설명용 효과 · 기록 재생")}</small></div>
    <div className={`mission-target ${revealed && outcome.changed ? "changed" : ""}`}><Panel sample={sample} part={revealed && state.epsilon > 0 ? 1 : 0} compact/><span>{revealed ? t("기록된 AI 분류") : t("선택한 실제 이미지")}<b>{revealed ? t(ko(outcome.prediction)) : t(ko(sample.truth))}</b></span>{revealed ? <Eye size={16}/> : <LockKeyhole size={16}/>}</div>
  </div>;
  return <section id="mission" className={`mission-shell mission-step-${state.step}`} aria-label={t("기록 재생 미션")}>
    <div className="mission-heading"><div><span className="eyebrow">MISSION 01 / SIGNAL BREAK</span><h1>{t("사진이 조금 달라지면 AI의 답도 바뀔까요?")}</h1><p>{t("선박 사진을 고르고 작은 변화가 분류에 미친 영향을 예상해 보세요. 저장된 실험 결과로 답을 확인합니다.")}</p></div><span className="mission-replay-tag"><Radio size={14}/>{t("저장 기록으로 플레이")}</span></div>
    <ol className="mission-progress" aria-label={t("미션 진행 단계")}>{steps.map((label, index) => <li key={label} aria-current={index === state.step ? "step" : undefined} className={index < state.step ? "complete" : index === state.step ? "current" : ""}><b>{index < state.step ? <Check size={14}/> : `0${index + 1}`}</b><span>{label}</span></li>)}</ol>
    <div className="mission-grid"><div className="mission-controls" data-mission-step={state.step} ref={controlRef} tabIndex={-1} aria-label={t("미션 조작 패널")}>
      <div className="mission-step-heading"><span>0{state.step + 1} / 04</span><button className="mission-reset" onClick={() => dispatch({ type: "reset" })}><RotateCcw size={14}/>{t("미션 초기화")}</button></div>
      {state.step === 0 && <><h2>{t("어떤 기록에 도전할까요?")}</h2><p className="mission-instruction">{t("공개된 실제 항공모함 사례 4개입니다. 결과는 선택 뒤에 확인하세요.")}</p><div className="mission-cases" role="group" aria-label={t("미션의 실제 이미지 선택")}>{data.samples.map((entry, index) => <button key={entry.id} onClick={() => onChoose(entry)} aria-pressed={entry.id === sample.id}><Panel sample={entry} part={0} compact/><span><small>CASE {String(index + 1).padStart(2, "0")}</small><b>{modelName(entry.model)}</b></span>{entry.id === sample.id && <Check size={15}/>}</button>)}</div><button className="mission-primary" onClick={() => dispatch({ type: "next" })}><Crosshair size={17}/>{t("이 사례로 시작")}<ArrowRight size={18}/></button></>}
      {state.step === 1 && <><h2>{t("입력 조건을 선택하세요.")}</h2><p className="mission-instruction">{t("이 사례에 남아 있는 정상 입력과 ε 0.03 공격 기록만 고를 수 있습니다.")}</p><div className="mission-conditions" role="group" aria-label={t("미션 공격 조건")}>{caseConditions(sample).map(epsilon => <button key={epsilon} aria-pressed={state.epsilon === epsilon} onClick={() => dispatch({ type: "condition", epsilon })}>{epsilon === 0 ? <Shield size={22}/> : <Zap size={22}/>}<span><b>{epsilon === 0 ? t("원본 사진") : t("기록된 FGSM 공격")}</b><small>{epsilon === 0 ? t("ε 0 · 변화 없는 대조군") : t("ε {epsilon} · 분류를 흔들도록 준 작은 변화", { epsilon })}</small></span>{state.epsilon === epsilon && <Check size={16}/>}</button>)}</div><p className="mission-scope">{t("새 픽셀이나 모델 출력을 계산하지 않습니다. 3D의 빛과 스캔은 연출입니다.")}</p><button className="mission-primary" onClick={() => dispatch({ type: "next" })}>{t("판단 예상하기")}<ArrowRight size={18}/></button></>}
      {state.step === 2 && <><h2>{t("AI는 같은 선종으로 볼까요?")}</h2><p className="mission-instruction">{t("정상 입력의 기록된 분류는 {prediction}입니다.", { prediction: t(ko(sample.cleanPrediction)) })}</p><div className="mission-selected-condition"><Zap size={16}/>{modelName(sample.model)} · ε {state.epsilon} · {t("필터 없음")}</div><div className="mission-guesses" role="group" aria-label={t("AI 분류에 대한 내 예상")}>{(["same", "changed"] as const).map(guess => <button key={guess} aria-pressed={state.guess === guess} onClick={() => dispatch({ type: "guess", guess })}>{guess === "same" ? <Shield size={23}/> : <Zap size={23}/>}<b>{guess === "same" ? t("같은 선종") : t("다른 선종")}</b><small>{guess === "same" ? t("분류가 유지될 것 같아요") : t("분류가 바뀔 것 같아요")}</small></button>)}</div><button className="mission-primary" disabled={state.guess === null} onClick={() => dispatch({ type: "reveal" })}><Play size={17}/>{t("기록된 결과 공개")}<ArrowRight size={18}/></button>{state.guess === null && <small className="mission-select-prompt">{t("먼저 예상 하나를 선택하세요.")}</small>}</>}
      {revealed && <><div role="status"><MissionReadout sample={sample} epsilon={state.epsilon} guess={state.guess}/></div><div className="mission-replay-actions"><button className="mission-primary" onClick={() => dispatch({ type: "reset" })}><RotateCcw size={17}/>{t("다른 사례에 도전")}</button><button className="mission-secondary" onClick={onOpenEvidence}>{state.epsilon === 0 ? t("ε {epsilon} 공격 기록 비교", { epsilon: sample.epsilon }) : t("이미지 자세히 비교")}<ArrowRight size={16}/></button></div><MissionDefense sample={sample} epsilon={state.epsilon}/></>}
      {state.step > 0 && !revealed && <button className="mission-back" onClick={() => dispatch({ type: "back" })}><ArrowLeft size={15}/>{t("이전 단계")}</button>}
      <p className="mission-honesty"><LockKeyhole size={13}/>{t("실시간 추론 없이 저장된 실험을 재생합니다.")}</p>
    </div><div className="mission-visual">{children({ stageOverlay })}</div></div>
  </section>;
}

export default function MissionConsole(props: Props) {
  const { t } = useLocale();
  if (!props.data || !props.sample) return <section className="mission-shell mission-loading" aria-label={t("기록 재생 미션")}><span className="eyebrow">MISSION 01 / SIGNAL BREAK</span><h1>{t("사진이 조금 달라지면 AI의 답도 바뀔까요?")}</h1><p role={props.error ? "alert" : "status"}>{props.error ? t(props.error) : t("확인된 실험 기록을 불러오는 중입니다.")}</p>{props.error && props.onRetry && <button className="mission-primary" onClick={props.onRetry}>{t("다시 불러오기")}</button>}{props.children({ stageOverlay: null })}</section>;
  return <LoadedMission {...props} data={props.data} sample={props.sample}/>;
}
