// Pure state/evidence and server-render tests; runtime browser coverage is separate.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const Module = require('node:module');
const root = path.resolve(__dirname, '..');
const resolve = Module._resolveFilename;
Module._resolveFilename = function(request, parent, ...rest) { return resolve.call(this, request.startsWith('@/') ? path.join(root, request.slice(2)) : request, parent, ...rest); };
for (const ext of ['.ts', '.tsx']) require.extensions[ext] = (module, file) => module._compile(ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true, target: ts.ScriptTarget.ES2022 } }).outputText, file);
const { initialMission, reduceMission, recordedCaseOutcome, caseConditions } = require('../lib/mission.ts');
const data = require('../public/evidence/data.json');
const defense = require('../public/evidence/defense-comparison.json');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const locale = require('../app/locale-provider.tsx');
let runs = 0;
for (const sample of data.samples) {
  assert.deepEqual(caseConditions(sample), [0, sample.epsilon]);
  for (const epsilon of caseConditions(sample)) for (const guess of ['same', 'changed']) {
    let state = initialMission(sample);
    assert.equal(reduceMission(sample, state, { type: 'reveal' }), state);
    assert.equal(reduceMission(sample, state, { type: 'guess', guess }), state);
    state = reduceMission(sample, state, { type: 'next' });
    state = reduceMission(sample, state, { type: 'condition', epsilon });
    state = reduceMission(sample, state, { type: 'next' });
    assert.equal(state.step, 2);
    assert.equal(reduceMission(sample, state, { type: 'reveal' }), state);
    state = reduceMission(sample, state, { type: 'guess', guess });
    state = reduceMission(sample, state, { type: 'reveal' });
    assert.equal(state.step, 3);
    assert.equal(reduceMission(sample, state, { type: 'reveal' }), state);
    const result = recordedCaseOutcome(sample, epsilon, guess);
    assert.equal(result.prediction, epsilon === 0 ? sample.cleanPrediction : sample.attackPrediction);
    assert.equal(result.changed, epsilon !== 0 && sample.attackPrediction !== sample.cleanPrediction);
    assert.equal(result.matches, guess === (result.changed ? 'changed' : 'same'));
    state = reduceMission(sample, state, { type: 'back' });
    assert.equal(state.guess, null);
    assert.deepEqual(reduceMission(sample, state, { type: 'reset' }), initialMission(sample));
    const rejected = reduceMission(sample, state, { type: 'condition', epsilon: .01 });
    assert.equal(rejected, state);
    assert.throws(() => recordedCaseOutcome(sample, .01, guess), /No recorded/);
    for (const lang of ['ko', 'en']) {
      locale.useLocale = () => ({ locale: lang, t: (s,v) => locale.translate(lang,s,v) });
      const { MissionReadout, MissionDefense } = require('../app/mission-console.tsx');
      const html = renderToStaticMarkup(React.createElement(MissionReadout, { sample, epsilon, guess }));
      assert.ok(html.includes(sample.sourceUrl));
      assert.ok(html.includes(`data-case-outcome="${result.changed ? 'changed' : 'same'}"`));
      assert.ok(!html.includes('NaN'));
      assert.ok(!html.includes('undefined'));
      if (lang === 'en') assert.ok(!/[가-힣]/.test(html.replace(/<[^>]*>/g,'')));
      const aggregate = renderToStaticMarkup(React.createElement(MissionDefense, { sample, epsilon }));
      const row = defense.methods.find(m=>m.id==='mean').results.find(r=>r.model===sample.model&&r.epsilon===epsilon);
      assert.ok(aggregate.includes(String(row.overall.samples)));
      assert.ok(aggregate.includes(lang === 'en' ? 'not a defended prediction for the selected image' : '선택한 한 장의 방어 결과가 아닙니다'));
      for (const value of [row.overall.accuracy.attacked,row.overall.accuracy.transfer_defended,row.overall.accuracy.adaptive_defended]) assert.ok(aggregate.includes(`${(value*100).toFixed(2)}%`));
      if (epsilon === 0) {
        assert.ok(aggregate.includes(lang === 'en' ? 'Clean input · no filter' : '정상 입력 · 필터 없음'));
        assert.ok(aggregate.includes(lang === 'en' ? "At zero attack strength, we measure the filter" : '공격 강도 0에서는 필터 자체의 영향을 봅니다.'));
        assert.ok(!aggregate.includes(lang === 'en' ? 'generated separately' : '새로 만든 별도 공격'));
      }
      if (lang === 'en') assert.ok(!/[가-힣]/.test(aggregate.replace(/<[^>]*>/g,'')));
    }
    runs++;
  }
}
for (const lang of ['ko', 'en']) {
 locale.useLocale = () => ({ locale: lang, t: (s,v) => locale.translate(lang,s,v) });
 const Console = require('../app/mission-console.tsx').default;
 const error = '연구 기록을 확인하지 못했습니다. 확인되지 않은 수치는 표시하지 않습니다.';
 const errorHtml = renderToStaticMarkup(React.createElement(Console, {data:null,error,onRetry:()=>{},onChoose:()=>{},onOpenEvidence:()=>{},children:()=>null}));
 assert.ok(errorHtml.includes('role="alert"'));
 assert.ok(errorHtml.includes(locale.translate(lang,'다시 불러오기')));
 assert.ok(!errorHtml.includes(locale.translate(lang,'확인된 실험 기록을 불러오는 중입니다.')));
}
const originalUseState = React.useState;
for (const method of defense.methods) for (const sample of data.samples) for (const epsilon of caseConditions(sample)) {
 React.useState = value => originalUseState(value === 'mean' ? method.id : value);
 locale.useLocale = () => ({locale:'en',t:(s,v)=>locale.translate('en',s,v)});
 const { MissionDefense } = require('../app/mission-console.tsx');
 const html = renderToStaticMarkup(React.createElement(MissionDefense,{sample,epsilon}));
 const row = method.results.find(r=>r.model===sample.model&&r.epsilon===epsilon);
 assert.ok(html.includes(locale.translate('en',method.name)));
 for (const value of [row.overall.accuracy.clean,row.overall.accuracy.defended_clean,row.overall.accuracy.attacked,row.overall.accuracy.transfer_defended,row.overall.accuracy.adaptive_defended]) assert.ok(html.includes(`${(value*100).toFixed(2)}%`));
}
React.useState = originalUseState;
console.log(`PASS: ${runs} complete case/condition/guess paths; gated reveal, repeat/back/reset, unsupported epsilon rejection; actual recorded predictions and separate aggregate defense KO/EN render.`);
