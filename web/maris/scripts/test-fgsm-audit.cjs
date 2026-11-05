/* eslint-disable @typescript-eslint/no-require-imports -- CJS harness transpiles repository TSX for SSR tests. */
/* Actual Python auditor fixtures, report tampering rejection, and bilingual SSR. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),ts=require('typescript'),Module=require('node:module'),{execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),resolve=Module._resolveFilename;
Module._resolveFilename=function(request,parent,...rest){return resolve.call(this,request.startsWith('@/')?path.join(root,request.slice(2)):request,parent,...rest);};
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(module,file)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true,target:ts.ScriptTarget.ES2022}}).outputText,file);
const api=require('../lib/fgsm-audit.ts'),React=require('react'),{renderToStaticMarkup}=require('react-dom/server'),locale=require('../app/locale-provider.tsx'),{AuditSummary}=require('../app/fgsm-run-review.tsx');
const args=[path.join(__dirname,'test-fgsm-audit-fixtures.py')];
if(process.env.PAULGUARD_REPO_ROOT)args.push('--repo-root',process.env.PAULGUARD_REPO_ROOT);
const reports=JSON.parse(execFileSync('python3',args,{encoding:'utf8',maxBuffer:2*1024*1024}));
const snapshot=api.parseAuditJson(fs.readFileSync(path.join(root,'public/evidence/fgsm-run-audit.json'),'utf8'));api.validateAuditSnapshot(snapshot);
const originalState=React.useState,originalLocale=locale.useLocale;
let renders=0,rejections=0;
function rejects(name,mutate,source=reports.public) {const d=structuredClone(source);mutate(d);assert.throws(()=>api.validateAuditReport(d),name);rejections++;}
try {
 for(const [name,data] of Object.entries(reports)) {
  const original=JSON.stringify(data);api.validateAuditReport(data);api.validateAuditReport(api.parseAuditJson('\uFEFF'+original));
  const plan=api.planExport(data);assert.deepEqual(plan.resume_plan,data.resume_plan);
  assert.equal(plan.independent_verification_approval,false);assert.equal(plan.process_liveness,'NOT_CHECKED');
  if(data.execution_errors.length)assert.equal(api.restartCommands(data),null,name);
  else if(data.resume_plan.length) {assert.ok(api.restartCommands(data).includes('REPLACE_WITH_NEW_DIRECTORY/'));for(const p of data.resume_plan)assert.ok(api.restartCommands(data).includes(`--epsilons ${p.epsilons.join(' ')}`));}
  else assert.equal(api.restartCommands(data),null,name);
  for(const lang of ['ko','en'])for(const model of ['all',...api.auditModels.filter(m=>[...data.conditions,...data.missing_conditions].some(c=>c.model===m))]) {
   React.useState=()=>[model,()=>{}];locale.useLocale=()=>({locale:lang});
   const html=renderToStaticMarkup(React.createElement(AuditSummary,{report:data,local:name!=='public'}));
   assert.ok(!/NaN|undefined|\[object Object\]/.test(html));if(lang==='en')assert.ok(!/[가-힣]/.test(html));
   assert.ok(html.includes(`${data.checked_conditions} / ${data.expected_conditions}`));
   assert.equal((html.match(/<tbody><tr|<\/tr><tr/g)||[]).length,[...data.conditions,...data.missing_conditions].filter(c=>model==='all'||c.model===model).length);
   if(data.execution_errors.length)assert.ok(!html.includes('REPLACE_WITH_NEW_DIRECTORY/'));
   renders++;
  }
  assert.equal(JSON.stringify(data),original,'Rendering/export must not mutate the report');
 }
 // Platform paths remain opaque display text, never executable output paths.
 const windows=structuredClone(reports.orphan);
 for(const c of windows.conditions)c.file=c.file.replaceAll('/','\\');
 for(const v of windows.invocations)v.directory=v.directory.replaceAll('/','\\');
 api.validateAuditReport(windows);
 const injected=structuredClone(reports.interrupted);injected.invocations[0].directory+='; $(echo BAD)';
 for(const c of injected.conditions)c.file=c.file.slice(0,c.file.lastIndexOf('/'))+'; $(echo BAD)/'+path.basename(c.file);
 api.validateAuditReport(injected);assert.ok(!api.restartCommands(injected).includes('BAD'));
 rejects('false success',d=>d.result='FULL_REQUESTED_SAVED_SAMPLE_COVERAGE',reports.orphan);
 rejects('approval escalation',d=>d.independent_verification_approval=true);
 rejects('process liveness escalation',d=>d.process_liveness='RUNNING');
 rejects('probability comparison escalation',d=>d.probabilities_compared=true);
 rejects('count mismatch',d=>d.checked_conditions--);
 rejects('duplicate saved condition',d=>d.conditions[1]=d.conditions[0]);
 rejects('wrong sample count',d=>d.conditions[0].rows=780);
 rejects('bad hash',d=>d.conditions[0].sha256='hello');
 rejects('different model epsilon sets',d=>d.conditions[0].epsilon=.99);
 rejects('colliding output filename tokens',d=>{d.conditions[0].epsilon=.01000001;d.conditions[4].epsilon=.01000001;});
 rejects('unknown model',d=>d.conditions[0].model='cnn;echo BAD');
 rejects('infinite epsilon',d=>d.conditions[0].epsilon=Infinity);
 rejects('boolean epsilon',d=>d.conditions[0].epsilon=false);
 rejects('duplicate plan model',d=>d.resume_plan.push(d.resume_plan[0]),reports.interrupted);
 rejects('dropped missing epsilon',d=>d.resume_plan[0].epsilons.pop(),reports.interrupted);
 rejects('invented rerun condition',d=>d.rerun_conditions=[{model:'cnn',epsilon:0,reason:'RECORDED_EXECUTION_ERROR'}]);
 rejects('error hidden',d=>d.execution_errors=[],reports.error);
 rejects('extra unrecorded condition',d=>d.invocations[0].unrecorded_saved_epsilons=[],reports.orphan);
 rejects('legacy marked completed',d=>d.invocations[0].completion_record_consistent=true);
 rejects('error treated as completed',d=>d.invocations[0].completion_record_consistent=true,reports.error);
 rejects('wrong provenance',d=>d.invocations[0].provenance='LEGACY_EXECUTION_PROVENANCE_UNVERIFIED',reports.error);
 rejects('orphan saved path',d=>d.conditions[0].file='/another/file.csv');
 for(const input of ['{"kind":1,"kind":2}','{"k":1,"\\u006b":2}','{"x":NaN}','{"x":1e999}','[1,]','{',' '.repeat(2*1024*1024+1),'['.repeat(42)+'0'+']'.repeat(42)]) {assert.throws(()=>api.parseAuditJson(input));rejections++;}
 assert.deepEqual(api.parseAuditJson('{"x":"brace } quote \\\"","a":[1,true,null,{},[]]}'),{x:'brace } quote "',a:[1,true,null,{},[]]});
 const code=fs.readFileSync(path.join(root,'app/fgsm-run-review.tsx'),'utf8');
 assert.ok(!/localStorage|sessionStorage|FormData|method\s*:\s*['"]POST/.test(code),'File imports must not upload or persist data');
 assert.equal((code.match(/fetch\(/g)||[]).length,1,'Only the public snapshot is fetched');
} finally {React.useState=originalState;locale.useLocale=originalLocale;}
console.log(`PASS: ${Object.keys(reports).length} actual Python audit fixtures, ${rejections} malformed/tampered report rejections, ${renders} KO/EN filtered SSR cases, safe command templates and unchanged report exports. Not browser QA.`);
