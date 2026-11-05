/* eslint-disable @typescript-eslint/no-require-imports -- This Node CJS harness loads transpiled TSX for SSR checks. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),ts=require('typescript'),Module=require('node:module');
const root=path.resolve(__dirname,'..'),resolve=Module._resolveFilename;
Module._resolveFilename=function(request,parent,...rest){return resolve.call(this,request.startsWith('@/')?path.join(root,request.slice(2)):request,parent,...rest);};
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(module,file)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true,target:ts.ScriptTarget.ES2022}}).outputText,file);
const React=require('react'),{renderToStaticMarkup}=require('react-dom/server'),locale=require('../app/locale-provider.tsx');
const api=require('../lib/research-diagnostics.ts'),{MatchedExplorer,TriageExplorer}=require('../app/research-diagnostics.tsx');
const data=JSON.parse(fs.readFileSync(path.join(root,'public/evidence/research-diagnostics.json')));
api.validateDiagnostics(data);
assert.equal(data.triage.cause_status,'UNRESOLVED');
assert.equal(data.triage.status_by_run['external-01'],'FAIL');
assert.equal(data.triage.status_by_run['pc-full-20260928'],'LOCAL_PASS');
assert.equal(data.triage.discrepancy_state['cross-environment-01'],'open');
assert.deepEqual(data.triage.totals,{compared_prediction_cells:62480,differing_prediction_cells:16,unique_affected_images:14});
const original=JSON.stringify(data),state=React.useState,oldLocale=locale.useLocale;
const setState=values=>{let index=0;React.useState=()=>[values[index++],()=>{}];};
let renders=0,selections=0;
try {
 for(const condition of api.conditions) for(const cls of ['all',...data.matched[condition].by_class.map(c=>c.true_class)]) {
  const unfiltered=api.selectMatched(data,condition,cls,'all');
  for(const outcome of api.outcomes) {
   const selected=api.selectMatched(data,condition,cls,outcome);
   assert.strictEqual(selected.summary,unfiltered.summary,'Outcome filter changed the metric cohort');
   assert.equal(selected.summary.samples,unfiltered.cases.length);
   assert.ok(selected.cases.every(c=>cls==='all'||c.true_class===cls));
   const exported=api.matchedExport(data,condition,cls,outcome);
   assert.deepEqual(exported.cases,selected.cases);assert.deepEqual(exported.source_sha256,data.matched[condition].source_sha256);
   assert.equal(api.csv(selected.cases,api.caseFields).trim().split('\r\n').length,selected.cases.length+1);
   for(const language of ['ko','en']) {
    setState([condition,cls,outcome,0]);locale.useLocale=()=>({locale:language});
    const html=renderToStaticMarkup(React.createElement(MatchedExplorer,{data}));
    assert.ok(!/NaN|undefined/.test(html));
    assert.ok(html.includes('id="diag-denominator"'));assert.ok(html.includes('aria-describedby="diag-denominator"'));
    if(language==='en')assert.ok(!/[가-힣]/.test(html));
    if(selected.cases.length===0)assert.ok(html.includes('diagnostic-empty'));
    assert.ok(html.includes(`${selected.summary.models.clean_only.correct} / ${selected.summary.samples}`));
    renders++;
   }
   selections++;
  }
 }
 const all=api.selectMatched(data,'pgd50','all','changed');
 assert.equal(all.summary.samples,781);assert.equal(all.cases.length,49);
 assert.equal(all.summary.mixed_vs_clean_only.newly_correct,28);assert.equal(all.summary.mixed_vs_clean_only.newly_incorrect,21);
 assert.equal(all.summary.common_clean_correct_asr.samples,518);
 const container=api.selectMatched(data,'pgd50','Container Ship','newly_incorrect');
 assert.equal(container.summary.samples,86);assert.equal(container.cases.length,6);assert.equal(container.summary.mixed_vs_clean_only.net_correct,-4);
 const tug=api.selectMatched(data,'pgd50','Tug','changed');assert.equal(tug.summary.samples,68);assert.equal(tug.cases.length,0);
 assert.equal(api.csv(tug.cases,api.caseFields).split('\r\n').length,2,'Empty exports retain their CSV header');
 assert.throws(()=>api.selectMatched(data,'pgd50','nonexistent','all'));
 for(const method of ['all','gaussian','mean']) for(const model of ['all','cnn','mobilenet']) for(const pipeline of ['all','clean','defended_clean','attacked','transfer_defended','adaptive_defended']) for(const relative_path of ['all',...new Set(data.triage.cases.map(c=>c.relative_path))]) {
  const filters={method,model,pipeline,relative_path},cases=api.selectTriage(data,filters),exported=api.triageExport(data,filters);
  assert.deepEqual(exported.totals,data.triage.totals);assert.deepEqual(exported.condition_groups,data.triage.condition_groups);
  assert.equal(exported.selection.differing_prediction_cells,cases.length);
  assert.equal(exported.selection.unique_affected_images,new Set(cases.map(c=>c.relative_path)).size);
  if(model==='cnn')assert.equal(cases.length,0);
  selections++;
 }
 for(const language of ['ko','en']) for(const values of [
  ['all','all','all','all',0],['all','cnn','all','all',0],['gaussian','mobilenet','attacked','all',0],['mean','mobilenet','adaptive_defended','all',0],['all','all','all','all',1]
 ]) {
  setState(values);locale.useLocale=()=>({locale:language});
  const html=renderToStaticMarkup(React.createElement(TriageExplorer,{data}));
  assert.ok(html.includes('62,480'));assert.ok(html.includes('UNRESOLVED'));assert.ok(html.includes('FAIL'));assert.ok(html.includes('LOCAL_PASS'));
  assert.ok(!/NaN|undefined/.test(html));if(language==='en')assert.ok(!/[가-힣]/.test(html));
  if(values[1]==='cnn')assert.ok(html.includes('diagnostic-empty'));
  renders++;
 }
} finally {React.useState=state;locale.useLocale=oldLocale;}
assert.equal(JSON.stringify(data),original,'Selection/export/render mutated evidence');
for(const mutate of [
 d=>d.matched.pgd50.overall.samples++,d=>d.matched.pgd50.cases[0].outcome='newly_correct',
 d=>d.matched.pgd50.by_class[0].models.clean_only.correct++,d=>d.matched.clean.overall.models.baseline.own_clean_asr=0,
 d=>d.matched.pgd50.overall.common_clean_correct_asr.samples++,d=>d.triage.totals.differing_prediction_cells++,
 d=>d.triage.condition_groups[0].differing_prediction_cells++,d=>d.matched.pgd50.cases[0].true_class='Tug'
]){const fixture=structuredClone(data);mutate(fixture);assert.throws(()=>api.validateDiagnostics(fixture));}
assert.equal(api.csv([{value:'a,"b"\nc'}],['value']),'"value"\r\n"a,""b""\nc"\r\n');
const page=fs.readFileSync(path.join(root,'app/page.tsx'),'utf8');
assert.ok(page.includes('href="#diagnostics"'));assert.ok(page.includes('<ResearchDiagnostics />'));
console.log(`PASS: ${selections} filter/export combinations, ${renders} Korean/English renders, 8 rejected snapshot mutations, preserved denominators and status verdicts, empty CSV headers and pagination. No model inference.`);
