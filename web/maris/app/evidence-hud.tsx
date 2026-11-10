"use client";

import { ArrowDown, ArrowRight, Check, Database, ExternalLink, FileSearch, LockKeyhole } from "lucide-react";
import { Panel } from "./image-comparison";
import { useLocale } from "./locale-provider";
import { evidenceHudState } from "@/lib/evidence-hud";
import { ko, modelName, pct } from "@/lib/display";
import type { Evidence, Sample } from "@/lib/evidence";
import type { MissionState } from "@/lib/mission";

export default function EvidenceHud({ data, sample, state }: { data: Evidence; sample: Sample; state: MissionState }) {
  const { t } = useLocale();
  const view = evidenceHudState(sample, state);
  const index = data.samples.findIndex(entry => entry.id === sample.id) + 1;
  return <section className="evidence-hud" aria-label={t("저장 기록 HUD")} data-hud-phase={state.step}>
    <header className="hud-header"><div><span className="hud-kicker">PAULGUARD / EVIDENCE LENS</span><h2>{t("하나의 기록, 판단의 흐름")}</h2></div><span className="hud-mode"><Database size={13}/>{t("저장 기록")}</span></header>
    <div className="hud-condition-strip"><span><b>{String(index).padStart(2, "0")}</b> / {String(data.samples.length).padStart(2, "0")} {t("공개 사례")}</span><span>{modelName(sample.model)}</span><span>{view.inputEpsilon === 0 ? "CLEAN" : "FGSM"} · ε {view.inputEpsilon}</span></div>
    <div className="hud-body">
      <figure className="hud-image-frame"><div className="hud-image-caption"><span>01 / INPUT RECORD</span><span>{t("이미지 전체")}</span></div><div className="hud-image"><Panel sample={sample} part={view.imagePart}/><i aria-hidden="true"/><i aria-hidden="true"/><i aria-hidden="true"/><i aria-hidden="true"/></div><figcaption><b>{view.inputEpsilon === 0 ? t("저장된 정상 입력") : t("저장된 FGSM 입력")}</b><span>{t("선택 사례 1장 · 필터 없음")}</span></figcaption></figure>
      <div className="hud-record-flow"><div className="hud-flow-label">02 / CLASSIFICATION RECORD</div><div className="hud-baseline"><span>{t("정상 입력의 분류")}</span><strong>{t(ko(sample.cleanPrediction))}</strong><small>{t("기록된 기준값")}</small></div><ArrowDown className="hud-flow-arrow" size={21} aria-hidden="true"/><div className={`hud-output ${view.changed === true ? "is-changed" : ""}`}><span>{t("선택 조건의 분류")}</span><strong>{view.prediction === null ? <><LockKeyhole size={19}/>{t("공개 전")}</> : t(ko(view.prediction))}</strong><small>{view.changed === null ? t("예상 선택 후 결과를 공개하세요.") : view.changed ? t("기준 분류와 다름") : t("기준 분류와 같음")}</small></div><div className="hud-score"><span>{t("선택 조건의 출력 점수")}</span><b>{view.score === null ? "—" : pct(view.score)}</b><small>{view.inputEpsilon > 0 ? t("공격 후 점수는 저장되지 않았습니다.") : view.revealed ? t("정답 확률이나 안전 점수가 아닙니다.") : t("결과 공개 뒤 확인할 수 있습니다.")}</small></div></div>
    </div>
    <div className="hud-verdict" aria-live="polite"><span className="hud-verdict-icon">{view.revealed ? <Check size={17}/> : <FileSearch size={17}/>}</span><p><b>{view.revealed ? t("저장된 출력 확인") : t("기록 비교 대기")}</b><span>{view.revealed ? t("실제 정답: {truth}", { truth: t(ko(sample.truth)) }) : t("새 추론 없이 선택한 기록을 순서대로 읽습니다.")}</span></p><span className="hud-step">0{state.step + 1} / 04</span></div>
    <footer className="hud-source"><div><span>03 / SOURCE</span><a href={sample.sourceUrl} target="_blank" rel="noreferrer">{t("이 사례의 원기록")}<ExternalLink size={12}/></a></div><a href={data.repoUrl + "/tree/" + data.sourceCommit} target="_blank" rel="noreferrer" aria-label={t("기준 커밋 확인")}><span>{data.sourceCommit.slice(0, 7)}</span><ArrowRight size={13}/></a></footer>
    <p className="hud-boundary">{t("프레임은 이미지 경계입니다. 표적 탐지·위험 예측·실시간 감시를 뜻하지 않습니다.")}</p>
  </section>;
}
