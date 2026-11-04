"use client";
import {useEffect, useState} from 'react';
import {useLocale} from './locale-provider';
import {conditions, models, outcomes, selectMatched, selectTriage, matchedExport, triageExport, csv, caseFields, differenceFields, validateDiagnostics, type Diagnostics, type Condition, type Outcome, type Model} from '@/lib/research-diagnostics';

const percent=(v:number|null)=>v===null?'—':`${(v*100).toFixed(2)}%`;
const signed=(v:number)=>`${v>0?'+':''}${v}`;
const repository='https://github.com/heechan9/AdversarialAI_Security';
const savedSource=`${repository}/blob/13d92a15c3b8953e24b5d44326cd2327973a7a25/results/extensions/matched_cnn_20261024`;
const originalSource=`${repository}/blob/d4b092361c16fff875e1d13532dacf5230564216/`;
const PAGE_SIZE=15;

function download(name:string,content:string,type:string) {
 const url=URL.createObjectURL(new Blob([content],{type}));
 const link=document.createElement('a');link.href=url;link.download=name;document.body.appendChild(link);link.click();link.remove();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function Pager({page,total,onPage,en}:{page:number;total:number;onPage:(n:number)=>void;en:boolean}) {
 const pages=Math.max(1,Math.ceil(total/PAGE_SIZE));
 return <div className="diagnostic-pager"><button disabled={page===0} onClick={()=>onPage(page-1)}>{en?'Previous':'이전'}</button><span>{page+1} / {pages}</span><button disabled={page>=pages-1} onClick={()=>onPage(page+1)}>{en?'Next':'다음'}</button></div>;
}
function Downloads({onCsv,onJson,en}:{onCsv:()=>void;onJson:()=>void;en:boolean}) {
 return <div className="diagnostic-downloads"><button onClick={onCsv}>{en?'Selected cases · CSV':'선택 표본 · CSV'}</button><button onClick={onJson}>{en?'Selection + evidence · JSON':'선택 조건·근거 · JSON'}</button></div>;
}

export function MatchedExplorer({data}:{data:Diagnostics}) {
 const {locale}=useLocale(), en=locale==='en';
 const [condition,setCondition]=useState<Condition>('pgd50');
 const [className,setClassName]=useState('all');
 const [outcome,setOutcome]=useState<Outcome>('changed');
 const [page,setPage]=useState(0);
 const report=data.matched[condition],{summary,cases}=selectMatched(data,condition,className,outcome);
 const paired=summary.mixed_vs_clean_only,common=summary.common_clean_correct_asr;
 const names:Record<Model,string>=en?{baseline:'Original CNN',clean_only:'B · Clean-only',pgd_mixed:'C · PGD-mixed'}:{baseline:'원본 CNN',clean_only:'B · 정상 추가학습',pgd_mixed:'C · PGD 혼합학습'};
 const outcomeName:Record<Outcome,string>=en?{all:'All outcomes',changed:'Correctness changed',newly_correct:'Newly correct',newly_incorrect:'Newly incorrect',both_correct:'Both correct',both_wrong:'Both wrong'}:{all:'모든 결과',changed:'정오가 바뀐 표본',newly_correct:'새 정답',newly_incorrect:'새 오답',both_correct:'둘 다 정답',both_wrong:'둘 다 오답'};
 const classNames=report.by_class.map(c=>c.true_class);
 const changeClass=(value:string)=>{setClassName(value);setPage(0);};
 const exportJson=()=>download(`maris-cnn-${condition}.json`,JSON.stringify(matchedExport(data,condition,className,outcome),null,2),'application/json');
 return <div className="diagnostic-panel" id="cnn-diagnostic-panel">
  <p className="diagnostic-intro">{en?'Compare the two training arms on the same saved image IDs. B and C received equal additional training; each model was attacked separately.':'같은 이미지 ID로 두 학습군을 비교합니다. B와 C의 추가학습량은 같으며, 공격 입력은 각 모델에서 따로 생성했습니다.'}</p>
  <div className="diagnostic-filters">
   <label htmlFor="diag-condition">{en?'Evaluation':'평가 조건'}<select id="diag-condition" value={condition} onChange={e=>{setCondition(e.target.value as Condition);setPage(0);}}>{conditions.map(c=><option key={c} value={c}>{c==='clean'?(en?'Clean images':'정상 이미지'):c==='pgd7'?'PGD7 · 1 restart':'PGD50 · 5 restarts'}</option>)}</select></label>
   <label htmlFor="diag-class">{en?'True vessel class':'실제 선종'}<select id="diag-class" value={className} onChange={e=>changeClass(e.target.value)}><option value="all">{en?'All vessel classes':'전체 선종'}</option>{classNames.map(c=><option key={c}>{c}</option>)}</select></label>
   <label htmlFor="diag-outcome">{en?'Case outcome · C versus B':'표본 결과 · C와 B 비교'}<select id="diag-outcome" value={outcome} aria-describedby="diag-denominator" onChange={e=>{setOutcome(e.target.value as Outcome);setPage(0);}}>{outcomes.map(o=><option key={o} value={o}>{outcomeName[o]}</option>)}</select></label>
  </div>
  <div className="diagnostic-scope" role="status">{className==='all'?(en?'All vessel classes':'전체 선종'):className} · {summary.samples} {en?'images in the metric cohort':'장 기준 집계'} · {cases.length} {en?'selected cases':'장 표본 선택'}</div>
  <div className="diagnostic-metrics"><div><span>{en?'Newly correct · C vs B':'새 정답 · C와 B 비교'}</span><strong>{paired.newly_correct}</strong></div><div><span>{en?'Newly incorrect':'새 오답'}</span><strong>{paired.newly_incorrect}</strong></div><div><span>{en?'Net correct':'정답 순변화'}</span><strong>{signed(paired.net_correct)}</strong></div></div>
  <p id="diag-denominator" className="diagnostic-note">{en?'Outcome filters change the case list only. Accuracy and ASR always use every image in the selected true class, including cases hidden by the filter.':'표본 결과 필터는 아래 목록만 바꿉니다. 정확도와 ASR은 숨겨진 표본까지 포함한 선택 선종 전체를 기준으로 계산합니다.'}</p>
  <div className="diagnostic-table"><table><caption>{en?'Accuracy and own-clean ASR':'정확도와 모델별 정상 정답 기준 ASR'}</caption><thead><tr><th scope="col">{en?'Model':'모델'}</th><th scope="col">{en?'Correct / images':'정답 / 표본'}</th><th scope="col">{en?'Accuracy':'정확도'}</th><th scope="col">{en?'ASR · failures / own clean-correct':'ASR · 오답 전환 / 해당 모델 정상 정답'}</th></tr></thead><tbody>{models.map(m=>{const v=summary.models[m];return <tr key={m}><th scope="row">{names[m]}</th><td>{v.correct} / {summary.samples}</td><td>{percent(v.accuracy)}</td><td>{v.own_clean_asr===null?'—':`${percent(v.own_clean_asr)} · ${v.own_clean_asr_successes} / ${v.own_clean_asr_denominator}`}</td></tr>;})}</tbody></table></div>
  <p className="diagnostic-common">{en?'Same clean-correct cohort for B/C':'B·C가 정상 입력에서 함께 맞힌 공통 집합'}: <b>{common.samples}</b> · ASR B {percent(common.models.clean_only.asr)}{common.models.clean_only.successes===null?'':` (${common.models.clean_only.successes}/${common.samples})`} / C {percent(common.models.pgd_mixed.asr)}{common.models.pgd_mixed.successes===null?'':` (${common.models.pgd_mixed.successes}/${common.samples})`}. {en?'Clean and zero denominators show —.':'정상 조건과 분모 0은 —로 표시합니다.'}</p>
  <details className="diagnostic-details"><summary>{en?'Compare all 10 classes · select a row to drill down':'10개 선종 비교 · 행을 선택해 표본 보기'}</summary><div className="diagnostic-table"><table><thead><tr><th scope="col">{en?'True class':'실제 선종'}</th><th scope="col">n</th><th scope="col">B</th><th scope="col">C</th><th scope="col">{en?'Gained':'새 정답'}</th><th scope="col">{en?'Lost':'새 오답'}</th><th scope="col">{en?'Net':'순변화'}</th></tr></thead><tbody>{report.by_class.map(c=><tr key={c.true_class}><th scope="row"><button className="diagnostic-link" aria-pressed={className===c.true_class} onClick={()=>changeClass(c.true_class)}>{c.true_class}</button></th><td>{c.samples}</td><td>{c.models.clean_only.correct}</td><td>{c.models.pgd_mixed.correct}</td><td>{c.mixed_vs_clean_only.newly_correct}</td><td>{c.mixed_vs_clean_only.newly_incorrect}</td><td>{signed(c.mixed_vs_clean_only.net_correct)}</td></tr>)}</tbody></table></div></details>
  <div className="diagnostic-list-heading"><h3>{en?'Saved image-level predictions':'표본별 저장 예측'}</h3><Downloads en={en} onJson={exportJson} onCsv={()=>download(`maris-cnn-${condition}.csv`,csv(cases,caseFields),'text/csv;charset=utf-8')}/></div>
  {cases.length===0?<p className="diagnostic-empty" role="status">{en?'No cases match these filters. The class population and metrics above are unchanged.':'선택 조건에 해당하는 표본이 없습니다. 위 선종의 표본 수와 집계는 그대로 유지됩니다.'}</p>:<><div className="diagnostic-table"><table><caption>{en?'Predictions under the selected evaluation; exports also include clean predictions.':'선택한 평가 조건의 예측입니다. 다운로드에는 정상 입력 예측도 포함됩니다.'}</caption><thead><tr><th scope="col">{en?'Image ID / true class':'이미지 ID / 실제 선종'}</th><th scope="col">{en?'Original':'원본'}</th><th scope="col">B</th><th scope="col">C</th><th scope="col">{en?'C versus B':'C와 B 비교'}</th></tr></thead><tbody>{cases.slice(page*PAGE_SIZE,(page+1)*PAGE_SIZE).map(c=><tr key={c.relative_path}><th scope="row"><code>{c.relative_path}</code><small>{c.true_class}</small></th>{models.map(m=><td key={m}>{classNames[c[`${m}_condition_pred`]]}</td>)}<td>{outcomeName[c.outcome]}</td></tr>)}</tbody></table></div><Pager page={page} total={cases.length} onPage={setPage} en={en}/></>}
  <details className="diagnostic-details"><summary>{en?'Evidence and export scope':'근거·다운로드 범위'}</summary><p>{en?'CSV contains every selected case, across all pages. JSON adds the selected cohort metrics, source hashes, attack settings and study boundaries. No raw images or trained models are included.':'CSV에는 페이지와 관계없이 선택 표본 전체가 담깁니다. JSON에는 집계 분모, 원본 해시, 공격 설정, 연구 범위도 포함됩니다. 원본 이미지와 학습 모델은 포함되지 않습니다.'}</p><p>{en?'One training seed (2026), descriptive saved-file audit. Independent model reproduction is incomplete.':'학습 시드 2026 하나의 기술적 집계이며, 저장 파일을 검산한 결과입니다. 독립 모델 재현은 미완료입니다.'}</p><a href={savedSource+'/evaluation.json'} target="_blank" rel="noreferrer">{en?'Saved evaluation ↗':'원본 평가 기록 ↗'}</a> · <a href="/evidence/research-diagnostics.json" target="_blank">{en?'Full diagnostic snapshot ↗':'전체 진단 기록 ↗'}</a></details>
 </div>;
}

export function TriageExplorer({data}:{data:Diagnostics}) {
 const {locale}=useLocale(),en=locale==='en';
 const [method,setMethod]=useState('all'),[model,setModel]=useState('all'),[pipeline,setPipeline]=useState('all'),[image,setImage]=useState('all'),[page,setPage]=useState(0);
 const filters={method,model,pipeline,relative_path:image},cases=selectTriage(data,filters),t=data.triage;
 const pipelineNames:Record<string,string>=en?{clean:'Clean',defended_clean:'Defended clean',attacked:'Attacked',transfer_defended:'Transfer defended',adaptive_defended:'Adaptive defended'}:{clean:'정상',defended_clean:'정상+방어',attacked:'공격',transfer_defended:'전이 공격+방어',adaptive_defended:'방어 인지 공격'};
 const controls=[{id:'method',label:en?'Filter method':'전처리 필터',value:method,set:setMethod,options:['gaussian','mean']},{id:'model',label:en?'Model':'모델',value:model,set:setModel,options:['cnn','mobilenet']},{id:'pipeline',label:en?'Evaluation path':'평가 경로',value:pipeline,set:setPipeline,options:Object.keys(pipelineNames)},{id:'image',label:en?'Image ID':'이미지 ID',value:image,set:setImage,options:[...new Set(t.cases.map(c=>c.relative_path))]}];
 return <div className="diagnostic-panel" id="triage-diagnostic-panel">
  <p className="diagnostic-intro">{en?'Inspect the 16 prediction differences preserved from the external run. Counts repeat images across evaluation conditions; they are not independent samples or proof of a cause.':'외부 실행에서 보존된 예측 차이 16건을 추적합니다. 같은 이미지가 여러 평가 조건에 반복되며, 발생 횟수가 독립 표본 수나 원인 증명을 뜻하지 않습니다.'}</p>
  <div className="diagnostic-verdicts"><span>Stage B · {t.status_by_run['external-01']}</span><span>PC · {t.status_by_run['pc-full-20260928']}</span><span>{en?'Cause':'원인'} · {t.cause_status}</span><span>{en?'Issue':'불일치 이력'} · {t.discrepancy_state['cross-environment-01']}</span></div>
  <div className="diagnostic-metrics"><div><span>{en?'Compared prediction cells':'비교한 예측 셀'}</span><strong>{t.totals.compared_prediction_cells.toLocaleString('en-US')}</strong></div><div><span>{en?'Different prediction cells':'예측 차이'}</span><strong>{t.totals.differing_prediction_cells}</strong></div><div><span>{en?'Unique affected images':'영향받은 고유 이미지'}</span><strong>{t.totals.unique_affected_images}</strong></div></div>
  <div className="diagnostic-filters diagnostic-triage-filters">{controls.map(c=><label key={c.id} htmlFor={'triage-'+c.id}>{c.label}<select id={'triage-'+c.id} value={c.value} onChange={e=>{c.set(e.target.value);setPage(0);}}><option value="all">{en?'All':'전체'}</option>{c.options.map(o=><option key={o} value={o}>{c.id==='pipeline'?pipelineNames[o]:o}</option>)}</select></label>)}</div>
  <p className="diagnostic-scope" role="status">{cases.length} {en?'selected differences':'건 선택'} · {new Set(cases.map(c=>c.relative_path)).size} {en?'unique images':'개 고유 이미지'}</p>
  <p className="diagnostic-note">{en?'Filters select the records below only. The three totals above cover all saved conditions and remain fixed.':'필터는 아래 기록만 선택합니다. 위 세 집계는 저장된 전체 조건을 기준으로 유지됩니다.'}</p>
  <Downloads en={en} onCsv={()=>download('maris-external-differences.csv',csv(cases,differenceFields),'text/csv;charset=utf-8')} onJson={()=>download('maris-external-differences.json',JSON.stringify(triageExport(data,filters),null,2),'application/json')}/>
  {cases.length===0?<p className="diagnostic-empty" role="status">{en?'No saved differences match these filters. This does not change the external FAIL verdict.':'선택 조건의 저장 불일치가 없습니다. 외부 실행의 FAIL 판정이 바뀌는 것은 아닙니다.'}</p>:<><div className="diagnostic-table"><table><caption>{en?'Reference → external run · label indices follow the canonical class map.':'기준 → 외부 실행 · 클래스 번호는 원본 클래스 매핑을 따릅니다.'}</caption><thead><tr><th scope="col">{en?'Image ID':'이미지 ID'}</th><th scope="col">{en?'Condition':'조건'}</th><th scope="col">{en?'True label':'정답 번호'}</th><th scope="col">{en?'Reference → actual':'기준 → 실행'}</th><th scope="col">{en?'Evidence':'근거'}</th></tr></thead><tbody>{cases.slice(page*PAGE_SIZE,(page+1)*PAGE_SIZE).map(c=><tr key={[c.method,c.file,c.pipeline,c.row_index].join(':')}><th scope="row"><code>{c.relative_path}</code><small>row {c.row_index} · 0-based</small></th><td>{c.method} · {c.model} · ε {c.epsilon}<small>{pipelineNames[c.pipeline]}</small></td><td>{c.true_index}</td><td>{c.reference} → {c.actual}</td><td><a href={originalSource+c.evidence_path} target="_blank" rel="noreferrer">JSON ↗</a><details><summary>SHA-256</summary><code>{c.evidence_sha256}</code></details></td></tr>)}</tbody></table></div><Pager page={page} total={cases.length} onPage={setPage} en={en}/></>}
  <details className="diagnostic-details"><summary>{en?'Condition totals and provenance':'조건별 집계·출처'}</summary><p>{en?'Rows below retain all conditions, including zero differences. Each row compares 781 prediction cells.':'차이가 없는 조건도 포함한 전체 집계입니다. 각 행은 예측 셀 781개를 비교합니다.'}</p><div className="diagnostic-table"><table><thead><tr><th scope="col">{en?'Method / model / ε':'필터 / 모델 / ε'}</th><th scope="col">{en?'Path':'평가 경로'}</th><th scope="col">{en?'Differences / cells':'차이 / 셀'}</th></tr></thead><tbody>{t.condition_groups.map((g,i)=><tr key={i}><td>{g.method} / {g.model} / {g.epsilon}</td><td>{pipelineNames[String(g.pipeline)]}</td><td>{g.differing_prediction_cells} / {g.compared_prediction_cells}</td></tr>)}</tbody></table></div><p>{en?'This view audits saved JSON accounting. The recorded reference/actual CSV hashes are declarations from the original reports; private CSVs were not reopened or rehashed. Original training manifests remain missing.':'저장 JSON의 집계를 검산한 화면입니다. 기준·실행 CSV 해시는 원본 보고서에 기록된 선언이며, 비공개 CSV를 다시 열어 해싱하지 않았습니다. 원본 학습 manifest는 여전히 확보되지 않았습니다.'}</p><a href={originalSource+'configs/classes.json'} target="_blank" rel="noreferrer">{en?'Canonical class map ↗':'원본 클래스 매핑 ↗'}</a> · <a href={originalSource+'results/verification/discrepancy_log.json'} target="_blank" rel="noreferrer">{en?'Issue history ↗':'불일치 이력 ↗'}</a></details>
 </div>;
}

export default function ResearchDiagnostics() {
 const {locale}=useLocale(),en=locale==='en';
 const [tab,setTab]=useState<'cnn'|'triage'>('cnn'),[data,setData]=useState<Diagnostics|null>(null),[failed,setFailed]=useState(false),[attempt,setAttempt]=useState(0);
 useEffect(()=>{
  const controller=new AbortController();
  fetch('/evidence/research-diagnostics.json',{signal:controller.signal}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{validateDiagnostics(d);if(!controller.signal.aborted)setData(d);}).catch(()=>{if(!controller.signal.aborted)setFailed(true);});
  return ()=>controller.abort();
 },[attempt]);
 return <section id="diagnostics" className="results-section research-diagnostics"><div className="section-heading"><div><span className="eyebrow">RESEARCH DIAGNOSTICS</span><h2>{en?'Trace the score back to each image.':'점수에서 표본까지 추적하기.'}</h2></div><p>{en?'Saved evidence · filter, inspect and export':'저장 근거 · 조건 선택 · 표본 확인 · 내보내기'}</p></div>
  <div className="diagnostic-switch" aria-label={en?'Diagnostic view':'진단 화면'}><button aria-pressed={tab==='cnn'} aria-controls="diagnostic-content" onClick={()=>setTab('cnn')}>{en?'CNN · class and error analysis':'CNN · 선종별 오류 분석'}</button><button aria-pressed={tab==='triage'} aria-controls="diagnostic-content" onClick={()=>setTab('triage')}>{en?'External run · discrepancy tracing':'외부 재현 · 불일치 추적'}</button></div>
  <div id="diagnostic-content">{failed?<div className="diagnostic-empty" role="alert"><p>{en?'The saved diagnostics could not be verified. No unverified statistics are shown.':'저장 진단 기록을 검증하지 못했습니다. 확인되지 않은 집계는 표시하지 않습니다.'}</p><button onClick={()=>{setFailed(false);setAttempt(a=>a+1);}}>{en?'Retry':'다시 불러오기'}</button></div>:!data?<p className="diagnostic-empty" role="status">{en?'Loading saved diagnostics…':'저장 진단 기록을 불러오는 중…'}</p>:tab==='cnn'?<MatchedExplorer data={data}/>:<TriageExplorer data={data}/>}</div>
 </section>;
}
