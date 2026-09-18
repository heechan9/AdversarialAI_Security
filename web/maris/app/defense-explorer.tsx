"use client";
import {useState} from "react";
import {Info, ArrowRight} from "lucide-react";
import {Button} from "@/components/ui/button";
import evidence from "../public/evidence/defense-comparison.json";
import {modelName,pct} from "@/lib/display";

export default function DefenseExplorer(){
 const [model,setModel]=useState("cnn"),[epsilon,setEpsilon]=useState(.03),[method,setMethod]=useState("mean");
 const group=evidence.methods.find(m=>m.id===method)!;
 const row=group.results.find(r=>r.model===model&&r.epsilon===epsilon)!;
 const a=row.overall.accuracy,n=row.overall.samples,asr=row.overall.asr_adaptive_defended;
 const stages=[{title:"공격 전",value:a.clean,description:"원래 사진을 보고 맞힌 비율",kind:"normal"},{title:"공격 후",value:a.attacked,description:"사진의 픽셀을 바꿨을 때",kind:"attack"},{title:"필터 적용",value:a.transfer_defended,description:"위 공격 입력을 부드럽게 처리",kind:"filter"},{title:"방어까지 고려한 공격",value:a.adaptive_defended,description:"필터를 알고 새로 만든 공격",kind:"adaptive"}];
 const difference=(a.defended_clean-a.clean)*100;
 return <section id="defense" className="results-section defense-lab">
  <div className="section-heading"><div><span className="eyebrow">03 / DEFENSE LAB</span><h2>부드럽게 만든 사진,<br/>AI를 지켜줄 수 있을까?</h2></div><p>두 가지 고정 필터 비교<br/>탐색 실험 · 저장된 결과 재생</p></div>
  <p className="defense-intro">필터는 주변 픽셀을 섞어 사진을 부드럽게 만듭니다. 기존 공격에 도움이 되는지, 공격자가 필터까지 알고 있어도 효과가 있는지 따로 확인했습니다.</p>
  <div className="defense-controls"><div><label htmlFor="defense-model">살펴볼 AI 모델</label><select id="defense-model" value={model} onChange={e=>setModel(e.target.value)}>{evidence.models.map(m=><option key={m} value={m}>{modelName(m)}</option>)}</select></div><div><label htmlFor="defense-method">사진에 적용할 필터</label><select id="defense-method" value={method} onChange={e=>setMethod(e.target.value)}>{evidence.methods.map(m=><option key={m.id} value={m.id}>{m.name}</option>)}</select></div><fieldset><legend>공격 강도 ε</legend><div className="epsilon-options">{evidence.epsilons.map(e=><Button key={e} variant="outline" aria-pressed={epsilon===e} className={epsilon===e?"selected":""} onClick={()=>setEpsilon(e)}>{e===0?"0 · 대조군":e}</Button>)}</div></fieldset></div>
  <p className="condition-label">{modelName(model)} · {group.name} · ε = {epsilon} · 전체 {n}장 기준 정확도<br/><span>위 이미지 사례·전체 통계와 독립적으로 선택합니다. 새 사진을 생성하거나 추론하지 않습니다.</span></p>
  <div className="defense-stages">{stages.map((stage,i)=><article key={stage.kind} className={`defense-stage ${stage.kind}`}><div className="stage-number">{String(i+1).padStart(2,"0")}<ArrowRight size={17}/></div><h3>{stage.title}</h3><strong>{pct(stage.value)}</strong><p>{stage.description}</p><small>{Math.round(stage.value*n)} / {n}장 정답</small></article>)}</div>
  <div className="defense-reading"><Info size={23}/><div><h3>{epsilon===0?"공격 강도 0에서는 필터 자체의 영향을 봅니다.":"필터 적용만 보고 ‘방어 성공’이라 판단할 수 없습니다."}</h3><p>{epsilon===0?"사진을 공격하지 않아도 필터가 AI의 판단을 바꿀 수 있습니다. 정상 사진에서의 성능도 함께 평가해야 합니다.":"세 번째 카드는 같은 공격 입력에 필터를 적용한 결과입니다. 네 번째는 필터까지 고려해 다시 만든 공격입니다. 이 두 조건을 구분해야 방어의 한계를 볼 수 있습니다."}</p></div></div>
  <div className="defense-cost"><div><span>공격 없는 사진에 필터만 적용하면</span><b>{pct(a.clean)} → {pct(a.defended_clean)}</b><p>{difference<0?"정확도 감소":"정확도 증가"} {Math.abs(difference).toFixed(2)}%p · 잘 맞히던 사진 {row.overall.clean_harmed}장 오답 전환 / 기존 오답 {row.overall.clean_recovered}장 회복</p></div><div><span>방어를 고려한 공격 성공률 · ASR</span><b>{pct(asr.asr)}</b><p>필터 적용 정상 정답 {asr.denominator}장 중 {asr.successes}장 오답 전환. 위의 방어 없는 ASR과 분모가 다릅니다.</p></div></div>
  <div className="filter-comparison"><h3>두 필터를 같은 조건에서 비교하면</h3><p>각 막대는 전체 {n}장에 대한 정확도입니다. 높을수록 더 많이 맞혔다는 뜻입니다.</p><div className="filter-grid">{evidence.methods.map(m=>{const r=m.results.find(x=>x.model===model&&x.epsilon===epsilon)!;return <article key={m.id}><h4>{m.name}</h4><p>{m.description}</p>{[{label:"필터 적용 정상",value:r.overall.accuracy.defended_clean},{label:"전달 공격 + 필터",value:r.overall.accuracy.transfer_defended},{label:"방어 인지 공격 + 필터",value:r.overall.accuracy.adaptive_defended}].map((v,i)=><div className={`filter-bar condition-${i}`} key={v.label}><div><span>{v.label}</span><b>{pct(v.value)}</b></div><div className="bar-track"><span style={{width:`${v.value*100}%`}}/></div></div>)}</article>})}</div></div>
  <details className="record-table"><summary>두 필터 · 두 모델 · 모든 강도의 상세 수치와 분모</summary><div className="table-scroll"><table><thead><tr><th>필터</th><th>모델</th><th>ε</th><th>정상</th><th>필터 정상</th><th>공격</th><th>전달+필터</th><th>방어 인지+필터</th><th>방어 인지 ASR</th></tr></thead><tbody>{evidence.methods.flatMap(m=>m.results.map(r=><tr key={m.id+r.model+r.epsilon}><th>{m.name}</th><td>{modelName(r.model)}</td><td>{r.epsilon}</td>{[r.overall.accuracy.clean,r.overall.accuracy.defended_clean,r.overall.accuracy.attacked,r.overall.accuracy.transfer_defended,r.overall.accuracy.adaptive_defended].map((v,i)=><td key={i}>{pct(v)}</td>)}<td>{pct(r.overall.asr_adaptive_defended.asr)} ({r.overall.asr_adaptive_defended.successes}/{r.overall.asr_adaptive_defended.denominator})</td></tr>))}</tbody></table></div></details>
  <div className="boundaries"><Info size={19}/><p>한 번의 FGSM 공격에 대한 탐색 결과입니다. 필터의 일반적 우수성이나 실제 운항 안전성을 입증하지 않습니다. 방어 전후 원본 이미지 배열은 없어 새 방어 이미지·차이 지도를 만들지 않았습니다. 이 화면의 원기록은 산출물 감사를 통과했지만 독립적인 모델 재추론은 수행하지 않았습니다.</p></div>
  <div className="defense-sources">{evidence.methods.map(m=><a key={m.id} href={m.sourceUrl} target="_blank" rel="noreferrer">{m.name} 원기록 ↗</a>)}<a href="/evidence/defense-comparison-provenance.json" target="_blank">파일 해시·검증 범위 ↗</a></div>
 </section>
}
