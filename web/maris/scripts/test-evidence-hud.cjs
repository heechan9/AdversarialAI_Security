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
const { caseConditions } = require('../lib/mission.ts');
const data = require('../public/evidence/data.json');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const locale = require('../app/locale-provider.tsx');

const { evidenceHudState } = require('../lib/evidence-hud.ts');
const Hud = require('../app/evidence-hud.tsx').default;
let checks = 0;
for (const sample of data.samples) for (const epsilon of caseConditions(sample)) {
 for (const step of [0, 1, 2, 3]) {
  const state = {step, epsilon, guess: step >= 2 ? 'same' : null};
  const view = evidenceHudState(sample, state);
  assert.equal(view.imagePart, step === 0 || epsilon === 0 ? 0 : 1);
  assert.equal(view.inputEpsilon, step === 0 ? 0 : epsilon);
  assert.equal(view.prediction, step === 3 ? (epsilon === 0 ? sample.cleanPrediction : sample.attackPrediction) : null);
  assert.equal(view.changed, step === 3 ? (epsilon !== 0 && sample.attackPrediction !== sample.cleanPrediction) : null);
  assert.equal(view.score, step === 3 && epsilon === 0 ? sample.cleanScore : null);
  for (const lang of ['ko','en']) {
   locale.useLocale = () => ({locale:lang, t:(s,v)=>locale.translate(lang,s,v)});
   const html = renderToStaticMarkup(React.createElement(Hud,{data,sample,state}));
   assert.ok(html.includes(sample.sourceUrl));
   assert.ok(html.includes(data.sourceCommit.slice(0,7)));
   assert.ok(!html.includes('NaN'));
   assert.ok(!html.includes('undefined'));
   assert.ok(!html.includes('mission-reticle'));
   assert.ok(!html.includes('mission-scan'));
   assert.ok(html.includes(lang === 'en' ? 'not target detection' : '표적 탐지'));
   if (step !== 3) assert.ok(html.includes(lang === 'en' ? 'Not revealed' : '공개 전'));
   if (epsilon !== 0 && step > 0) assert.ok(html.includes(lang === 'en' ? 'No attack score was saved.' : '공격 후 점수는 저장되지 않았습니다.'));
   if (lang === 'en') assert.ok(!/[가-힣]/.test(html.replace(/<[^>]*>/g,'')));
   checks++;
  }
 }
}
assert.throws(()=>evidenceHudState(data.samples[0],{step:3,epsilon:.01,guess:'same'}),/No recorded/);
const missionSource = fs.readFileSync(path.join(root,'app/mission-console.tsx'),'utf8');
assert.ok(missionSource.includes('stageOverlay: null'));
assert.ok(!missionSource.includes('mission-scan'));
assert.ok(!missionSource.includes('mission-reticle'));
assert.ok(missionSource.includes('className="hud-model-disclosure"'));
console.log(`PASS: ${checks} HUD KO/EN renders, original PNG/commit links, hidden outputs, score nullability, epsilon rejection, no faux detection overlay.`);
