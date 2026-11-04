export const conditions = ['clean', 'pgd7', 'pgd50'] as const;
export const models = ['baseline', 'clean_only', 'pgd_mixed'] as const;
export const outcomes = ['all', 'changed', 'newly_correct', 'newly_incorrect', 'both_correct', 'both_wrong'] as const;
export type Condition = typeof conditions[number];
export type Model = typeof models[number];
export type Outcome = typeof outcomes[number];
export type Case = {relative_path:string;true_index:number;true_class:string;condition:Condition;outcome:Outcome} & Record<`${Model}_${'clean'|'condition'}_pred`,number>;
type Metric = {samples:number;correct:number;accuracy:number|null;clean_correct:number;own_clean_asr_successes:number|null;own_clean_asr_denominator:number|null;own_clean_asr:number|null};
export type Summary = {samples:number;models:Record<Model,Metric>;mixed_vs_clean_only:Record<'newly_correct'|'newly_incorrect'|'both_correct'|'both_wrong'|'net_correct',number>;common_clean_correct_asr:{samples:number;models:Record<'clean_only'|'pgd_mixed',{successes:number|null;asr:number|null}>}};
export type MatchedReport = {condition:Condition;overall:Summary;by_class:(Summary & {true_class:string})[];cases:Case[];source_sha256:Record<string,string>;evaluation_source_commit:string;settings:unknown;boundaries:unknown;notes:string[]};
export type Difference = {method:string;model:string;epsilon:string;file:string;pipeline:string;row_index:number;relative_path:string;reference:string;actual:string;true_index:string;outcome:string;reference_csv_sha256:string;actual_csv_sha256:string;evidence_path:string;evidence_sha256:string;source_commit:string};
export type Triage = {totals:{compared_prediction_cells:number;differing_prediction_cells:number;unique_affected_images:number};cases:Difference[];status_by_run:Record<string,string>;discrepancy_state:Record<string,string>;cause_status:string;source_evidence:{path:string;sha256:string;source_commit:string}[];registry_sha256:string;manifest_sha256:string;classes_sha256:string;condition_groups:Record<string,string|number>[];limitations:string[]};
export type Diagnostics = {schema:string;inference_performed:false;matched:Record<Condition,MatchedReport>;triage:Triage;generator_sha256:Record<string,string>};
export type TriageFilter = {method:string;model:string;pipeline:string;relative_path:string};

export function selectMatched(data:Diagnostics, condition:Condition, className:string, outcome:Outcome) {
 const report=data.matched[condition];
 const summary=className==='all'?report.overall:report.by_class.find(c=>c.true_class===className);
 if(!summary) throw Error('Unknown class');
 const population=report.cases.filter(c=>className==='all'||c.true_class===className);
 const cases=population.filter(c=>outcome==='all'||(outcome==='changed'?['newly_correct','newly_incorrect'].includes(c.outcome):c.outcome===outcome));
 return {summary,cases};
}

export function selectTriage(data:Diagnostics, filters:TriageFilter) {
 return data.triage.cases.filter(c=>(Object.keys(filters) as (keyof TriageFilter)[]).every(k=>filters[k]==='all'||c[k]===filters[k]));
}

export function csv(rows:Record<string,unknown>[], fields:string[]) {
 const cell=(v:unknown)=>'"'+String(v??'').replaceAll('"','""')+'"';
 return [fields.map(cell).join(','),...rows.map(r=>fields.map(k=>cell(r[k])).join(','))].join('\r\n')+'\r\n';
}
export const caseFields=['relative_path','true_index','true_class','condition','outcome',...models.flatMap(m=>[`${m}_clean_pred`,`${m}_condition_pred`])];
export const differenceFields=['method','model','epsilon','pipeline','relative_path','row_index','true_index','reference','actual','outcome','file','reference_csv_sha256','actual_csv_sha256','evidence_path','evidence_sha256','source_commit'];

export function matchedExport(data:Diagnostics, condition:Condition, className:string, outcome:Outcome) {
 const {summary,cases}=selectMatched(data,condition,className,outcome);
 const {source_sha256,evaluation_source_commit,settings,boundaries,notes}=data.matched[condition];
 return {schema:'maris-matched-selection/v1',inference_performed:false,selection:{condition,true_class:className,outcome,exported_cases:cases.length,metrics_scope:'Selected true class BEFORE outcome filtering'},summary,cases,source_sha256,evaluation_source_commit,settings,boundaries,notes,generator_sha256:data.generator_sha256};
}
export function triageExport(data:Diagnostics, filters:TriageFilter) {
 const cases=selectTriage(data,filters);
 return {schema:'maris-triage-selection/v1',inference_performed:false,...data.triage,cases,selection:{...filters,differing_prediction_cells:cases.length,unique_affected_images:new Set(cases.map(c=>c.relative_path)).size},generator_sha256:data.generator_sha256};
}

