"use client";
import {useEffect,useRef} from "react";
import {usePathname} from "next/navigation";
import {useWorkspace} from "@/lib/hooks/useWorkspace";
import {writeCodeDraft} from "@/lib/storage/codeDrafts";
import {matchesDeletedCode} from "@/lib/storage/codeDeletion";
const LANGUAGES=[{id:"SQL",label:"SQL",mark:"DB"},{id:"PYTHON",label:"Python",mark:"Py"},{id:"DAX",label:"DAX",mark:"ƒx"}];
export default function ScriptWorkbench({language,onLanguage,code,onCode,onCommit,busy=false,disabled=false,autoFocus=false,compact=false,toolbarEnd=null,validation=null,draftKey="main",metricId=null}){
 const pathname=usePathname();
 const {activeWorkspace}=useWorkspace();
 const previous=useRef(null);
 useEffect(()=>{
  // The Code notebook owns its cells directly. A temporary saved cell may be
  // deleted after a failed execution, and that cleanup must never erase the
  // draft the user is still editing. Other workspaces still react to genuine
  // code deletions as before.
  if(pathname==="/app/scripts")return;
  const clearDeleted=event=>{if(String(event.detail.workspace)===String(activeWorkspace?.id)&&matchesDeletedCode(code,language,event.detail))onCode?.("")};
  window.addEventListener("bi-code-deleted",clearDeleted);
  return()=>window.removeEventListener("bi-code-deleted",clearDeleted);
 },[pathname,activeWorkspace?.id,code,language,onCode]);
 useEffect(()=>{
  if(pathname==="/app/scripts"||!activeWorkspace?.id)return;
  const id=`${pathname}:${draftKey}`;
  const owner=`${activeWorkspace.id}:${id}`;
  // Empty initial mounts must not erase a draft from another visit.
  if(code?.trim()||previous.current===owner)writeCodeDraft(activeWorkspace.id,id,{code,language,source:pathname,metricId});
  previous.current=code?.trim()?owner:null;
 },[code,language,pathname,draftKey,metricId,activeWorkspace?.id]);
 const ref=useRef(null);
 function fitHeight(){const el=ref.current;if(!el)return;el.style.height="26px";const next=Math.max(26,el.scrollHeight);el.style.height=`${next}px`;}
 useEffect(()=>{fitHeight()},[code]);
 function keyDown(e){
  const run=(e.ctrlKey||e.metaKey)&&e.key==="Enter";const runNext=(e.shiftKey||e.altKey)&&e.key==="Enter";
  if(run||runNext){e.preventDefault();if(!disabled&&!busy&&String(code||"").trim())onCommit?.({addNext:runNext});return}
  if(disabled||busy||e.ctrlKey||e.metaKey||e.altKey)return;
  const pairs={"(":")","[":"]","{":"}","\"":"\"","'":"'","`":"`"};
  const close=pairs[e.key];if(!close)return;
  const el=e.currentTarget,start=el.selectionStart,end=el.selectionEnd,current=String(code||""),selected=current.slice(start,end);
  // If the matching quote/closer is already immediately to the right, move
  // over it instead of producing a duplicate character.
  if(start===end&&current[start]===e.key&&(e.key==="\""||e.key==="'"||e.key==="`")){e.preventDefault();requestAnimationFrame(()=>el.setSelectionRange(start+1,start+1));return}
  e.preventDefault();const next=current.slice(0,start)+e.key+selected+close+current.slice(end);onCode?.(next);
  requestAnimationFrame(()=>{const caret=selected?start+selected.length+2:start+1;el.focus();el.setSelectionRange(caret,caret);fitHeight()});
 }
 return <section className={`transformationWorkbench sharedScriptWorkbench unifiedScriptWorkbench ${compact?"compactScriptWorkbench":""} ${validation?.valid===false?"scriptHasError":""}`}>
  <div className="scriptToolbar"><div className="languageSwitch modernLanguageSwitch">{LANGUAGES.map(x=><button type="button" key={x.id} className={language===x.id?"active":""} onClick={()=>onLanguage?.(x.id)} disabled={disabled||busy}><span className="languageMark">{x.mark}</span><span>{x.label}</span></button>)}</div><div className="scriptToolbarEnd">{toolbarEnd}</div></div>
  <textarea ref={ref} rows={1} autoFocus={autoFocus} className="workbenchCodeEditor" value={code} onChange={e=>{onCode?.(e.target.value);requestAnimationFrame(fitHeight)}} onKeyDown={keyDown} spellCheck={false} disabled={disabled||busy}/>
  {validation?.valid===false?<div className="scriptValidationError"><strong>{String(validation.error||"").toLowerCase().includes("environment error")||String(validation.error||"").toLowerCase().includes("not installed")?"Environment error":"Execution error"}</strong><span>{validation.error||"Review the highlighted code block."}</span></div>:null}
 </section>
}
