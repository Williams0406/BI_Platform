"use client";
import {useRef} from "react";
import Icon from "@/components/ui/Icon";

const LANGUAGES=[
  {id:"SQL",label:"SQL",mark:"DB"},
  {id:"PYTHON",label:"Python",mark:"Py"},
  {id:"DAX",label:"DAX",mark:"ƒx"},
];
export default function ScriptWorkbench({language,onLanguage,code,onCode,onCommit,busy=false,disabled=false,autoFocus=false,compact=false}){
  const ref=useRef(null);
  function keyDown(e){
    const run=(e.ctrlKey||e.metaKey)&&e.key==="Enter";
    const runNext=(e.shiftKey||e.altKey)&&e.key==="Enter";
    if(!run&&!runNext)return;
    e.preventDefault();
    if(!disabled&&!busy&&String(code||"").trim())onCommit?.({addNext:runNext});
  }
  return <section className={`transformationWorkbench sharedScriptWorkbench unifiedScriptWorkbench ${compact?"compactScriptWorkbench":""}`}>
    <div className="scriptToolbar"><div className="languageSwitch modernLanguageSwitch">{LANGUAGES.map(x=><button type="button" key={x.id} className={language===x.id?"active":""} onClick={()=>onLanguage?.(x.id)} disabled={disabled||busy}><span className="languageMark">{x.mark}</span><span>{x.label}</span></button>)}</div><span className="scriptShortcutHint"><kbd>Ctrl</kbd><span>+</span><kbd>Enter</kbd> run · <kbd>Shift</kbd><span>+</span><kbd>Enter</kbd> run + next</span></div>
    <textarea ref={ref} autoFocus={autoFocus} className="workbenchCodeEditor" value={code} onChange={e=>onCode?.(e.target.value)} onKeyDown={keyDown} spellCheck={false} disabled={disabled||busy}/>
  </section>
}