// Reconcile the public snapshot against its rows before showing any statistics.
// Canonical file/hash/lifecycle checks run in the Python exporter and CI.
export function validateDiagnostics(value:unknown):asserts value is Diagnostics {
 const d=value as Diagnostics;
 const fail=()=>{throw Error('Invalid research diagnostics')};
 if(!d||d.schema!=='maris-research-diagnostics/v1'||d.inference_performed!==false)fail();
 for(const condition of conditions) {
  const r=d.matched[condition];
  if(r.condition!==condition||r.cases.length!==r.overall.samples||new Set(r.cases.map(c=>c.relative_path)).size!==r.cases.length||r.by_class.length!==10)fail();
  for(const c of r.cases) {
   if(c.condition!==condition||!Number.isInteger(c.true_index)||c.true_index<0||c.true_index>9||r.by_class[c.true_index].true_class!==c.true_class)fail();
   for(const m of models) for(const kind of ['clean','condition'] as const) if(!Number.isInteger(c[`${m}_${kind}_pred`])||c[`${m}_${kind}_pred`]<0||c[`${m}_${kind}_pred`]>9)fail();
   const b=c.clean_only_condition_pred===c.true_index, p=c.pgd_mixed_condition_pred===c.true_index;
   if(c.outcome!==(b&&p?'both_correct':!b&&!p?'both_wrong':p?'newly_correct':'newly_incorrect'))fail();
  }
  const groups=[{summary:r.overall,rows:r.cases},...r.by_class.map(s=>({summary:s,rows:r.cases.filter(c=>c.true_class===s.true_class)}))];
  if(new Set(r.by_class.map(c=>c.true_class)).size!==10||r.by_class.reduce((n,s)=>n+s.samples,0)!==r.overall.samples)fail();
  for(const {summary:s,rows} of groups) {
   if(rows.length!==s.samples)fail();
   for(const m of models) {
    const metric=s.models[m], clean=rows.filter(c=>c[`${m}_clean_pred`]===c.true_index).length;
    const correct=rows.filter(c=>c[`${m}_condition_pred`]===c.true_index).length;
    const lost=condition==='clean'?null:rows.filter(c=>c[`${m}_clean_pred`]===c.true_index&&c[`${m}_condition_pred`]!==c.true_index).length;
    if(metric.samples!==rows.length||metric.correct!==correct||metric.clean_correct!==clean||metric.accuracy!==(rows.length?correct/rows.length:null)||metric.own_clean_asr_successes!==lost||metric.own_clean_asr_denominator!==(condition==='clean'?null:clean)||metric.own_clean_asr!==(lost!==null&&clean?lost/clean:null))fail();
   }
   const paired=s.mixed_vs_clean_only;
   for(const o of ['newly_correct','newly_incorrect','both_correct','both_wrong'] as const)if(paired[o]!==rows.filter(c=>c.outcome===o).length)fail();
   if(paired.net_correct!==paired.newly_correct-paired.newly_incorrect)fail();
   const common=rows.filter(c=>c.clean_only_clean_pred===c.true_index&&c.pgd_mixed_clean_pred===c.true_index);
   if(s.common_clean_correct_asr.samples!==common.length)fail();
   for(const m of ['clean_only','pgd_mixed'] as const) {
    const metric=s.common_clean_correct_asr.models[m],lost=condition==='clean'?null:common.filter(c=>c[`${m}_condition_pred`]!==c.true_index).length;
    if(metric.successes!==lost||metric.asr!==(lost!==null&&common.length?lost/common.length:null))fail();
   }
  }
 }
 const t=d.triage;
 if(t.totals.differing_prediction_cells!==t.cases.length||t.totals.unique_affected_images!==new Set(t.cases.map(c=>c.relative_path)).size||t.totals.compared_prediction_cells!==t.condition_groups.reduce((s,g)=>s+Number(g.compared_prediction_cells),0))fail();
 for(const g of t.condition_groups)if(Number(g.differing_prediction_cells)!==t.cases.filter(c=>['method','model','epsilon','pipeline'].every(k=>c[k as keyof Difference]===g[k])).length)fail();
}
