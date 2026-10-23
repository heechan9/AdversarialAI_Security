const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),ts=require('typescript'),Module=require('node:module');
const root=path.resolve(__dirname,'..'),resolve=Module._resolveFilename;
Module._resolveFilename=function(request,parent,...rest){return resolve.call(this,request.startsWith('@/')?path.join(root,request.slice(2)):request,parent,...rest);};
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(module,file)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true,target:ts.ScriptTarget.ES2022}}).outputText,file);
const React=require('react'),{renderToStaticMarkup}=require('react-dom/server'),locale=require('../app/locale-provider.tsx');
const report=require('../public/evidence/paired-defense-review.json'),worst=require('../public/evidence/worst-class-review.json');
const base=require('../public/evidence/defense-comparison.json');
const Panel=require('../app/paired-defense-review.tsx').default;
const realState=React.useState;let count=0;
assert.equal(report.independent_units_verified,false);
assert.equal(report.inference.mcnemar_p,null);assert.equal(report.inference.bootstrap_ci,null);
assert.equal(require('node:crypto').createHash('sha256').update(fs.readFileSync(path.join(root,'public/evidence/paired-defense-review.json'))).digest('hex'), '8b035db4459bd4bd68eab9dffabc5067418cd8a2123f8abf29f49b19271d2702');
for(const c of report.conditions){
 const existing=base.methods.find(m=>m.id===c.defense).results.find(r=>r.model===c.model&&r.epsilon===c.epsilon);
 assert.equal(c.overall.clean_plain_to_defended.a_correct,Math.round(existing.overall.accuracy.clean*781));
 assert.equal(c.overall.attack_plain_to_adaptive_defended.b_correct,Math.round(existing.overall.accuracy.adaptive_defended*781));
 for(const selected of ['all',...Object.keys(c.by_class)]) for(const lang of ['en','ko']){
  React.useState=()=>[selected,()=>{}];locale.useLocale=()=>({locale:lang});
  const html=renderToStaticMarkup(React.createElement(Panel,{model:c.model,epsilon:c.epsilon,method:c.defense}));
  assert.ok(html.includes('McNemar p = null'));assert.ok(html.includes('bootstrap CI = null'));
  assert.ok(html.includes('id="paired-class"'));assert.ok(!html.includes('NaN'));assert.ok(!html.includes('undefined'));
  if(lang==='en')assert.ok(!/[가-힣]/.test(html.replace(/<[^>]*>/g,'')));
  const row=selected==='all'?c.overall:c.by_class[selected];
  assert.ok(html.includes(String(row.n)));
  for(const kind of ['attack_plain_to_transfer_defended','attack_plain_to_adaptive_defended','defended_transfer_to_adaptive']){
   assert.ok(html.includes(`<td>${row[kind].gained}</td>`));assert.ok(html.includes(`<td>${row[kind].lost}</td>`));
  }
  const w=worst.conditions.find(w=>w.model===c.model&&w.epsilon===c.epsilon);
  for(const k of ['minimum_clean_accuracy','minimum_attacked_accuracy','maximum_conditional_ASR'])assert.ok(html.includes(w[k].classes.join(', ')));
  count++;
 }
}
React.useState=()=>['all',()=>{}];
const missing=renderToStaticMarkup(React.createElement(Panel,{model:'missing',epsilon:.03,method:'mean'}));assert.ok(missing.includes('role="status"'));
React.useState=realState;
const explorer=fs.readFileSync(path.join(root,'app/defense-explorer.tsx'),'utf8');
assert.ok(explorer.includes('<PairedDefenseReview model={model} epsilon={epsilon} method={method}/>'));
const page=fs.readFileSync(path.join(root,'app/page.tsx'),'utf8');assert.ok(page.includes('VerificationStatus'));
console.log(`${count} paired review SSR condition/class/language cases, existing evidence agreement, missing condition fallback, ties and retained verification section: PASS`);
