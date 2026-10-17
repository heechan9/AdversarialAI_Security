// Pure server-render/static regression tests. No browser or interaction claims.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),Module=require('node:module'),ts=require('typescript');
const root=path.resolve(__dirname,'..');
const resolve=Module._resolveFilename;
Module._resolveFilename=function(request,parent,...rest){return resolve.call(this,request.startsWith('@/')?path.join(root,request.slice(2)):request,parent,...rest)};
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(module,file)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true,target:ts.ScriptTarget.ES2022}}).outputText,file);
const React=require('react'),{renderToStaticMarkup}=require('react-dom/server');
const locale=require('../app/locale-provider.tsx');
const dictionary={...require('../lib/locale-en.ts').english,...require('../lib/page-locale-en.ts').pageEnglish};
const sourceFiles=['page.tsx','verification-status.tsx','defense-explorer.tsx','image-comparison.tsx','result-charts.tsx','ocean.tsx'];
let count=0;
for(const name of sourceFiles){const sf=ts.createSourceFile(name,fs.readFileSync(path.join(root,'app',name),'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);const walk=n=>{if(ts.isCallExpression(n)&&n.expression.getText(sf)==='t'&&n.arguments[0]&&ts.isStringLiteral(n.arguments[0])){const k=n.arguments[0].text;if(/[가-힣]/.test(k)){assert.ok(dictionary[k],`${name}: missing translation ${k}`);assert.deepEqual([...k.matchAll(/\{\w+\}/g)].map(m=>m[0]).sort(),[...dictionary[k].matchAll(/\{\w+\}/g)].map(m=>m[0]).sort(),`placeholder mismatch ${k}`);count++;}}ts.forEachChild(n,walk)};walk(sf)}
const snapshot=require('../public/evidence/verification-status.json');
for(const s of [...snapshot.cards.flatMap(c=>[c.title,c.label,c.detail]),snapshot.cause_note,...snapshot.discrepancies.flatMap(i=>[i.title,i.label,...i.events.map(e=>e.note)])])assert.ok(dictionary[s],`snapshot translation missing: ${s}`);
const data=require('../public/evidence/data.json');
assert.equal(locale.translate("en",require("../lib/display.ts").pct(null)),"Undefined");
const originalState=React.useState;
for(const lang of ['ko','en']){
 locale.useLocale=()=>({locale:lang,setLocale:()=>{},t:(s,v)=>locale.translate(lang,s,v)});
 let stateIndex=0;React.useState=function(value){const index=stateIndex++;if(index===0)return originalState(data);if(index===3)return originalState(data.samples[0].id);return originalState(value)};
 const Home=require('../app/page.tsx').default;
 const html=renderToStaticMarkup(React.createElement(Home));
 fs.mkdirSync(path.join(root,'qa'),{recursive:true});fs.writeFileSync(path.join(root,'qa',`render-${lang}.html`),html);
 assert.ok(html.indexOf('id="experiment"')<html.indexOf('id="results"'));
 assert.ok(html.indexOf('id="results"')<html.indexOf('id="defense"'));
 assert.ok(html.indexOf('id="defense"')<html.indexOf('id="progress"'));
 assert.ok(html.includes('775'));assert.ok(html.includes('781'));
 assert.ok(!html.includes('[object Object]'));assert.ok(!/\{v\d\}/.test(html));
 if(lang==='en'){
  const text=html.replace(/<[^>]*>/g,'').replaceAll('한국어','');
  assert.ok(!/[가-힣]/.test(text),`English rendered Korean: ${text.match(/.{0,30}[가-힣].{0,60}/)?.[0]}`);
 }
}
React.useState=originalState;
console.log(`PASS: ${count} localized literals, template placeholders, frozen status translations, KO/EN server render, evidence section order. Not browser QA.`);
