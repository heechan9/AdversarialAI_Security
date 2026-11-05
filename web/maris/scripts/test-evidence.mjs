import ts from 'typescript';
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const root=new URL('../',import.meta.url);
const source=fs.readFileSync(new URL('lib/evidence.ts',root),'utf8');
const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const {validateEvidence}=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'));
const bytes=fs.readFileSync(new URL('public/evidence/data.json',root));
const data=JSON.parse(bytes),provenance=JSON.parse(fs.readFileSync(new URL('public/evidence/provenance.json',root)));
assert.equal(createHash('sha256').update(bytes).digest('hex'),provenance.export_sha256);
validateEvidence(data);
for(const s of data.samples){const path='public'+s.asset;const hash=createHash('sha256').update(fs.readFileSync(new URL(path,root))).digest('hex');const repoPath='results/attacks/provisional/samples/'+s.asset.split('/').at(-1);assert.equal(hash,provenance.source_sha256[repoPath]);}
const mutations=[x=>x.results[0].asr=.5,x=>x.results[0].successes++,x=>x.results.push(x.results[0]),x=>x.samples[0].success=!x.samples[0].success,x=>x.samples[0].asset='/secret.png',x=>x.results[0].classes[0].n++];
for(const mutate of mutations){const altered=structuredClone(data);mutate(altered);assert.throws(()=>validateEvidence(altered));}
console.log('PASS: snapshot hash, 4 unchanged image hashes, valid evidence, 6 rejected mutations');

// Synthetic paired predictions only: never modify the saved JSON or images.
// Enumerate the four disjoint clean/attack correctness cells as an independent
// oracle, rather than restating the validator's inequalities in this test.
function fixture(rows) {
 const sample=structuredClone(data.samples[0]);
 const names=rows.map((_,i)=>`Class ${i}`);
 Object.assign(sample,{truth:names[0],cleanPrediction:names[0],attackPrediction:names[0],success:false});
 const classes=rows.map((r,i)=>({...r,name:names[i],asr:r.cleanCorrect?r.successes/r.cleanCorrect:null}));
 const total=Object.fromEntries(['n','cleanCorrect','robustCorrect','successes'].map(k=>[k,classes.reduce((sum,c)=>sum+c[k],0)]));
 return {...data,total:total.n,models:[sample.model],epsilons:[sample.epsilon],classNames:names,samples:[sample],
  results:[{...total,asr:total.cleanCorrect?total.successes/total.cleanCorrect:null,model:sample.model,epsilon:sample.epsilon,classes}]};
}
let accepted=0,rejected=0;
for(let n=1;n<=8;n++) {
 const feasible=new Set();
 for(let bothCorrect=0;bothCorrect<=n;bothCorrect++)
  for(let lost=0;lost<=n-bothCorrect;lost++)
   for(let gained=0;gained<=n-bothCorrect-lost;gained++)
    feasible.add(`${bothCorrect+lost}:${bothCorrect+gained}:${lost}`);
 for(let cleanCorrect=0;cleanCorrect<=n;cleanCorrect++)
  for(let robustCorrect=0;robustCorrect<=n;robustCorrect++)
   for(let successes=0;successes<=cleanCorrect;successes++) {
    const candidate=fixture([{n,cleanCorrect,robustCorrect,successes}]);
    const label=`n=${n}, clean=${cleanCorrect}, attacked=${robustCorrect}, successes=${successes}`;
    if(feasible.has(`${cleanCorrect}:${robustCorrect}:${successes}`)) {
     assert.doesNotThrow(()=>validateEvidence(candidate),label);accepted++;
    } else {assert.throws(()=>validateEvidence(candidate),/Invalid evidence/,label);rejected++;}
   }
}
// The aggregate is feasible in both cases, but one class is impossible.
// This catches accidentally applying the invariant only at aggregate level.
for(const rows of [
 [{n:2,cleanCorrect:1,robustCorrect:0,successes:0},{n:2,cleanCorrect:1,robustCorrect:2,successes:0}],
 [{n:2,cleanCorrect:1,robustCorrect:2,successes:1},{n:2,cleanCorrect:1,robustCorrect:0,successes:1}],
]) assert.throws(()=>validateEvidence(fixture(rows)),/Invalid evidence/);
console.log(`PASS: ${accepted} feasible paired-count cases, ${rejected} impossible cases rejected, 2 masked class inconsistencies rejected`);
