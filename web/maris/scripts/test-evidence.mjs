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
