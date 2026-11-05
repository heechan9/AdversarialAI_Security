"use client";
import {useEffect, useRef, useState, type ChangeEvent} from 'react';
import {useLocale} from './locale-provider';
import {auditModels, parseAuditJson, planExport, restartCommands, validateAuditReport, validateAuditSnapshot, type AuditReport, type AuditSnapshot} from '@/lib/fgsm-audit';

const repo='https://github.com/heechan9/AdversarialAI_Security';
const guide=`${repo}/blob/main/docs/FGSM_INTERRUPTED_RUNS.md`;
function download(name:string,content:string) {
 const url=URL.createObjectURL(new Blob([content],{type:name.endsWith('.json')?'application/json;charset=utf-8':'text/plain;charset=utf-8'}));
 const link=document.createElement('a');link.href=url;link.download=name;document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export function AuditSummary({report,local}:{report:AuditReport;local:boolean}) {
 const {locale}=useLocale(),en=locale==='en';
 const [model,setModel]=useState('all');
 const labels:Record<string,string>=en?{
  FULL_REQUESTED_SAVED_SAMPLE_COVERAGE:'Saved rows cover the requested scope',PARTIAL_SAVED_SAMPLE_COVERAGE:'Some requested conditions are missing',SAVED_CONDITIONS_REQUIRE_RERUN:'Some saved conditions need a rerun',RECORDED_EXECUTION_ERROR:'Resolve the recorded error first',
  PREPARING:'Preparing',RUNNING:'Recorded as running · liveness unknown',INTERRUPTED:'Interrupted',ERROR:'Error',COMPLETED_REQUESTED_SCOPE:'Requested scope recorded complete',
 }:{FULL_REQUESTED_SAVED_SAMPLE_COVERAGE:'요청한 조건의 저장 행이 모두 있음',PARTIAL_SAVED_SAMPLE_COVERAGE:'요청한 조건 중 일부가 빠져 있음',SAVED_CONDITIONS_REQUIRE_RERUN:'저장돼 있지만 다시 실행할 조건이 있음',RECORDED_EXECUTION_ERROR:'기록된 오류부터 해결해야 함',
  PREPARING:'준비 중',RUNNING:'실행 중으로 기록됨 · 현재 동작 여부는 알 수 없음',INTERRUPTED:'중단됨',ERROR:'오류',COMPLETED_REQUESTED_SCOPE:'요청한 범위 완료로 기록됨'};
 const rows=[...report.conditions,...report.missing_conditions].filter(c=>model==='all'||c.model===model).sort((a,b)=>auditModels.indexOf(a.model)-auditModels.indexOf(b.model)||a.epsilon-b.epsilon);
 const commands=restartCommands(report);
 const need=report.missing_conditions.length+report.rerun_conditions.length;
 return <div className="run-review-body">
  <div className={'run-verdict'+(report.execution_errors.length?' run-verdict-error':'')} role="status"><span>{local?(en?'LOCAL REPORT · CONTENT RECONCILED':'로컬 보고서 · 내용 검산'):(en?'PUBLIC SAVED EVIDENCE':'공개 저장 근거')}</span><h3>{labels[report.result]}</h3><p>{en?'Counts describe this report’s requested scope. Uploaded reports are self-reported; the browser does not reopen their CSVs or authenticate execution.':'집계는 이 보고서가 요청한 범위 기준입니다. 불러온 보고서는 파일의 선언을 보여주며, 브라우저에서 원본 CSV를 다시 검사하거나 실행 사실을 인증하지 않습니다.'}</p></div>
  <div className="diagnostic-metrics run-metrics"><div><span>{en?'Saved conditions':'저장된 조건'}</span><strong>{report.checked_conditions} / {report.expected_conditions}</strong></div><div><span>{en?'Missing conditions':'빠진 조건'}</span><strong>{report.missing_conditions.length}</strong></div><div><span>{en?'Saved but needs rerun':'저장됐지만 재실행 필요'}</span><strong>{report.rerun_conditions.length}</strong></div><div><span>{en?'Invocations with errors':'오류가 기록된 실행'}</span><strong>{report.execution_errors.length}</strong></div></div>
  <div className="run-table-heading"><h3>{en?'Conditions in this report':'이 보고서의 조건'}</h3><label>{en?'Model':'모델'} <select aria-label={en?'Model':'모델'} value={model} onChange={e=>setModel(e.target.value)}><option value="all">{en?'All':'전체'}</option>{auditModels.filter(m=>[...report.conditions,...report.missing_conditions].some(c=>c.model===m)).map(m=><option key={m} value={m}>{m==='cnn'?'CNN':'MobileNetV2'}</option>)}</select></label></div>
  <p className="run-help">{en?'The model filter changes the table only. Counts and downloads retain the full report scope.':'모델 선택은 아래 표만 바꿉니다. 집계와 다운로드는 보고서 전체 범위를 유지합니다.'}</p>
  <div className="diagnostic-table"><table><caption>{en?'Saved rows and rerun requirements are separate.':'저장 행의 존재와 재실행 필요 여부를 나누어 표시합니다.'}</caption><thead><tr><th scope="col">{en?'Model / ε':'모델 / ε'}</th><th scope="col">{en?'Saved rows':'저장 행'}</th><th scope="col">{en?'Next step':'다음 조치'}</th><th scope="col">{en?'CSV hash in report':'보고서에 기록된 CSV 해시'}</th></tr></thead><tbody>{rows.map(c=>{
   const saved=report.conditions.find(s=>s.model===c.model&&s.epsilon===c.epsilon),rerun=report.rerun_conditions.find(s=>s.model===c.model&&s.epsilon===c.epsilon);
   const action=!saved?(en?'Run in a new directory':'새 폴더에서 실행'):rerun?.reason==='RECORDED_EXECUTION_ERROR'?(en?'Resolve error, then rerun':'오류 해결 후 재실행'):rerun?(en?'Unjournaled · rerun':'완료 기록 없음 · 재실행'):(en?'No rerun listed':'재실행 목록에 없음');
   return <tr key={`${c.model}:${c.epsilon}`}><th scope="row">{c.model==='cnn'?'CNN':'MobileNetV2'} / {c.epsilon}</th><td>{saved?`${saved.rows} / 781`:(en?'Missing':'없음')}</td><td>{action}</td><td>{saved?<details><summary>SHA-256</summary><code>{saved.sha256}</code></details>:'—'}</td></tr>;
  })}</tbody></table></div>
  <details className="diagnostic-details"><summary>{en?'Invocation records and completion scope':'실행별 기록과 완료 범위'}</summary><p>{en?'A saved RUNNING journal is not a process monitor. Legacy records have no authenticated lineage through this journal mechanism.':'저장된 RUNNING 기록은 현재 프로세스가 살아 있다는 뜻이 아닙니다. 과거 기록은 이 새 기록 체계로 실행 이력이 인증되지 않습니다.'}</p>{report.invocations.length?<ul className="run-invocations">{report.invocations.map((v,i)=><li key={i}><strong>{v.model==='cnn'?'CNN':'MobileNetV2'} · {v.journal_status?labels[v.journal_status]:(en?'Legacy saved output · execution provenance unverified':'과거 저장 결과 · 실행 이력 미인증')}</strong><code>{v.directory}</code><span>{v.completion_record_consistent?(en?'Completion record consistent within its requested scope':'해당 실행이 요청한 범위에서 완료 기록 일치'):(en?'No consistent completion record asserted':'일치하는 완료 기록으로 선언되지 않음')}</span></li>)}</ul>:<p>{en?'No saved invocation found.':'저장된 실행 기록이 없습니다.'}</p>}</details>
  <div className="run-plan"><h3>{en?'Fresh-directory restart plan':'새 폴더에서 이어갈 계획'}</h3><p>{report.execution_errors.length?(en?'Investigate and resolve recorded errors before restarting. Command templates are withheld until a new audit report has no recorded error.':'기록된 오류를 조사하고 해결한 뒤 다시 검사하세요. 오류가 없는 새 검사 보고서를 불러오기 전까지 실행 명령은 만들지 않습니다.'):need?(en?'Run whole conditions in a new empty directory outside every previous output. Replace the template path before use.':'이전 결과 폴더 밖의 새 빈 폴더에서 조건 전체를 실행하세요. 명령의 경로를 새 폴더로 바꾼 뒤 사용하세요.'):(en?'This report lists no conditions to restart. This does not grant independent approval.':'이 보고서에는 다시 실행할 조건이 없습니다. 독립 검증 승인을 뜻하지 않습니다.')}</p>
   {report.execution_errors.length>0&&<ul>{report.execution_errors.map((e,i)=><li key={i}><strong>{e.model} · {en?'Recorded error':'기록된 오류'}</strong><pre>{e.error||(en?'No error message recorded':'오류 메시지 없음')}</pre></li>)}</ul>}
   {report.resume_plan.length>0&&<ul>{report.resume_plan.map(p=><li key={p.model}>{p.model==='cnn'?'CNN':'MobileNetV2'} · ε {p.epsilons.join(' / ')}</li>)}</ul>}
   {commands&&<pre className="run-command" tabIndex={0} aria-label={en?'Restart command templates':'재실행 명령 예시'}>{commands}</pre>}
   <div className="diagnostic-downloads"><button onClick={()=>download('paulguard-fgsm-audit.json',JSON.stringify(report,null,2))}>{en?'Audit report · JSON':'검사 보고서 · JSON'}</button><button onClick={()=>download('paulguard-fgsm-restart-plan.json',JSON.stringify(planExport(report),null,2))}>{en?'Restart plan · JSON':'재실행 계획 · JSON'}</button><button disabled={!commands} onClick={()=>commands&&download('paulguard-fgsm-restart-commands.txt',commands+'\n')}>{en?'Command templates · TXT':'명령 예시 · TXT'}</button></div>
  </div>
 </div>;
}

export default function FgsmRunReview() {
 const {locale}=useLocale(),en=locale==='en';
 const [snapshot,setSnapshot]=useState<AuditSnapshot|null>(null),[publicError,setPublicError]=useState(false),[attempt,setAttempt]=useState(0);
 const [mode,setMode]=useState<'public'|'local'>('public'),[local,setLocal]=useState<AuditReport|null>(null),[fileName,setFileName]=useState(''),[fileError,setFileError]=useState(false),[reading,setReading]=useState(false),[fileVersion,setFileVersion]=useState(0);
 const request=useRef(0);
 useEffect(()=>{const controller=new AbortController();fetch('/evidence/fgsm-run-audit.json',{signal:controller.signal}).then(r=>{if(!r.ok)throw Error();return r.text();}).then(text=>{const d=parseAuditJson(text);validateAuditSnapshot(d);setSnapshot(d);}).catch(()=>{if(!controller.signal.aborted)setPublicError(true);});return()=>controller.abort();},[attempt]);
 useEffect(()=>()=>{request.current++;},[]);
 const importFile=async(e:ChangeEvent<HTMLInputElement>)=>{
  const file=e.target.files?.[0];e.target.value='';if(!file)return;
  const id=++request.current;setFileVersion(n=>n+1);setMode('local');setLocal(null);setFileName(file.name.slice(0,200));setFileError(false);setReading(true);
  try {if(file.size>2*1024*1024)throw Error();const d=parseAuditJson(await file.text());validateAuditReport(d);if(request.current===id)setLocal(d);}
  catch {if(request.current===id)setFileError(true);}finally{if(request.current===id)setReading(false);}
 };
 const report=mode==='local'?local:snapshot?.report;
 return <section id="run-review" className="results-section fgsm-run-review" aria-labelledby="run-review-title"><div className="section-heading"><div><span className="eyebrow">RUN RECORDS / SAFE RESTART</span><h2 id="run-review-title">{en?'Check what was saved. Plan what comes next.':'남은 결과를 확인하고, 빠진 조건을 이어가세요.'}</h2></div><p>{en?'Read a saved audit report. No model starts here.':'저장된 검사 보고서를 읽습니다. 여기서 모델을 실행하지 않습니다.'}</p></div>
  <div className="run-source-controls"><button aria-pressed={mode==='public'} onClick={()=>{request.current++;setReading(false);setMode('public');setLocal(null);setFileName('');setFileError(false);}}>{en?'Public saved results':'공개 저장 결과'}</button><label className="run-file-label">{en?'Open audit JSON':'검사 JSON 불러오기'}<input type="file" accept=".json,application/json" onChange={importFile} aria-describedby="run-file-help"/></label><span>{mode==='local'?fileName:(en?'Public snapshot':'공개 저장본')}</span></div>
  <p className="run-help" id="run-file-help">{en?'Files stay in this browser tab and are not sent to a server. Maximum 2 MB. CSV and journal checks are performed by the Python auditor; the browser reconciles the report’s conditions, errors and restart plan.':'파일은 이 브라우저 탭에서만 읽으며 서버로 전송하지 않습니다. 최대 2 MB입니다. CSV·실행 기록 검사는 Python 검사기가 수행하고, 웹은 보고서의 조건·오류·재실행 계획을 검산합니다.'}</p>
  {mode==='local'&&reading?<p role="status">{en?'Reading report…':'보고서를 읽는 중…'}</p>:mode==='local'&&fileError?<div role="alert" className="run-file-error">{en?'Cannot display this file. Use a valid FGSM audit JSON up to 2 MB; its counts, error status and restart plan must agree. No previous result is being substituted.':'이 파일을 표시할 수 없습니다. 2 MB 이하 FGSM 검사 JSON인지, 집계·오류 상태·재실행 계획이 일치하는지 확인하세요. 이전 결과로 대신 표시하지 않습니다.'}</div>:mode==='public'&&publicError?<div role="alert" className="run-file-error">{en?'Public report could not be loaded.':'공개 보고서를 불러오지 못했습니다.'}<button onClick={()=>{setPublicError(false);setAttempt(n=>n+1);}}>{en?'Retry':'다시 불러오기'}</button></div>:report?<AuditSummary key={mode+fileVersion+attempt} report={report} local={mode==='local'}/>:<p role="status">{en?'Loading saved report…':'저장 보고서를 불러오는 중…'}</p>}
  <details className="diagnostic-details"><summary>{en?'Create a report from your stopped run':'중단된 실행에서 검사 보고서 만들기'}</summary><p>{en?'Run this command in a matching source checkout. Replace the quoted directory with the old output folder. Partial coverage exits 2 and recorded errors exit 3, while still writing the report. Resolve malformed or corrupted files first if no JSON is produced.':'같은 소스의 작업 폴더에서 아래 명령을 실행하세요. 따옴표 안의 경로를 기존 결과 폴더로 바꾸세요. 일부 조건이 빠지면 종료 코드 2, 기록된 오류가 있으면 3이지만 보고서는 저장됩니다. JSON이 만들어지지 않으면 손상된 파일 등 검사 오류부터 해결하세요.'}</p><pre className="run-command" tabIndex={0}>python verification/fgsm_run_audit.py &quot;PATH_TO_SAVED_OUTPUT&quot; &gt; fgsm-audit.json</pre><p>{en?'Then open fgsm-audit.json above. Only the requested models and epsilons are covered. Saved files, journal completeness and independent review remain separate.':'생성된 fgsm-audit.json을 위에서 불러오세요. 요청한 모델과 ε만 검사 범위에 포함됩니다. 저장 파일의 존재, 실행 기록의 완료, 독립 검증 승인은 각각 별개입니다.'}</p><a href={guide} target="_blank" rel="noreferrer">{en?'Full interruption and restart guide ↗':'중단·재실행 안내 전체 보기 ↗'}</a></details>
  {mode==='public'&&snapshot&&<p className="run-help">{en?'Public evidence snapshot source:':'공개 근거 저장본 기준:'} <a href={`${repo}/tree/${snapshot.evidence_source_commit}`} target="_blank" rel="noreferrer">{snapshot.evidence_source_commit.slice(0,7)} ↗</a> · {en?'No new inference or independent approval.':'새 추론이나 독립 검증 승인이 아닙니다.'}</p>}
 </section>;
}
