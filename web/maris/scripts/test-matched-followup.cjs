const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const ts = require('typescript');
const Module = require('node:module');
const {execFileSync} = require('node:child_process');
const root = path.resolve(__dirname, '..'), repo = path.resolve(root, '../..');
const resolve = Module._resolveFilename;
Module._resolveFilename = function(request, parent, ...rest) { return resolve.call(this, request.startsWith('@/') ? path.join(root, request.slice(2)) : request, parent, ...rest); };
for (const ext of ['.ts', '.tsx']) require.extensions[ext] = (module, file) => module._compile(ts.transpileModule(fs.readFileSync(file, 'utf8'), {compilerOptions: {module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true, target: ts.ScriptTarget.ES2022}}).outputText, file);
const React = require('react'), {renderToStaticMarkup} = require('react-dom/server');
const locale = require('../app/locale-provider.tsx');
const Panel = require('../app/matched-cnn-followup.tsx').default;
const report = require('../public/evidence/matched-cnn-followup.json');
const saved = JSON.parse(execFileSync('python', ['verification/matched_cnn_saved_audit.py'], {cwd: repo, encoding: 'utf8'}));
assert.equal(report.sourceCommit, '13d92a15c3b8953e24b5d44326cd2327973a7a25');
assert.equal(report.status, 'COMPLETED_NOT_INDEPENDENT_APPROVAL');
assert.equal(report.independentVerificationApproval, false);
assert.deepEqual(report.completedTrainingSeeds, [2026]);
assert.deepEqual(report.unrunTrainingSeeds, [2027, 2028]);
assert.equal(report.scope.existingExternalStageB, 'FAIL');
assert.equal(report.scope.independentReproductionComplete, false);
assert.deepEqual(report.mixedMinusCleanOnly, saved.mixed_minus_clean_only);
for (const [file, hash] of Object.entries(report.sourceSha256)) {
 assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(repo, file))).digest('hex'), hash, file);
}
for (const model of ['baseline', 'clean_only', 'pgd_mixed']) for (const condition of ['clean', 'pgd7', 'pgd50']) assert.deepEqual(report.models[model][condition], saved.models[model][condition]);
const oldState = React.useState, oldLocale = locale.useLocale;
const originalReport = structuredClone(report);
const cautionParagraphs = html => {
 const aside = html.match(/<aside class="matched-caution"[\s\S]*?<\/aside>/)[0];
 return [...aside.matchAll(/<p>(.*?)<\/p>/g)].map(match => match[1]);
};
function verifyWarning(html, language, expected) {
 const [strong, interpretation] = cautionParagraphs(html);
 const {accuracy, gained, lost, net, difference, pgd7} = expected;
 if (language === 'en') {
  assert.equal(strong, `PGD-mixed accuracy under PGD50 / 5 restarts is ${accuracy}%. Compared with clean-only: ${gained} newly correct − ${lost} newly incorrect = ${net} net correct (${difference} percentage points).`);
  assert.ok(interpretation.includes(`PGD7 ${pgd7} percentage points; PGD50 ${difference} percentage points.`));
 } else {
  assert.equal(strong, `PGD50·5회 재시작에서 PGD 혼합학습의 정확도는 ${accuracy}%입니다. 정상 추가학습 대비 새 정답 ${gained}장 − 새 오답 ${lost}장 = 정답 ${net < 0 ? '순감' : '순증'} ${Math.abs(net)}장(${difference}%p)입니다.`);
  assert.ok(interpretation.includes(`PGD7 ${pgd7}%p, PGD50 ${difference}%p`));
 }
 assert.ok(!strong.includes('+-') && !interpretation.includes('+-'));
}
let count = 0;
for (const language of ['ko', 'en']) for (const selected of ['all', 'clean', 'pgd7', 'pgd50']) {
 React.useState = () => [selected, () => {}]; locale.useLocale = () => ({locale: language});
 const html = renderToStaticMarkup(React.createElement(Panel));
 assert.equal((html.match(/class="matched-condition-card"/g) || []).length, selected === 'all' ? 3 : 1);
 assert.ok(html.includes('6.15%')); assert.ok(html.includes('28')); assert.ok(html.includes('21'));
 verifyWarning(html, language, {accuracy:'6.15', gained:28, lost:21, net:7, difference:'+0.90', pgd7:'+7.43'});
 assert.ok(html.includes('2027')); assert.ok(html.includes('2028')); assert.ok(html.includes('Stage B FAIL'));
 assert.ok(html.includes('id="matched-condition"')); assert.ok(html.includes('aria-describedby="matched-controls-note"'));
 assert.ok(html.includes('role="status"')); assert.ok(html.includes('<details'));
 if (language === 'en') assert.ok(!/[가-힣]/.test(html));
 const renderedConditions = selected === 'all' ? ['clean', 'pgd7', 'pgd50'] : [selected];
 for (const c of renderedConditions) for (const model of ['baseline', 'clean_only', 'pgd_mixed']) assert.ok(html.includes(`${(saved.models[model][c].accuracy * 100).toFixed(2)}%`));
 assert.ok(!/drive\.google|colab\.research|<img|NaN|undefined/.test(html));
 count++;
}
// These intentionally synthetic, in-memory fixtures leave cached accuracy,
// net_correct and percentage_points stale. Real evidence files are never edited.
const scenarios = [
 {mixed50:64, clean50:61, gained:10, lost:7, mixed7:160,
  expected:{accuracy:'8.19', gained:10, lost:7, net:3, difference:'+0.38', pgd7:'+8.96'}},
 {mixed50:30, clean50:41, gained:4, lost:15, mixed7:70,
  expected:{accuracy:'3.84', gained:4, lost:15, net:-11, difference:'-1.41', pgd7:'-2.56'}},
 {mixed50:41, clean50:41, gained:8, lost:8, mixed7:90,
  expected:{accuracy:'5.25', gained:8, lost:8, net:0, difference:'0.00', pgd7:'0.00'}},
];
let synthetic = 0;
try {
 for (const scenario of scenarios) {
  Object.assign(report, structuredClone(originalReport));
  report.models.pgd_mixed.pgd50.correct = scenario.mixed50;
  report.models.clean_only.pgd50.correct = scenario.clean50;
  report.models.pgd_mixed.pgd7.correct = scenario.mixed7;
  report.mixedMinusCleanOnly.pgd7.newly_correct = Math.max(0, scenario.mixed7 - 90);
  report.mixedMinusCleanOnly.pgd7.newly_incorrect = Math.max(0, 90 - scenario.mixed7);
  report.mixedMinusCleanOnly.pgd50.newly_correct = scenario.gained;
  report.mixedMinusCleanOnly.pgd50.newly_incorrect = scenario.lost;
  for (const language of ['ko', 'en']) for (const selected of ['all', 'clean', 'pgd7', 'pgd50']) {
   React.useState = () => [selected, () => {}]; locale.useLocale = () => ({locale:language});
   const html = renderToStaticMarkup(React.createElement(Panel));
   verifyWarning(html, language, scenario.expected);
   if (selected === 'all' || selected === 'pgd50') assert.ok(html.includes(`<strong>${scenario.expected.accuracy}%</strong>`));
   synthetic++;
  }
 }
} finally {
 Object.assign(report, originalReport);
}
React.useState = oldState; locale.useLocale = oldLocale;
const page = fs.readFileSync(path.join(root, 'app/page.tsx'), 'utf8');
const historical = source => source.match(/<div className="retained-research-progress"[\s\S]*?<VerificationStatus \/>/)[0];
const original = execFileSync('git', ['show', `${report.sourceCommit}:web/maris/app/page.tsx`], {cwd: repo, encoding: 'utf8'});
assert.equal(historical(page), historical(original), 'October 12 panel changed');
assert.ok(page.indexOf('<MatchedCnnFollowup />') < page.indexOf('id="progress"'));
assert.ok(page.includes('이 안내는 해당 기존 패널에만 적용됩니다.'));
const before = fs.readFileSync(path.join(root, 'public/evidence/matched-cnn-followup.json'));
execFileSync('python', ['web/maris/scripts/export-matched-followup.py'], {cwd: repo});
assert.deepEqual(fs.readFileSync(path.join(root, 'public/evidence/matched-cnn-followup.json')), before, 'Export must reproduce exactly');
console.log(`PASS: ${count} recorded and ${synthetic} synthetic condition/language renders; warnings follow JSON counts including positive/negative/zero changes with stale cached metrics; audited source hashes; deterministic export; unchanged October 12 panel. Not browser or independent model reproduction.`);
