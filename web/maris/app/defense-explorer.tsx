"use client";
import PairedDefenseReview from "./paired-defense-review";
import {useLocale} from "./locale-provider";
import {useState} from "react";
import {Info, ArrowRight} from "lucide-react";
import {Button} from "@/components/ui/button";
import evidence from "../public/evidence/defense-comparison.json";
import {modelName,pct} from "@/lib/display";

export default function DefenseExplorer(){
 const {t}=useLocale();
 const [model,setModel]=useState("cnn"),[epsilon,setEpsilon]=useState(.03),[method,setMethod]=useState("mean");
 const group=evidence.methods.find(m=>m.id===method)!;
 const row=group.results.find(r=>r.model===model&&r.epsilon===epsilon)!;
 const a=row.overall.accuracy,n=row.overall.samples,asr=row.overall.asr_adaptive_defended;
 const stages=[{title:t("원본 사진"),value:a.clean,description:t("변화를 주기 전의 선박 분류 결과"),kind:"normal"},{title:t("작은 변화를 준 사진"),value:a.attacked,description:t("분류를 흔들도록 작은 변화를 준 사진"),kind:"attack"},{title:t("공격 사진 + 필터"),value:a.transfer_defended,description:t("같은 공격 사진에 필터를 적용한 분류 결과"),kind:"filter"},{title:t("필터를 고려한 공격 + 필터"),value:a.adaptive_defended,description:t("필터를 알고 새로 만든 공격"),kind:"adaptive"}];
 const difference=(a.defended_clean-a.clean)*100;
 return <section id="defense" className="results-section defense-lab">
  <div className="section-heading"><div><span className="eyebrow">03 / DEFENSE LAB</span><h2>{t("사진에 필터를 적용하면")}<br/>{t("AI의 선박 분류는 달라질까요?")}</h2></div><p>{t("두 가지 고정 필터 비교")}<br/>{t("탐색 실험 · 저장된 결과 재생")}</p></div>
  <p className="defense-intro">{t("선박 사진에 작은 변화를 주어 AI가 선박 종류를 다르게 분류하도록 시도한 실험입니다. 원본 → 공격 사진 → 필터 적용 후의 분류 결과를 비교해 보세요. 필터가 항상 정답을 되찾아 주는 것은 아닙니다.")}</p>
  <details className="record-table photo-guide"><summary>{t("사진을 바꾸는 이유와 필터의 역할 알아보기")}</summary>
   <h3>{t("사진에 왜 작은 변화를 주나요?")}</h3><p>{t("공격은 사진 속 배를 바꾸는 대신, 사진을 이루는 작은 색 점인 픽셀 값을 바꿔 AI의 분류를 흔드는 실험입니다. 여기서는 FGSM이라는 방법을 썼습니다. ε는 허용한 변화의 최대 크기이며, 0은 변화를 주지 않은 비교 조건입니다. 변화가 눈에 잘 안 보일 수도 있지만, 모든 사진에서 안 보인다는 뜻은 아닙니다.")}</p>
   <h3>{t("필터는 무엇을 하나요?")}</h3><p>{t("평균·가우시안 필터는 주변 픽셀 값을 섞어 작은 변화를 줄이려는 처리입니다. 배의 윤곽 같은 세부 정보도 함께 줄어들 수 있어, 원본에서 맞히던 사진을 틀릴 수도 있습니다. 공격을 없애거나 정답을 복원한다고 보장하지 않습니다.")}</p>
   <h3>{t("세 번째와 네 번째 카드는 어떻게 다른가요?")}</h3><p>{t("세 번째는 두 번째와 같은 공격 사진에 필터만 적용한 결과입니다. 네 번째는 필터 사용까지 고려해 새로 만든 공격 사진을 필터에 통과시킨 결과입니다. 더 어려운 조건에서도 효과가 있는지 따로 보는 것이며, 한 사진에 처리를 계속 더한 네 단계는 아닙니다.")}</p>
   <h3>{t("결과는 어떻게 읽나요?")}</h3><p>{t("정확도는 전체 {n}장 중 선박 종류를 맞힌 비율입니다. 한 사진의 정답 확률이 아닙니다. 카드 아래 정답 수를 함께 보세요. 이 선박 이미지 분류 실험은 실제 선박의 충돌 방지나 자율운항 안전을 입증하지 않습니다.",{n})}</p>
  </details>
  <div className="defense-controls"><div><label htmlFor="defense-model">{t("살펴볼 AI 모델")}</label><select id="defense-model" value={model} onChange={e=>setModel(e.target.value)}>{evidence.models.map(m=><option key={m} value={m}>{modelName(m)}</option>)}</select></div><div><label htmlFor="defense-method">{t("결과를 비교할 필터")}</label><select id="defense-method" value={method} onChange={e=>setMethod(e.target.value)}>{evidence.methods.map(m=><option key={m.id} value={m.id}>{t(m.name)}</option>)}</select></div><fieldset><legend>{t("공격 강도 ε")}</legend><div className="epsilon-options">{evidence.epsilons.map(e=><Button key={e} variant="outline" aria-pressed={epsilon===e} className={epsilon===e?"selected":""} onClick={()=>setEpsilon(e)}>{e===0?t("0 · 대조군"):e}</Button>)}</div></fieldset></div>
  <p className="condition-label">{modelName(model)} · {t(group.name)} · ε = {epsilon} · {t("전체 {n}장 기준 정확도",{n})}<br/><span>{t("위 단일 이미지 사례와 독립적으로 조건을 선택합니다. 선택한 조건으로 미리 계산해 둔 결과이며, 이 화면에서 새 사진 생성이나 AI 분석을 실행하지 않습니다.")}</span></p>
  <p className="condition-label">{t("정확도: 전체 {n}장 중 선박 종류를 맞힌 비율 · 한 사진의 정답 확률이 아닙니다.",{n})}</p>
  <div className="defense-stages" aria-live="polite">{stages.map((stage,i)=><article key={stage.kind} className={`defense-stage ${stage.kind}`}><div className="stage-number">{String(i+1).padStart(2,"0")}<ArrowRight size={17}/></div><h3>{stage.title}</h3><strong>{pct(stage.value)}</strong><p>{stage.description}</p><small>{t("{correct} / {n}장 정답",{correct:Math.round(stage.value*n),n})}</small></article>)}</div>
  <div className="defense-reading"><Info size={23}/><div><h3>{epsilon===0?t("공격 강도 0에서는 필터 자체의 영향을 봅니다."):t("필터 적용만 보고 ‘방어 성공’이라 판단할 수 없습니다.")}</h3><p>{epsilon===0?t("사진을 공격하지 않아도 필터가 AI의 판단을 바꿀 수 있습니다. 정상 사진에서의 성능도 함께 평가해야 합니다."):t("세 번째 카드는 같은 공격 입력에 필터를 적용한 결과입니다. 네 번째는 필터까지 고려해 다시 만든 공격입니다. 이 두 조건을 구분해야 방어의 한계를 볼 수 있습니다.")}</p></div></div>
  <div className="defense-cost"><div><span>{t("공격 없는 사진에 필터만 적용하면")}</span><b>{pct(a.clean)} → {pct(a.defended_clean)}</b><p>{difference<0?t("정확도 감소"):t("정확도 증가")} {t("{difference}%p · 잘 맞히던 사진 {harmed}장 오답 전환 / 기존 오답 {recovered}장 회복",{difference:Math.abs(difference).toFixed(2),harmed:row.overall.clean_harmed,recovered:row.overall.clean_recovered})}</p></div><div><span>{t("방어를 고려한 공격 성공률 · ASR")}</span><b>{t(pct(asr.asr))}</b><p>{t("필터 적용 정상 정답 {denominator}장 중 {successes}장 오답 전환. 위의 방어 없는 ASR과 분모가 다릅니다.",{denominator:asr.denominator,successes:asr.successes})}</p></div></div>
  <div className="filter-comparison"><h3>{t("두 필터를 같은 조건에서 비교하면")}</h3><p>{t("각 막대는 전체 {n}장에 대한 정확도입니다. 높을수록 더 많이 맞혔다는 뜻입니다.",{n})}</p><div className="filter-grid">{evidence.methods.map(m=>{const r=m.results.find(x=>x.model===model&&x.epsilon===epsilon)!;return <article key={m.id}><h4>{t(m.name)}</h4><p>{t(m.description)}</p>{[{label:t("필터 적용 정상"),value:r.overall.accuracy.defended_clean},{label:t("전달 공격 + 필터"),value:r.overall.accuracy.transfer_defended},{label:t("방어 인지 공격 + 필터"),value:r.overall.accuracy.adaptive_defended}].map((v,i)=><div className={`filter-bar condition-${i}`} key={v.label}><div><span>{v.label}</span><b>{pct(v.value)}</b></div><div className="bar-track"><span style={{width:`${v.value*100}%`}}/></div></div>)}</article>})}</div></div>
  <PairedDefenseReview model={model} epsilon={epsilon} method={method}/>
  <details className="record-table"><summary>{t("두 필터 · 두 모델 · 모든 강도의 상세 수치와 분모")}</summary><div className="table-scroll"><table><thead><tr><th>{t("필터")}</th><th>{t("모델")}</th><th>ε</th><th>{t("정상")}</th><th>{t("필터 정상")}</th><th>{t("공격")}</th><th>{t("전달+필터")}</th><th>{t("방어 인지+필터")}</th><th>{t("방어 인지 ASR")}</th></tr></thead><tbody>{evidence.methods.flatMap(m=>m.results.map(r=><tr key={m.id+r.model+r.epsilon}><th>{t(m.name)}</th><td>{modelName(r.model)}</td><td>{r.epsilon}</td>{[r.overall.accuracy.clean,r.overall.accuracy.defended_clean,r.overall.accuracy.attacked,r.overall.accuracy.transfer_defended,r.overall.accuracy.adaptive_defended].map((v,i)=><td key={i}>{pct(v)}</td>)}<td>{t(pct(r.overall.asr_adaptive_defended.asr))} ({r.overall.asr_adaptive_defended.successes}/{r.overall.asr_adaptive_defended.denominator})</td></tr>))}</tbody></table></div></details>
  <div className="boundaries"><Info size={19}/><p>{t("한 번의 FGSM 공격에 대한 탐색 결과입니다. 필터의 일반적 우수성이나 실제 운항 안전성을 입증하지 않습니다. 방어 전후 원본 이미지 배열은 없어 새 방어 이미지·차이 지도를 만들지 않았습니다. 이 화면의 원기록은 산출물 감사를 통과했지만 독립적인 모델 재추론은 수행하지 않았습니다.")}</p></div>
  <div className="defense-sources">{evidence.methods.map(m=><a key={m.id} href={m.sourceUrl} target="_blank" rel="noreferrer">{t(m.name)} {t("원기록 ↗")}</a>)}<a href="/evidence/defense-comparison-provenance.json" target="_blank">{t("파일 해시·검증 범위 ↗")}</a></div>
 </section>
}
