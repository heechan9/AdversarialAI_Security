const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), ts = require('typescript');
const root = path.resolve(__dirname, '..');
for (const ext of ['.ts', '.tsx']) require.extensions[ext] = (module, file) => module._compile(ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true, target: ts.ScriptTarget.ES2022 } }).outputText, file);
require.extensions['.css'] = () => {};
const React = require('react'), { renderToStaticMarkup } = require('react-dom/server');
const data = require('../app/evidence-learning/content.ts'), api = require('../app/evidence-learning/state.ts'), storage = require('../app/evidence-learning/storage.ts');
const Panel = require('../app/evidence-learning/learning-panel.tsx').default;
let transitions = 0, renders = 0, rejected = 0, diagnosticPaths = 0;
const act = (s, a) => { transitions++; const before = JSON.stringify(s), result = api.reduceSession(s, a); assert.equal(JSON.stringify(s), before, 'Reducer mutated original session'); api.parseSession(JSON.stringify(result)); return result; };
const sourceIds = new Set(data.sources.map(s => s.id));
assert.equal(data.diagnosis.length, 3); assert.equal(data.scenarios.length, 3);
for (const c of data.concepts) {
  assert.ok(c.evidence.every(id => sourceIds.has(id)));
  const visit = (id, seen) => { assert.ok(!seen.has(id), 'Concept cycle'); const next = data.concepts.find(c => c.id === id); assert.ok(next); next.prerequisites.forEach(p => visit(p, new Set([...seen, id]))); };
  visit(c.id, new Set());
}
for (const a of data.diagnosis[0].choices) for (const b of data.diagnosis[1].choices) for (const c of data.diagnosis[2].choices) {
  let s = api.emptySession();
  [a,b,c].forEach((choice,i) => s = act(s, { type:'diagnosis', id:data.diagnosis[i].id, choice:choice.id }));
  s = act(s, {type:'diagnosis-done'});
  const map = api.minimalMap(s);
  for (const q of data.diagnosis) for (const id of q.concepts) {
    const conceptMatchedElsewhere = data.diagnosis.some(other => s.diagnosis[other.id] === other.correct && other.concepts.includes(id));
    if (s.diagnosis[q.id] === q.correct || conceptMatchedElsewhere) assert.ok(!map.includes(id), 'Unneeded prerequisite shown');
    else assert.ok(map.includes(id), 'Needed concept omitted');
  }
  diagnosticPaths++;
}
let allCorrect = api.emptySession();
for (const q of data.diagnosis) allCorrect = act(allCorrect, {type:'diagnosis',id:q.id,choice:q.correct});
assert.deepEqual(api.minimalMap(allCorrect), []);
assert.equal(act(api.emptySession(), {type:'diagnosis-done'}).stage, 'diagnosis');
const allUnanswered = act(api.emptySession(), {type:'skip-diagnosis'});
assert.equal(api.minimalMap(allUnanswered).length, data.concepts.length);
const stateHook = React.useState;
function render(state, language, opened = true) {
  let index = 0;
  const values = [opened, state, false, null, 0];
  React.useState = () => [values[index++], () => {}];
  try {
    const html = renderToStaticMarkup(React.createElement(Panel, {locale: language}));
    assert.ok(html.includes('FAIL') && html.includes('UNRESOLVED'));
    assert.ok(html.includes('613/781') && html.includes('97/781') && html.includes('341/781') && html.includes('74/781') && html.includes('574/648'));
    assert.ok(!/NaN|undefined/.test(html));
    if (language === 'en') assert.ok(!/[가-힣]/.test(html), 'Korean leaked into English');
    assert.ok(!/<textarea|type="text"|type="email"|<iframe|<script|<img/.test(html));
    renders++; return html;
  } finally { React.useState = stateHook; }
}
for (const lang of ['ko','en']) for (const s of [api.emptySession(), allUnanswered, act(allCorrect,{type:'diagnosis-done'})]) {render(s,lang);render(s,lang,false);}
for (let index=0;index<data.scenarios.length;index++) {
 const scenario=data.scenarios[index];
 for (const prediction of scenario.predictions) for (const reason of scenario.reasons) {
  let s=act(api.emptySession(),{type:'scenario',index});
  assert.strictEqual(act(s,{type:'reveal'}),s);
  for (const lang of ['ko','en']) assert.ok(!render(s,lang).includes('class="pg-learning-explanation"'));
  s=act(s,{type:'hint'});
  for(const lang of ['ko','en']) {const html=render(s,lang);assert.ok(html.includes(scenario.hints[0][lang]));assert.ok(!html.includes(scenario.hints[1][lang]));}
  s=act(s,{type:'hint'});s=act(s,{type:'hint'});assert.equal(s.progress[scenario.id].hint,2);
  s=act(s,{type:'choose',field:'prediction',choice:prediction.id});
  assert.strictEqual(act(s,{type:'reveal'}),s,'Reason must be selected too');
  s=act(s,{type:'choose',field:'reason',choice:reason.id});s=act(s,{type:'reveal'});
  for(const lang of ['ko','en']) assert.ok(render(s,lang).includes('pg-learning-explanation'));
  assert.strictEqual(act(s,{type:'choose',field:'prediction',choice:scenario.predictionCorrect}),s,'Revealed prediction was overwritten');
  s=act(s,{type:'check-stage'});assert.strictEqual(act(s,{type:'submit-check'}),s);
  for(const check of scenario.check.choices) {
   let checked=act(s,{type:'choose',field:'check',choice:check.id});checked=act(checked,{type:'submit-check'});
   for(const lang of ['ko','en']) render(checked,lang);
   const records=api.conceptRecords(checked);
   assert.equal(records.find(r=>r.concept===scenario.concepts.at(-1)).status,check.id===scenario.check.correct?'check-matched':'review');
   const next=act(checked,{type:'next'});assert.equal(next.progress[scenario.id].phase,'done');
   const skipAfterCheck=act(checked,{type:'skip'});assert.equal(skipAfterCheck.progress[scenario.id].checked,true,'Skip erased a completed check');
   const retry=act(checked,{type:'retry-check'});assert.equal(retry.progress[scenario.id].check,null);
   storage.saveSession({setItem:(_key,raw)=>assert.deepEqual(storage.loadSession({getItem:()=>raw}),next)},next);
  }
 }
 let direct=act(api.emptySession(),{type:'scenario',index});direct=act(direct,{type:'direct'});
 assert.equal(direct.progress[scenario.id].bypassed,true);
 assert.ok(api.conceptRecords(direct).filter(r=>scenario.concepts.includes(r.concept)).every(r=>r.status!=='check-matched'));
 const skipped=act(direct,{type:'skip'});
 assert.ok(api.conceptRecords(skipped).find(r=>r.concept===scenario.concepts[0]).observations.includes(scenario.id),'Viewed observation lost after skipping');
 for(const lang of ['ko','en']) {render(direct,lang);render(skipped,lang);}
}
const fake = new Map([['other-project-record','preserve']]), calls=[];
const port={getItem:key=>(calls.push(['get',key]),fake.get(key)??null),setItem:(key,value)=>(calls.push(['set',key]),fake.set(key,value)),removeItem:key=>(calls.push(['remove',key]),fake.delete(key))};
storage.saveSession(port,allCorrect);assert.deepEqual(storage.loadSession(port),allCorrect);storage.clearSession(port);
assert.equal(fake.get('other-project-record'),'preserve');assert.ok(calls.every(([,key])=>key===storage.STORAGE_KEY));
assert.throws(()=>storage.saveSession({setItem:()=>{throw Error('quota');}},api.emptySession()));
assert.throws(()=>storage.loadSession({getItem:()=>{throw Error('blocked');}}));
for(const mutate of [
 s=>s.identity='private',s=>s.version=2,s=>s.contentVersion='stale',s=>s.scenarioIndex=-1,s=>s.scenarioIndex=100,s=>s.stage='unknown',
 s=>s.diagnosis['d-prob']='free form',s=>s.diagnosis.extra='bad',s=>s.progress.extra={},s=>delete s.progress.probabilities,
 s=>s.progress.probabilities.prediction='text',s=>s.progress.probabilities.hint=99,s=>s.progress.probabilities.hint=-1,
 s=>s.progress.probabilities.checked=true,s=>s.progress.probabilities.phase='done',s=>s.progress.probabilities.explanationSeen=true,
 s=>s.progress.probabilities.freeText='private',s=>s.progress.probabilities.reason={},s=>s.progress.probabilities.bypassed='true'
]) { const fixture=api.emptySession();mutate(fixture);assert.throws(()=>api.parseSession(JSON.stringify(fixture)));rejected++; }
for(const raw of ['{','null','[]','x'.repeat(14001)]) {assert.throws(()=>api.parseSession(raw));rejected++;}
const rootFiles=fs.readdirSync(path.join(root,'app/evidence-learning')).filter(f=>/\.(ts|tsx)$/.test(f));
for(const file of rootFiles) {
 const source=fs.readFileSync(path.join(root,'app/evidence-learning',file),'utf8');
 assert.ok(!/\b(fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon|Worker)\s*\(/.test(source),'Network primitive added');
 assert.ok(!/\beval\s*\(|dangerouslySetInnerHTML|sessionStorage|document\.cookie|indexedDB|navigator\.(geolocation|mediaDevices)/.test(source));
 const imports=[...source.matchAll(/from\s+["']([^"']+)["']/g)].map(m=>m[1]);
 assert.ok(imports.every(name=>name==='react'||name.startsWith('./')),'New provider or external dependency');
 assert.ok(!/libfile_|C:\\\\Users|\.npz|\.h5|Opera/i.test(source));
}
assert.deepEqual(data.publicFacts.gaussian.correct,[613,97,341,74]);assert.equal(data.publicFacts.gaussian.denominator,781);assert.equal(data.publicFacts.gaussian.adaptiveDenominator,648);
assert.equal(data.publicFacts.completeCells,4);assert.equal(data.publicFacts.matchingLabelPairs,10);assert.equal(data.publicFacts.exactProbabilityPairs,0);assert.equal(data.publicFacts.maxProbabilityDelta,2.9206275939941406e-6);
const baseline=JSON.parse(fs.readFileSync(path.join(root,'scripts/fixtures/evidence-learning/public-fixed-array-baseline.json'),'utf8'));
assert.equal(data.publicFacts.selectedImages,baseline.selected_unique_images);assert.equal(data.publicFacts.conditionsPerCell,baseline.selected_conditions_per_cell);
assert.equal(data.publicFacts.matchingLabelPairs,baseline.same_array_cross_environment.matching_label_pairs);assert.equal(data.publicFacts.maxProbabilityDelta,baseline.same_array_cross_environment.max_abs_probability_component_delta);
const gaussian=JSON.parse(fs.readFileSync(path.join(root,'scripts/fixtures/evidence-learning/public-gaussian-baseline.json'),'utf8'));
assert.deepEqual(data.publicFacts.gaussian.correct,['clean','attacked','transfer_defended','adaptive_defended'].map(key=>Math.round(gaussian.overall.accuracy[key]*gaussian.overall.samples)));
assert.equal(data.publicFacts.gaussian.denominator,gaussian.overall.samples);
assert.equal(data.publicFacts.gaussian.adaptiveSuccess,gaussian.overall.asr_adaptive_defended.successes);
assert.equal(data.publicFacts.gaussian.adaptiveDenominator,gaussian.overall.asr_adaptive_defended.denominator);
const report={status:'PASS',diagnostic_paths:diagnosticPaths,pure_transitions_checked:transitions,bilingual_SSR_renders:renders,malformed_records_rejected:rejected,scenario_count:data.scenarios.length,concept_count:data.concepts.length,live_learning_efficacy_tested:false,new_inference:false};
fs.mkdirSync(path.join(root,'qa'),{recursive:true});
fs.writeFileSync(path.join(root,'qa/learning-regression.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
