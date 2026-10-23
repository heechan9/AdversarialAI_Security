"use client";
import {useState} from "react";
import {useLocale} from "./locale-provider";
import report from "../public/evidence/paired-defense-review.json";
import worst from "../public/evidence/worst-class-review.json";

export default function PairedDefenseReview({model,epsilon,method}:{model:string;epsilon:number;method:string}) {
 const {locale}=useLocale();
 const en=locale==="en";
 const [selected,setSelected]=useState("all");
 const condition=report.conditions.find(c=>c.model===model&&c.epsilon===epsilon&&c.defense===method);
 const weak=worst.conditions.find(c=>c.model===model&&c.epsilon===epsilon);
 if(!condition||!weak) return <p role="status">{en?"No matched saved evidence for this condition.":"이 조건에 일치하는 저장 근거가 없습니다."}</p>;
 const classes=condition.by_class as Record<string,typeof condition.overall>;
 const row=selected==="all"?condition.overall:classes[selected];
 if(!row) return <p role="status">{en?"Class evidence unavailable.":"클래스 근거가 없습니다."}</p>;
 const comparison=[
  [en?"Clean → filtered clean":"정상 → 필터 정상",row.clean_plain_to_defended],
  [en?"Attack → transfer + filter":"공격 → 전달 공격 + 필터",row.attack_plain_to_transfer_defended],
  [en?"Attack → adaptive + filter":"공격 → 방어 인지 공격 + 필터",row.attack_plain_to_adaptive_defended],
  [en?"Transfer → adaptive (with filter)":"전달 → 방어 인지 (필터 포함)",row.defended_transfer_to_adaptive]
 ] as const;
 const percent=(v:number|null)=>v===null?(en?"Undefined":"정의 불가"):`${(v*100).toFixed(2)}%`;
 return <section className="paired-review" aria-labelledby="paired-review-heading">
  <h3 id="paired-review-heading">{en?"Same images: gains and harms":"같은 사진에서 회복과 손실을 따로 보기"}</h3>
  <p>{en?"Saved replay only. The model, filter and epsilon follow the controls above. No new inference or robustness gain.":"저장 기록 재생입니다. 모델·필터·강도는 위 선택과 연동됩니다. 새 추론이나 강건성 향상이 아닙니다."}</p>
  <label htmlFor="paired-class">{en?"Review group":"검토 그룹"} </label>
  <select id="paired-class" value={selected} onChange={e=>setSelected(e.target.value)}>
   <option value="all">{en?"All 781 images":"전체 781장"}</option>
   {Object.keys(classes).map(label=><option value={label} key={label}>{label}</option>)}
  </select>
  <p>{en?"Paired image count":"동일 이미지 쌍 수"}: {row.n}</p>
  <div className="table-scroll"><table><thead><tr>
   <th>{en?"A → B":"A → B"}</th><th>{en?"Wrong → correct":"오답 → 정답"}</th><th>{en?"Correct → wrong":"정답 → 오답"}</th><th>{en?"Accuracy change":"정확도 차이"}</th>
  </tr></thead><tbody>{comparison.map(([label,value])=><tr key={label}><th scope="row">{label}</th><td>{value.gained}</td><td>{value.lost}</td><td>{value.b_minus_a_percentage_points.toFixed(2)} pp</td></tr>)}</tbody></table></div>
  <p>{en?"Adaptive attacks are newly constructed against the filter. These are paired outcomes, not the causal effect of a filter under identical perturbations.":"방어 인지 공격은 필터를 고려해 별도로 만든 공격입니다. 같은 사진의 결과 비교이지 동일 교란에서 필터의 인과 효과를 입증한 것은 아닙니다."}</p>
  <details><summary>{en?"ASR on the common clean-correct subset":"정상에서 둘 다 맞힌 공통 집합의 ASR"}</summary>
   <p>{en?"Common denominator":"공통 분모"}: {row.common_clean_correct_subset.n}. {en?"This selected subset is not the full test set or a paired comparison of the original unequal ASR denominators.":"전체 테스트 집합이 아닌 선택된 부분집합입니다. 분모가 다른 기존 ASR을 그대로 paired 비교한 수치가 아닙니다."}</p>
   <ul>{(["plain","transfer","adaptive"] as const).map(k=><li key={k}>{en?({plain:"Plain attack",transfer:"Transfer + filter",adaptive:"Adaptive + filter"}[k]):({plain:"원래 공격",transfer:"전달 + 필터",adaptive:"방어 인지 + 필터"}[k])}: {row.common_clean_correct_subset[k].successes}/{row.common_clean_correct_subset.n} · {percent(row.common_clean_correct_subset[k].asr)}</li>)}</ul>
  </details>
  <p className="paired-inference">{en?"Statistical inference withheld: McNemar p = null; bootstrap CI = null. Independent scene/vessel/session units are unverified. Repeated conditions do not create independent samples.":"통계 추론 보류: McNemar p = null; bootstrap CI = null. 촬영 장면·선박·세션의 독립성이 확인되지 않았습니다. 반복 조건을 독립 표본으로 세지 않습니다."}</p>
  <details><summary>{en?"Worst-class review: unfiltered baseline (all classes)":"취약 클래스 검토: 필터 없는 기준 결과 (전체 클래스)"}</summary>
   <p>{en?"Independent of the class selector. All ties are retained; this is not a worst-case safety guarantee.":"클래스 선택과 별개인 전체 클래스 비교이며 동률을 모두 표시합니다. 최악 상황의 안전 보장은 아닙니다."}</p>
   <ul>{([
    [en?"Lowest clean accuracy":"최저 정상 정확도",weak.minimum_clean_accuracy],
    [en?"Lowest attacked accuracy":"최저 공격 후 정확도",weak.minimum_attacked_accuracy],
    [en?"Highest conditional ASR":"최대 조건부 ASR",weak.maximum_conditional_ASR]
   ] as const).map(([label,value])=><li key={label}>{label}: {percent(value.value)} · {value.classes.join(", ")}</li>)}</ul>
   {epsilon===0&&<p>{en?"At epsilon zero, tied zero ASRs are the no-attack control, not safety certification.":"강도 0에서 ASR 0% 동률은 무공격 대조군이며 안전 인증이 아닙니다."}</p>}
  </details>
  <div className="defense-sources"><a href="/evidence/paired-defense-review.json">{en?"Paired report · hashes":"paired 보고서 · 해시"}</a><a href="/evidence/worst-class-review.json">{en?"Worst-class source":"취약 클래스 근거"}</a><a href={`https://github.com/heechan9/AdversarialAI_Security/tree/${report.source_head}`}>source {report.source_head.slice(0,8)}</a><a href="https://github.com/heechan9/AdversarialAI_Security/blob/9507e14a551fc697d9466e3257a1249d4579dc3d/docs/STAGE_B_HYEONSU_01_REVIEW.md">{en?"Reproduction limits":"독립 재현 한계"}</a></div>
 </section>;
}
