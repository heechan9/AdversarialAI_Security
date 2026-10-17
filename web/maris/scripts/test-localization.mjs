import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
const readDictionary=(file,name)=>{
 const result=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;
 const context={exports:{}};vm.runInNewContext(result,context);return context.exports[name];
};
const dictionary={...readDictionary('lib/locale-en.ts','english'),...readDictionary('lib/page-locale-en.ts','pageEnglish')};
const placeholders=text=>[...text.matchAll(/\{(\w+)\}/g)].map(m=>m[1]).sort();
for(const [key,value] of Object.entries(dictionary))assert.deepEqual(placeholders(key),placeholders(value),`Placeholder mismatch: ${key}`);
const files=['app/page.tsx','app/verification-status.tsx','app/image-comparison.tsx','app/defense-explorer.tsx','app/result-charts.tsx','app/ocean.tsx'];
let checked=0;const missing=[];
for(const file of files){
 const ast=ts.createSourceFile(file,fs.readFileSync(file,'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 function visit(node){
  if(ts.isCallExpression(node)&&node.expression.getText(ast)==='t'&&ts.isStringLiteral(node.arguments[0])){
   const key=node.arguments[0].text;if(/[가-힣]/.test(key)){checked++;if(!Object.hasOwn(dictionary,key))missing.push(`${file}: ${key}`);}
  }
  if(ts.isJsxText(node)&&/[가-힣]/.test(node.text))missing.push(`${file}: untranslated JSX text: ${node.text}`);
  if(ts.isJsxAttribute(node)&&node.initializer&&ts.isStringLiteral(node.initializer)&&/[가-힣]/.test(node.initializer.text))missing.push(`${file}: untranslated ${node.name.getText(ast)}`);
  ts.forEachChild(node,visit);
 }
 visit(ast);
}
assert.deepEqual(missing,[],`Missing English translations:\n${missing.join('\n')}`);
const defense=JSON.parse(fs.readFileSync('public/evidence/defense-comparison.json','utf8'));
for(const method of defense.methods){assert.ok(dictionary[method.name]);assert.ok(dictionary[method.description]);}
const snapshot=JSON.parse(fs.readFileSync('public/evidence/verification-status.json','utf8'));
const snapshotStrings=[snapshot.cause_note,...snapshot.cards.flatMap(card=>[card.title,card.label,card.detail]),...snapshot.discrepancies.flatMap(issue=>[issue.title,issue.label,...issue.events.map(event=>event.note)])];
for(const source of snapshotStrings)assert.ok(dictionary[source],`Missing snapshot translation: ${source}`);
for(const source of ['항공모함','벌크선','자동차 운반선','컨테이너선','크루즈선','구축함','레저선','범선','잠수함','예인선','정의 불가'])assert.ok(dictionary[source],`Missing display translation: ${source}`);
console.log(`PASS: ${checked} literal translations, interpolation parity, filter metadata, snapshot records, and ship classes.`);
