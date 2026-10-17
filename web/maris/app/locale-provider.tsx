"use client";
import {createContext,useCallback,useContext,useEffect,useSyncExternalStore,type ReactNode} from "react";
import {english} from "@/lib/locale-en";
import {pageEnglish} from "@/lib/page-locale-en";
export type Locale="ko"|"en";
type Values=Record<string,string|number>;
const dictionary={...english,...pageEnglish};
export function translate(locale:Locale,source:string,values?:Values){
 const translated=locale==="en"?(dictionary[source]??source):source;
 return translated.replace(/\{(\w+)\}/g,(match,key)=>values?.[key]===undefined?match:String(values[key]));
}
const localeListeners=new Set<()=>void>();
let currentLocale:Locale|undefined;
const getServerLocale=():Locale=>"ko";
function getLocaleSnapshot():Locale{
 if(currentLocale===undefined){
  try{currentLocale=localStorage.getItem("maris-locale")==="en"?"en":"ko";}catch{currentLocale="ko";}
 }
 return currentLocale;
}
function setLocale(locale:Locale){
 currentLocale=locale;
 try{localStorage.setItem("maris-locale",locale);}catch{}
 localeListeners.forEach(listener=>listener());
}
function subscribeLocale(listener:()=>void){
 localeListeners.add(listener);
 const onStorage=(event:StorageEvent)=>{
  if(event.key!=="maris-locale"&&event.key!==null)return;
  currentLocale=event.newValue==="en"?"en":"ko";
  localeListeners.forEach(notify=>notify());
 };
 window.addEventListener("storage",onStorage);
 return()=>{localeListeners.delete(listener);window.removeEventListener("storage",onStorage);};
}
const LocaleContext=createContext({locale:"ko" as Locale,setLocale,t:(source:string,values?:Values)=>translate("ko",source,values)});
export function LocaleProvider({children}:{children:ReactNode}){
 const locale=useSyncExternalStore(subscribeLocale,getLocaleSnapshot,getServerLocale);
 useEffect(()=>{
  document.documentElement.lang=locale;
  document.title=locale==="en"?"MARIS · Maritime AI Virtual Lab":"MARIS · 해양 AI 가상 실험실";
  const description=document.querySelector('meta[name="description"]');
  description?.setAttribute("content",locale==="en"?"Explore how small changes in vessel images affect AI predictions. A 3D maritime lab with recorded clean-input and FGSM experiments.":"선박 이미지의 작은 변화가 AI 판단에 미치는 영향. 실제 Clean·FGSM 기록을 탐색하는 3D 해양 실험 공간.");
 },[locale]);
 const t=useCallback((source:string,values?:Values)=>translate(locale,source,values),[locale]);
 return <LocaleContext.Provider value={{locale,setLocale,t}}>{children}</LocaleContext.Provider>;
}
export const useLocale=()=>useContext(LocaleContext);
