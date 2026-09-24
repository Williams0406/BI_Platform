"use client";
import {useEffect,useRef} from "react";
const LANGUAGES=[{id:"SQL",label:"SQL",mark:"DB"},{id:"PYTHON",label:"Python",mark:"Py"},{id:"DAX",label:"DAX",mark:"ƒx"}];
export default function ScriptWorkbench({language,onLanguage,code,onCode,onCommit,busy=false,disabled=false,autoFocus=false,compact=false,toolbarEnd=null,validation=null}){
 const ref=useRef(null);
 function fitHeight(){const el=ref.current;if(!el)return;el.style.height="26px";const next=Math.max(26,el.scrollHeight);el.style.height=`${next}px`;}
 useEffect(()=>{fitHeight()},[code]);
 function keyDown(e){const run=(e.ctrlKey||e.metaKey)&&e.key==="Enter";const runNext=(e.shiftKey||e.altKey)&&e.key==="Enter";if(!run&&!runNext)return;e.preventDefault();if(!disabled&&!busy&&String(code||"").trim())onCommit?.({addNext:runNext})}
 return <section className={`transformationWorkbench sharedScriptWorkbench unifiedScriptWorkbench ${compact?"compactScriptWorkbench":""} ${validation?.valid===false?"scriptHasError":""}`}>
  <div className="scriptToolbar"><div className="languageSwitch modernLanguageSwitch">{LANGUAGES.map(x=><button type="button" key={x.id} className={language===x.id?"active":""} onClick={()=>onLanguage?.(x.id)} disabled={disabled||busy}><span className="languageMark">{x.mark}</span><span>{x.label}</span></button>)}</div><div className="scriptToolbarEnd">{toolbarEnd}</div></div>
  <textarea ref={ref} rows={1} autoFocus={autoFocus} className="workbenchCodeEditor" value={code} onChange={e=>{onCode?.(e.target.value);requestAnimationFrame(fitHeight)}} onKeyDown={keyDown} spellCheck={false} disabled={disabled||busy}/>
  {validation?.valid===false?<div className="scriptValidationError"><strong>Syntax error</strong><span>{validation.error||"Review the highlighted code block."}</span></div>:null}
 </section>
}
