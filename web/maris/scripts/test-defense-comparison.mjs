import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const root=new URL('../public/evidence/',import.meta.url);
const bytes=fs.readFileSync(new URL('defense-comparison.json',root));
const d=JSON.parse(bytes),p=JSON.parse(fs.readFileSync(new URL('defense-comparison-provenance.json',root)));
assert.equal(createHash('sha256').update(bytes).digest('hex'),p.export_sha256);
assert.equal(d.status,'experimental');
for(const m of d.methods){
 const seen=new Set();assert.equal(p.audits[m.id].status,'PASSED');
 assert.equal(m.results.length,d.models.length*d.epsilons.length);
 for(const r of m.results){
  const key=r.model+':'+r.epsilon;assert.ok(!seen.has(key));seen.add(key);
  assert.ok(d.models.includes(r.model)&&d.epsilons.includes(r.epsilon));
  const o=r.overall,n=o.samples;assert.ok(Number.isSafeInteger(n)&&n>0);
  for(const v of Object.values(o.accuracy)){assert.ok(Number.isFinite(v)&&v>=0&&v<=1);assert.ok(Math.abs(v*n-Math.round(v*n))<1e-8);}
  for(const [key,pipeline] of [['asr_original','clean'],['asr_transfer_defended','defended_clean'],['asr_adaptive_defended','defended_clean']]){
   const a=o[key];assert.equal(a.denominator,Math.round(o.accuracy[pipeline]*n));
   assert.ok(Number.isSafeInteger(a.successes)&&a.successes>=0&&a.successes<=a.denominator);
   assert.equal(a.asr,a.denominator?a.successes/a.denominator:null);
  }
  assert.equal(Math.round((o.accuracy.defended_clean-o.accuracy.clean)*n),o.clean_recovered-o.clean_harmed);
  if(r.epsilon===0){assert.equal(o.accuracy.clean,o.accuracy.attacked);assert.equal(o.accuracy.defended_clean,o.accuracy.adaptive_defended);assert.equal(o.asr_adaptive_defended.successes,0);}
 }
}
for(const r of d.methods[0].results){const other=d.methods[1].results.find(x=>x.model===r.model&&x.epsilon===r.epsilon);assert.equal(r.overall.accuracy.clean,other.overall.accuracy.clean);assert.equal(r.overall.accuracy.attacked,other.overall.accuracy.attacked);}
console.log('PASS: both defense exports, complete conditions, integer counts, pipeline ASR denominators, epsilon-zero and common baselines.');
