/** Browser-side reconciliation of a Python FGSM audit report, never raw-data auditing. */
export const auditModels = ['cnn', 'mobilenet'] as const;
export type AuditModel = typeof auditModels[number];
export type AuditCondition = {model:AuditModel;epsilon:number};
export type SavedCondition = AuditCondition & {rows:number;file:string;sha256:string};
export type Invocation = {model:AuditModel;directory:string;provenance:string;journal_status:string|null;completion_record_consistent:boolean;run_id?:string;validated_recorded_epsilons?:number[];unrecorded_saved_epsilons?:number[]};
export type AuditReport = {
 kind:'fgsm_saved_output_audit';result:string;saved_sample_coverage:string;
 expected_conditions:number;checked_conditions:number;conditions:SavedCondition[];
 missing_conditions:AuditCondition[];rerun_conditions:(AuditCondition & {reason:string})[];
 execution_errors:{model:AuditModel;directory:string;run_id:string;error:string|null}[];
 resume_requires_error_resolution:boolean;invocations:Invocation[];
 resume_plan:{model:AuditModel;epsilons:number[];output_requirement:string}[];
 independent_verification_approval:false;probabilities_compared:false;process_liveness:'NOT_CHECKED';limitations:string[];
};
export type AuditSnapshot = {schema:'maris-fgsm-audit/v1';inference_performed:false;evidence_source_commit:string;source_sha256:Record<string,string>;report:AuditReport};
const FULL='FULL_REQUESTED_SAVED_SAMPLE_COVERAGE', PARTIAL='PARTIAL_SAVED_SAMPLE_COVERAGE';
const states=['PREPARING','RUNNING','INTERRUPTED','ERROR','COMPLETED_REQUESTED_SCOPE'];
const provenances=['LEGACY_EXECUTION_PROVENANCE_UNVERIFIED','RECORDED_JOURNAL_INPUTS_AND_ARTIFACTS_VALIDATED','JOURNAL_WITHOUT_COMPLETED_CONDITIONS','RECORDED_ERROR_ARTIFACTS_ONLY','JOURNAL_WITH_UNRECORDED_SAVED_CONDITIONS'];
const key=(c:AuditCondition)=>`${c.model}:${c.epsilon}`;
const validEpsilon=(v:unknown):v is number=>typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=1;
const sameSet=(a:string[],b:string[])=>a.length===b.length&&new Set(a).size===a.length&&new Set(b).size===b.length&&a.every(v=>b.includes(v));
const fail=():never=>{throw Error('Invalid or inconsistent FGSM audit report');};
function requireThat(v:unknown):asserts v {if(!v)fail();}
function record(v:unknown):Record<string,unknown> {requireThat(v&&typeof v==='object'&&!Array.isArray(v));return v as Record<string,unknown>;}
function items(v:unknown):unknown[] {requireThat(Array.isArray(v)&&v.length<=512);return v;}
function text(v:unknown):asserts v is string {requireThat(typeof v==='string'&&v.length<=16384);}
function condition(v:unknown):asserts v is AuditCondition {const c=record(v);requireThat(auditModels.includes(c.model as AuditModel)&&validEpsilon(c.epsilon));}
function epsilonList(v:unknown):asserts v is number[] {const a=items(v);requireThat(a.every(validEpsilon)&&new Set(a.map(n=>Number((n as number).toPrecision(6)))).size===a.length);}

/** Reject duplicate JSON keys (including escaped spellings) before reconciling fields. */
export function parseAuditJson(input:string):unknown {
 requireThat(input.length<=2*1024*1024);
 const source=input.replace(/^\uFEFF/,'');
 const value:unknown=JSON.parse(source);
 const tokens=source.match(/"(?:\\[\s\S]|[^"\\])*"|[{}\[\]:,]|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null/g)||[];
 let i=0;
 const walk=(depth:number)=>{
  requireThat(depth<40);
  if(tokens[i]==='{') {
   i++;const names=new Set<string>();
   while(tokens[i]!=='}') {const name=JSON.parse(tokens[i++]);requireThat(!names.has(name));names.add(name);i++;walk(depth+1);if(tokens[i]!==',')break;i++;}
   requireThat(tokens[i++]==='}');
  } else if(tokens[i]==='[') {i++;while(tokens[i]!==']') {walk(depth+1);if(tokens[i]!==',')break;i++;}requireThat(tokens[i++]===']');}
  else {const t=JSON.parse(tokens[i++]);requireThat(typeof t!=='number'||Number.isFinite(t));}
 };
 walk(0);requireThat(i===tokens.length);return value;
}

