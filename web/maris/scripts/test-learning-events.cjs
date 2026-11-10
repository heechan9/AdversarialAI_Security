// Event-handler contract tests with injected storage; no browser claim.
require('./test-evidence-learning.cjs');
const assert=require('node:assert/strict'),React=require('react');
const api=require('../app/evidence-learning/state.ts'),{STORAGE_KEY}=require('../app/evidence-learning/storage.ts'),Panel=require('../app/evidence-learning/learning-panel.tsx').default;
const original={useState:React.useState,useEffect:React.useEffect,useRef:React.useRef};
const values=[true,api.emptySession(),false,null,0];let calls={read:0,write:0,remove:0},raw=null,fail=false;
const port={getItem(key){assert.equal(key,STORAGE_KEY);calls.read++;return raw},setItem(key,value){assert.equal(key,STORAGE_KEY);calls.write++;if(fail)throw Error('synthetic quota');raw=value},removeItem(key){assert.equal(key,STORAGE_KEY);calls.remove++;raw=null}};
function flatten(node){if(!node||typeof node!=='object')return [];return [node,...[node.props?.children].flat(Infinity).flatMap(flatten)]}
function render(){let i=0;React.useState=()=>{const n=i++;return [values[n],v=>{values[n]=typeof v==='function'?v(values[n]):v}]};React.useEffect=()=>{};React.useRef=()=>({current:null});return flatten(Panel({locale:'en',storage:port}))}
function checkbox(nodes){return nodes.find(n=>n.type==='input'&&n.props.type==='checkbox')}
function button(nodes,text){return nodes.find(n=>n.type==='button'&&n.props.children===text)}
try{
 let tree=render();assert.deepEqual(calls,{read:0,write:0,remove:0});
 checkbox(tree).props.onChange({target:{checked:true}});assert.equal(values[2],true);assert.equal(calls.write,1);assert.equal(calls.read,0);assert.ok(!raw.includes('identity'));
 tree=render();const radio=tree.find(n=>n.type==='input'&&n.props.type==='radio');radio.props.onChange();assert.equal(calls.write,2);assert.ok(Object.values(api.parseSession(raw).diagnosis).some(Boolean));
 tree=render();checkbox(tree).props.onChange({target:{checked:false}});assert.equal(raw,null);assert.equal(values[2],false);assert.equal(calls.remove,1);assert.ok(Object.values(values[1].diagnosis).some(Boolean));
 tree=render();fail=true;checkbox(tree).props.onChange({target:{checked:true}});assert.equal(values[2],false);assert.ok(values[3].en.includes('Device save failed'));fail=false;
 tree=render();checkbox(tree).props.onChange({target:{checked:true}});const saved=JSON.parse(raw);values[1]=api.emptySession();values[2]=false;
 tree=render();button(tree,"Load this feature's device record").props.onClick();assert.equal(calls.read,1);assert.deepEqual(values[1],saved);assert.equal(values[2],true);
 tree=render();button(tree,"Reset all · delete this feature's saved copy").props.onClick();assert.equal(raw,null);assert.equal(values[2],false);assert.deepEqual(values[1],api.emptySession());
 console.log(JSON.stringify({status:'PASS',injected_storage_event_contracts:7,storage_access_on_initial_render:0,synthetic_write_failure_falls_back:true,real_browser:false}));
}finally{Object.assign(React,original)}
