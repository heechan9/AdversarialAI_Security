"use client";
import {useState} from "react";
import {useLocale} from "./locale-provider";
import report from "../public/evidence/matched-cnn-followup.json";

const conditions = ["clean", "pgd7", "pgd50"] as const;
const models = ["baseline", "clean_only", "pgd_mixed"] as const;
type Condition = typeof conditions[number];
type Selection = "all" | Condition;
const source = `https://github.com/heechan9/AdversarialAI_Security/blob/${report.sourceCommit}`;
const evidence = `${source}/results/extensions/matched_cnn_20261024`;

export default function MatchedCnnFollowup() {
 const {locale} = useLocale();
 const en = locale === "en";
 const [selected, setSelected] = useState<Selection>("all");
 const labels = en ? {
  title: "Follow-up exploratory experiment",
  intro: "October 24, 2026 · A separate one-seed CNN study. These saved test results do not replace the original paper or October 12 panels.",
  replay: "Saved evaluation · no live inference",
  models: {baseline: "Original CNN", clean_only: "Clean-only training", pgd_mixed: "PGD-mixed training"},
  conditions: {clean: "Clean images", pgd7: "PGD7 · 1 restart", pgd50: "PGD50 · 5 restarts"},
  filter: "Compare an evaluation condition", all: "All three conditions",
  control: "This selector only filters this follow-up panel. The original model, vessel, epsilon and preprocessing-filter controls remain separate.",
  scope: "CNN · no preprocessing filter · seed 2026 · historical test set, 781 images per model",
  training: "Both new arms received 3 epochs of additional training from the same original CNN: clean-only loss versus 50:50 clean/PGD loss. Best checkpoints were selected on 689 validation images; every accuracy below uses the 781-image test set.",
  difference: "Mixed minus clean-only", net: "net correct",
  callout: "Strong attacks still expose a substantial weakness",
  strong: "PGD-mixed accuracy under PGD50 / 5 restarts is 6.15%. Compared with clean-only: 28 newly correct − 21 newly incorrect = 7 net correct (+0.90 percentage points).",
  interpretation: "PGD7 improves by 7.43 percentage points; the gain shrinks under PGD50. One seed does not establish stable or general defense effectiveness, statistical significance or maritime safety.",
  limits: "What remains unverified",
  seeds: "Only training seed 2026 is complete. Planned seeds 2027 and 2028 have not run.",
  reproduction: "Independent replay of the new trained models is incomplete. The original preprocessing study's external Stage B FAIL remains unresolved. Saved-file recalculation is not independent model reproduction.",
  data: "Historical baseline exposure and vessel/scene independence remain unresolved. No external holdout, AutoAttack or certified robustness result is supplied.",
  settings: "Evaluation conditions and provenance", protocol: "Own-gradient untargeted white-box PGD, L∞ ε=0.03, step size=0.005, batch=8; evaluation seed=2026+batch. PGD7: 7 steps / 1 restart. PGD50: 50 steps / 5 restarts.",
  state: "The nested paired-audit test_evaluation_complete=false is the preserved pre-inference snapshot. The separate evaluation completed all three 781-row CSVs. Independent approval remains false.",
  examples: "No verified PGD comparison images are supplied for these checkpoints. The image cases above remain the original FGSM examples. Only public saved records are linked here.",
  sources: "Public evidence", summary: "Result report and limitations", json: "Displayed data and hashes", code: "Executed evaluator", fail: "Existing Stage B FAIL", recorded: "correct / 781 test images",
 } : {
  title: "후속 탐색 실험",
  intro: "2026년 10월 24일 · 단일 seed의 별도 CNN 연구입니다. 이 저장 평가 결과는 기존 논문·10월 12일 패널의 수치를 대체하지 않습니다.",
  replay: "저장 평가 결과 · 실시간 추론 없음",
  models: {baseline: "원본 CNN", clean_only: "정상 추가학습", pgd_mixed: "PGD 혼합학습"},
  conditions: {clean: "정상 이미지", pgd7: "PGD7 · 1회 재시작", pgd50: "PGD50 · 5회 재시작"},
  filter: "비교할 평가 조건", all: "세 조건 모두 보기",
  control: "이 선택은 후속 실험 화면만 필터링합니다. 기존 모델·선종·공격 강도·전처리 필터 선택은 별도로 유지됩니다.",
  scope: "CNN · 전처리 필터 없음 · seed 2026 · 기존 시험셋, 모델별 781장",
  training: "동일 원본 CNN에서 두 군을 각각 3 epoch 추가학습했습니다. 정상 손실만 사용한 군과 정상·PGD 손실을 50:50으로 섞은 군입니다. 검증셋 689장으로 최적 체크포인트를 골랐으며, 아래 정확도는 모두 테스트 781장 기준입니다.",
  difference: "혼합학습 − 정상 추가학습", net: "정답 순증",
  callout: "강한 공격에는 여전히 취약합니다",
  strong: "PGD50·5회 재시작에서 PGD 혼합학습의 정확도는 6.15%입니다. 정상 추가학습 대비 새 정답 28장 − 새 오답 21장 = 정답 순증 7장(+0.90%p)입니다.",
  interpretation: "PGD7에서는 +7.43%p 개선됐지만 PGD50에서는 개선 폭이 작아졌습니다. 단일 seed로 안정적·전반적인 방어 성능, 통계적 유의성이나 실제 해양 안전을 입증하지 않습니다.",
  limits: "남은 검증",
  seeds: "학습 seed 2026만 완료됐습니다. 계획한 2027·2028은 미실행입니다.",
  reproduction: "새 학습 모델의 독립 재실행은 미완료입니다. 기존 전처리 연구의 외부 Stage B FAIL도 원인 미확정 상태로 유지합니다. 저장 파일 검산은 독립 모델 재현이 아닙니다.",
  data: "원본 모델의 과거 학습 노출과 선박·장면 단위 독립성은 미확정입니다. 외부 시험셋·AutoAttack·인증된 강건성 결과는 없습니다.",
  settings: "평가 조건과 출처", protocol: "모델별 자신의 경사를 쓰는 비표적 white-box PGD, L∞ ε=0.03, step size=0.005, batch=8, 평가 seed=2026+batch입니다. PGD7은 7 steps·1회, PGD50은 50 steps·5회 재시작입니다.",
  state: "paired audit의 test_evaluation_complete=false는 추론 전 기록을 보존한 값입니다. 별도 평가에서는 세 CSV가 각각 781행으로 완료됐습니다. 독립 승인 값은 false입니다.",
  examples: "이 체크포인트의 검증된 PGD 비교 이미지는 제공되지 않았습니다. 위 이미지 사례는 기존 FGSM 기록입니다. 여기에는 공개된 저장 근거만 연결합니다.",
  sources: "공개 근거", summary: "결과 보고서·한계", json: "화면 데이터·해시", code: "실행한 평가 코드", fail: "기존 Stage B FAIL", recorded: "정답 / 테스트 781장",
 };
 const visible = selected === "all" ? conditions : [selected];
 return <section id="followup" className="results-section matched-followup" aria-labelledby="matched-followup-heading" data-experiment="matched-cnn-20261024">
  <div className="section-heading"><div><span className="eyebrow">FOLLOW-UP / 2026-10-24</span><h2 id="matched-followup-heading">{labels.title}</h2></div><span className="matched-badge">{labels.replay}</span></div>
  <p className="matched-intro">{labels.intro}</p>
  <p className="matched-scope">{labels.scope}</p>
  <p className="matched-training">{labels.training}</p>
  <div className="matched-controls"><label htmlFor="matched-condition">{labels.filter}</label><select id="matched-condition" value={selected} onChange={event=>setSelected(event.target.value as Selection)} aria-describedby="matched-controls-note"><option value="all">{labels.all}</option>{conditions.map(condition=><option key={condition} value={condition}>{labels.conditions[condition]}</option>)}</select><p id="matched-controls-note">{labels.control}</p></div>
  <p className="sr-only" role="status">{selected === "all" ? labels.all : labels.conditions[selected]}</p>
  <div className="matched-comparisons">{visible.map(condition=>{
   const difference = report.mixedMinusCleanOnly[condition];
   return <article className="matched-condition-card" key={condition} aria-label={labels.conditions[condition]}>
    <h3>{labels.conditions[condition]}</h3><dl>{models.map(model=>{
     const metric = report.models[model][condition];
     return <div key={model} className={model === "pgd_mixed" ? "matched-mixed" : ""}><dt>{labels.models[model]}</dt><dd><strong>{(metric.accuracy * 100).toFixed(2)}%</strong><small>{metric.correct} / {metric.samples}</small><span className="sr-only">{labels.recorded}</span></dd></div>;
    })}</dl><p className="matched-difference">{labels.difference}<br/><b>+{difference.percentage_points.toFixed(2)} {en ? "pp" : "%p"}</b> · {labels.net} {difference.net_correct}{!en && "장"}</p>
   </article>;
  })}</div>
  <aside className="matched-caution" aria-labelledby="matched-caution-heading"><h3 id="matched-caution-heading">{labels.callout}</h3><p>{labels.strong}</p><p>{labels.interpretation}</p></aside>
  <div className="matched-limits"><h3>{labels.limits}</h3><ul><li>{labels.seeds}</li><li>{labels.reproduction}</li><li>{labels.data}</li></ul></div>
  <details className="matched-protocol"><summary>{labels.settings}</summary><p>{labels.protocol}</p><p>{labels.state}</p><p>{labels.examples}</p></details>
  <nav className="matched-sources" aria-label={labels.sources}>
   <a href={`${evidence}/README.md`}>{labels.summary} ↗</a><a href="/evidence/matched-cnn-followup.json">{labels.json} ↗</a>
   {models.map(model=><a key={model} href={`${evidence}/${model}.csv`}>{labels.models[model]} CSV ↗</a>)}
   <a href={`${evidence}/provenance/executed-evaluator-v2.py`}>{labels.code} ↗</a><a href={`${source}/docs/STAGE_B_HYEONSU_01_REVIEW.md`}>{labels.fail} ↗</a>
  </nav>
 </section>;
}