export function validateAuditReport(value:unknown):asserts value is AuditReport {
 const d=record(value);
 requireThat(d.kind==='fgsm_saved_output_audit'&&d.independent_verification_approval===false&&d.probabilities_compared===false&&d.process_liveness==='NOT_CHECKED');
 const saved=items(d.conditions),missing=items(d.missing_conditions),rerun=items(d.rerun_conditions);
 const invocations=items(d.invocations),errors=items(d.execution_errors),plans=items(d.resume_plan);
 requireThat(Number.isInteger(d.expected_conditions)&&Number(d.expected_conditions)>0&&d.expected_conditions===saved.length+missing.length&&d.checked_conditions===saved.length);
 [...saved,...missing,...rerun].forEach(condition);
 const s=saved as SavedCondition[], m=missing as AuditCondition[], r=rerun as (AuditCondition & {reason:string})[];
 const scope=[...s,...m];requireThat(new Set(scope.map(key)).size===scope.length);
 const selected=auditModels.filter(model=>scope.some(c=>c.model===model));
 const eps=scope.filter(c=>c.model===selected[0]).map(c=>String(c.epsilon));
 epsilonList(eps.map(Number));
 for(const model of selected)requireThat(sameSet(eps,scope.filter(c=>c.model===model).map(c=>String(c.epsilon))));
 for(const c of s) {requireThat(c.rows===781&&/^[a-f0-9]{64}$/.test(c.sha256));text(c.file);requireThat(c.file.length>0);}
 requireThat(new Set(r.map(key)).size===r.length);
 for(const c of r) requireThat(s.some(v=>key(v)===key(c))&&['RECORDED_EXECUTION_ERROR','SAVED_CONDITION_NOT_IN_JOURNAL'].includes(c.reason));
 const inv=invocations as Invocation[];
 const identity=(v:{model:AuditModel;directory:string})=>`${v.model}:${v.directory}`;
 requireThat(new Set(inv.map(v=>identity(v))).size===inv.length);
 for(const v of inv) {
  record(v);requireThat(selected.includes(v.model)&&provenances.includes(v.provenance)&&typeof v.completion_record_consistent==='boolean');text(v.directory);
  requireThat(v.journal_status===null||states.includes(v.journal_status));
  const local=s.filter(c=>c.model===v.model&&c.file.replace(/\\/g,'/').slice(0,c.file.replace(/\\/g,'/').lastIndexOf('/'))===v.directory.replace(/\\/g,'/'));
  if(v.journal_status===null)requireThat(v.provenance==='LEGACY_EXECUTION_PROVENANCE_UNVERIFIED'&&!v.completion_record_consistent&&!local.some(c=>r.some(x=>key(x)===key(c))));
  else {
   text(v.run_id);requireThat(v.run_id.length>0);epsilonList(v.validated_recorded_epsilons);epsilonList(v.unrecorded_saved_epsilons);
   requireThat(sameSet(local.filter(c=>!v.validated_recorded_epsilons!.includes(c.epsilon)).map(c=>String(c.epsilon)),v.unrecorded_saved_epsilons.map(String)));
   if(v.journal_status==='ERROR')requireThat(v.provenance==='RECORDED_ERROR_ARTIFACTS_ONLY');
   else if(v.unrecorded_saved_epsilons.length)requireThat(v.provenance==='JOURNAL_WITH_UNRECORDED_SAVED_CONDITIONS');
   else requireThat(v.provenance===(v.validated_recorded_epsilons.length?'RECORDED_JOURNAL_INPUTS_AND_ARTIFACTS_VALIDATED':'JOURNAL_WITHOUT_COMPLETED_CONDITIONS'));
   for(const c of local) {
    const reason=v.journal_status==='ERROR'?'RECORDED_EXECUTION_ERROR':v.unrecorded_saved_epsilons.includes(c.epsilon)?'SAVED_CONDITION_NOT_IN_JOURNAL':null;
    requireThat(reason?r.some(x=>key(x)===key(c)&&x.reason===reason):!r.some(x=>key(x)===key(c)));
   }
  }
  requireThat(v.completion_record_consistent===(v.journal_status==='COMPLETED_REQUESTED_SCOPE'));
 }
 // A saved file must belong to exactly one declared invocation, never a guessed run.
 for(const c of s)requireThat(inv.filter(v=>v.model===c.model&&c.file.replace(/\\/g,'/').slice(0,c.file.replace(/\\/g,'/').lastIndexOf('/'))===v.directory.replace(/\\/g,'/')).length===1);
 const e=errors as AuditReport['execution_errors'];
 for(const x of e) {record(x);text(x.directory);text(x.run_id);requireThat(x.error===null||typeof x.error==='string');requireThat(inv.some(v=>identity(v)===identity(x)&&v.journal_status==='ERROR'&&v.run_id===x.run_id));}
 requireThat(sameSet(e.map(identity),inv.filter(v=>v.journal_status==='ERROR').map(identity)));
 const coverage=m.length?PARTIAL:FULL;
 requireThat(d.saved_sample_coverage===coverage&&d.resume_requires_error_resolution===(e.length>0));
 requireThat(d.result===(e.length?'RECORDED_EXECUTION_ERROR':r.length?'SAVED_CONDITIONS_REQUIRE_RERUN':coverage));
 const restart=[...m,...r];
 const planned:string[]=[];
 for(const raw of plans) {const p=record(raw);requireThat(selected.includes(p.model as AuditModel)&&p.output_requirement==='NEW_DIRECTORY_OUTSIDE_ALL_PRIOR_OUTPUTS');epsilonList(p.epsilons);requireThat(p.epsilons.length>0);planned.push(...p.epsilons.map(epsilon=>key({model:p.model as AuditModel,epsilon})));}
 requireThat(new Set(plans.map(p=>record(p).model)).size===plans.length&&sameSet(planned,restart.map(key)));
 for(const l of items(d.limitations))text(l);
}

