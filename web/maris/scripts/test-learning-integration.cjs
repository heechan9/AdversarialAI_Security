// Full Home tree integration: real HUD, results and learning panel, with saved public data.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module'),ts=require('typescript');
const root=path.resolve(__dirname,'..'),resolve=Module._resolveFilename;
Module._resolveFilename=function(request,parent,...rest){return resolve.call(this,request.startsWith('@/')?path.join(root,request.slice(2)):request,parent,...rest)};
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(module,file)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true,target:ts.ScriptTarget.ES2022}}).outputText,file);
require.extensions['.css']=()=>{};
const React=require('react'),{renderToStaticMarkup}=require('react-dom/server'),locale=require('../app/locale-provider.tsx'),data=require('../public/evidence/data.json');
const page=fs.readFileSync(path.join(root,'app/page.tsx'),'utf8');
assert.ok(page.includes('<FixedArrayCrossScore /><EvidenceLearningPanel locale={locale}/>'));
assert.equal((page.match(/<EvidenceLearningPanel /g)||[]).length,1);
assert.ok(page.includes('href="#evidence-learning"'));
const originalState=React.useState,originalLocale=locale.useLocale;
let renders=0;
try{for(const lang of ['ko','en']){
 locale.useLocale=()=>({locale:lang,setLocale:()=>{},t:(s,v)=>locale.translate(lang,s,v)});
 let n=0;React.useState=function(initial){const i=n++;return originalState(i===0?data:i===3?data.samples[0].id:initial)};
 const html=renderToStaticMarkup(React.createElement(require('../app/page.tsx').default));
 assert.ok(html.includes('evidence-hud'));
 assert.ok(html.includes('id="cross-score"'));
 assert.ok(html.indexOf('id="cross-score"')<html.indexOf('id="evidence-learning"'));
 assert.ok(html.indexOf('id="evidence-learning"')<html.indexOf('id="run-review"'));
 assert.ok(html.includes('id="evidence-learning" lang="'+lang+'"'));
 assert.ok(html.includes(lang==='en'?'Open / continue learning':'학습 열기 / 이어가기'));
 for(const value of ['4/4','10/10','FAIL','UNRESOLVED','613/781','97/781','341/781','74/781','574/648'])assert.ok(html.includes(value),value);
 assert.ok(!html.includes('pg-learning-explanation'),'Result revealed on initial load');
 if(lang==='en')assert.ok(!/[가-힣]/.test(html.replace(/<[^>]*>/g,'').replaceAll('한국어','')));
 renders++;
}}finally{React.useState=originalState;locale.useLocale=originalLocale;}
const pins=require('./fixtures/evidence-learning/integration-pins.json');
for(const [file,hash] of Object.entries(pins.unchangedFiles))assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex'),hash,file+' changed');
// The new capture adapter is excluded only by exact reconstruction. Existing 3D
// rendering, visibility and cleanup code must still match the original v24 pin.
function restoredSource(file){
 let source=fs.readFileSync(path.join(root,file),'utf8');
 if(file==='app/ocean.tsx'){
 const sync=source.match(/  \/\/ BEGIN SCENE SYNC\n  const syncScene=\(\)=>\{\n([\s\S]*?)  };\n  \/\/ END SCENE SYNC\n/);
 assert.ok(sync,'Shared scene synchronization missing');
 source=source.replace(sync[0],'').replace('   syncScene();\n   controls.autoRotate=',sync[1]+'   controls.autoRotate=');
 source=source
  .replace('import {useEffect,useRef,useState,type RefObject} from "react";\nimport type {SceneCapture,PixelFrame} from "@/lib/pixel-lab";', 'import {useEffect,useRef,useState} from "react";')
  .replace('onInteract,onZoom,captureRef}:{captureRef?:RefObject<SceneCapture|null>,playing:boolean','onInteract,onZoom}:{playing:boolean')
  .replace(/  \/\/ BEGIN PIXEL CAPTURE[\s\S]*?  \/\/ END PIXEL CAPTURE\n/,'')
  .replace('return()=>{if(captureRef)captureRef.current=null;cancelAnimationFrame(frame);','return()=>{cancelAnimationFrame(frame);')
  .replace(' },[captureRef]);',' },[]);');
 }
 return source;
}
for(const [file,record] of Object.entries(pins.intentional3DRestoreFiles))assert.equal(crypto.createHash('sha256').update(restoredSource(file)).digest('hex'),record.restored_sha256,file+' restored layout changed');
console.log(JSON.stringify({intentional_3D_restore_files:Object.keys(pins.intentional3DRestoreFiles).length,status:'PASS',full_home_KO_EN_SSR_renders:renders,unchanged_public_and_HUD_files:Object.keys(pins.unchangedFiles).length,root_entry:true,locale_passed:true,browser_coverage:false}));