export function validateAuditSnapshot(value:unknown):asserts value is AuditSnapshot {
 const d=record(value);requireThat(d.schema==='maris-fgsm-audit/v1'&&d.inference_performed===false&&typeof d.evidence_source_commit==='string'&&/^[a-f0-9]{40}$/.test(d.evidence_source_commit));
 const hashes=record(d.source_sha256);requireThat(Object.keys(hashes).length>=3&&Object.values(hashes).every(h=>typeof h==='string'&&/^[a-f0-9]{64}$/.test(h)));validateAuditReport(d.report);
}

export function restartCommands(report:AuditReport):string|null {
 validateAuditReport(report);
 if(report.execution_errors.length||!report.resume_plan.length)return null;
 return report.resume_plan.map(p=>`python -m adversarial_ai.evaluation.evaluate_fgsm_${p.model} --epsilons ${p.epsilons.join(' ')} --output "REPLACE_WITH_NEW_DIRECTORY/${p.model}"`).join('\n');
}

export function planExport(report:AuditReport) {
 validateAuditReport(report);
 return {schema:'maris-fgsm-restart-plan/v1',inference_performed:false,independent_verification_approval:false,process_liveness:'NOT_CHECKED',result:report.result,execution_errors:report.execution_errors,missing_conditions:report.missing_conditions,rerun_conditions:report.rerun_conditions,resume_plan:report.resume_plan,commands:restartCommands(report),instructions:'Resolve recorded errors before rerunning. Replace each output path with a new empty directory outside all previous outputs. This report does not start a process.'};
}
