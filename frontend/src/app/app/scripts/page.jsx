"use client";
import {useEffect,useMemo,useState} from "react";
import {useWorkspace} from "@/lib/hooks/useWorkspace";
import {analyzeScript,createScriptBlock,deleteScriptBlock,listScriptBlocks,updateScriptBlock} from "@/lib/services/scripts";
import EmptyState from "@/components/ui/EmptyState";
import ScriptWorkbench from "@/components/data/ScriptWorkbench";
import Icon from "@/components/ui/Icon";
import WorkspaceCommandBar from "@/components/data/WorkspaceCommandBar";
const listValue=v=>Array.isArray(v)?v:v?.results||[];
const newDraft=(language="PYTHON")=>({id:`draft-${Date.now()}-${Math.random().toString(36).slice(2)}`,language,code:"",busy:false,validation:null});
const artifactNames=item=>(item.artifacts||[]).map(a=>a.name).filter(Boolean);
const references=(code,names)=>names.some(name=>new RegExp(`(^|[^A-Za-z0-9_])${String(name).replace(/[.*+?^${}()|[\]\\]/g,"\\$&")}([^A-Za-z0-9_]|$)`,"i").test(code||""));
function SavedCell({item,index,onReload,onDelete,onAddNext,dependent}){
 const [language,setLanguage]=useState(item.language),[code,setCode]=useState(item.code),[busy,setBusy]=useState(false),[validation,setValidation]=useState(null);
 useEffect(()=>{setLanguage(item.language);setCode(item.code);setValidation(null)},[item.id,item.updated_at]);
 async function run({addNext=false}={}){if(!code.trim()||busy)return;setBusy(true);try{const check=await analyzeScript(language,code);setValidation(check);if(check?.valid===false)return;await updateScriptBlock(item.id,{language,code,status:"SAVED"});await onReload();if(addNext)onAddNext(language)}finally{setBusy(false)}}
 async function remove(){if(!window.confirm("Delete this code block?"))return;await onDelete(item)}
 const meta=<><div className="notebookExecutionMeta">{(item.artifacts||[]).slice(0,3).map(a=><span key={a.id||`${a.artifact_type}-${a.name}`}>{a.artifact_type.replaceAll("_"," ")}</span>)}</div><button type="button" className="notebookDelete inlineDelete" aria-label="Delete code block" title="Delete block" onClick={remove}>×</button></>;
 return <article className={`notebookCell streamlinedNotebookCell ${dependent?"dependentScriptCell":""}`}><div className="notebookPromptVisible">In [{index+1}]</div><div className="notebookCellBody"><ScriptWorkbench language={language} onLanguage={setLanguage} code={code} onCode={setCode} onCommit={run} busy={busy} validation={validation} toolbarEnd={meta}/>{dependent?<div className="dependencyWarning">This block depends on an artifact from the deleted block. Review it or undo the deletion.</div>:null}</div></article>
}
export default function ScriptsPage(){
 const {activeWorkspace}=useWorkspace();const [items,setItems]=useState([]),[drafts,setDrafts]=useState([]),[undo,setUndo]=useState(null),[dependentIds,setDependentIds]=useState([]);
 async function load(){if(activeWorkspace?.id)setItems(listValue(await listScriptBlocks(activeWorkspace.id)))}
 useEffect(()=>{load()},[activeWorkspace?.id]);
 function addBlock(language="PYTHON"){setDrafts(current=>[...current,newDraft(language)])}
 function patchDraft(id,patch){setDrafts(current=>current.map(d=>d.id===id?{...d,...patch}:d))}
 async function commitDraft(draft,{addNext=false}={}){if(!activeWorkspace?.id||!draft.code.trim()||draft.busy)return;patchDraft(draft.id,{busy:true});try{const check=await analyzeScript(draft.language,draft.code);patchDraft(draft.id,{validation:check});if(check?.valid===false)return;await createScriptBlock({workspace:activeWorkspace.id,name:`${draft.language} · ${new Date().toLocaleString()}`,language:draft.language,purpose:"",code:draft.code,context:{section:"notebook"},status:"SAVED"});setDrafts(current=>current.filter(d=>d.id!==draft.id));await load();if(addNext)addBlock(draft.language)}finally{patchDraft(draft.id,{busy:false})}}
 async function removeSaved(item){const names=artifactNames(item);const affected=items.filter(x=>x.id!==item.id&&references(x.code,names)).map(x=>x.id);await deleteScriptBlock(item.id);setItems(current=>current.filter(x=>x.id!==item.id));setDependentIds(affected);setUndo({item,affected})}
 async function undoDelete(){if(!undo||!activeWorkspace?.id)return;const x=undo.item;await createScriptBlock({workspace:activeWorkspace.id,name:x.name,language:x.language,purpose:x.purpose||"",code:x.code,context:x.context||{section:"notebook"},status:x.status||"SAVED"});setUndo(null);setDependentIds([]);await load()}
 if(!activeWorkspace)return <EmptyState title="Select a workspace"/>;
 const empty=items.length===0&&drafts.length===0;
 return <div className="pageStack scriptsPage codeWorkspacePage"><WorkspaceCommandBar view="code"><div className="codeToolbarMeta"><span>{items.length+drafts.length} block{items.length+drafts.length===1?"":"s"}</span></div><button type="button" className="codeNewBlockButton" onClick={()=>addBlock()} title="Add code block" aria-label="Add code block"><Icon name="plus" size={15}/><span>New block</span></button></WorkspaceCommandBar>
  {undo?<div className="scriptUndoBar"><span>Block deleted. {undo.affected.length?`${undo.affected.length} dependent block(s) highlighted.`:""}</span><button type="button" onClick={undoDelete}>Undo change</button></div>:null}
  <section className="scriptNotebook codeWorkspaceNotebook">
   {empty?<div className="codeEmptyWelcome"><span className="codeEmptyIcon"><Icon name="code" size={22}/></span><strong>Start a code workflow</strong><p>Create a Python, SQL or DAX block. Keep reusable analysis logic together with the workspace.</p></div>:null}
   {items.map((x,i)=><SavedCell key={x.id} item={x} index={i} onReload={load} onDelete={removeSaved} onAddNext={addBlock} dependent={dependentIds.includes(x.id)}/>)}
   {drafts.map((draft,index)=>{const meta=<><div className="notebookExecutionMeta"><span>Draft</span></div><button type="button" className="notebookDelete inlineDelete" title="Remove draft" aria-label="Remove draft" onClick={()=>setDrafts(c=>c.filter(d=>d.id!==draft.id))}>×</button></>;return <article className="notebookCell notebookDraftCell streamlinedNotebookCell" key={draft.id}><div className="notebookPromptVisible">In [{items.length+index+1}]</div><div className="notebookCellBody"><ScriptWorkbench language={draft.language} onLanguage={language=>patchDraft(draft.id,{language,validation:null})} code={draft.code} onCode={code=>patchDraft(draft.id,{code,validation:null})} onCommit={opts=>commitDraft(draft,opts)} busy={draft.busy} validation={draft.validation} toolbarEnd={meta} autoFocus/></div></article>})}
   {!empty?<button type="button" className="notebookAddZone compactAddZone" onClick={()=>addBlock(drafts.at(-1)?.language||items.at(-1)?.language||"PYTHON")}><Icon name="plus" size={16}/><span>Add code block</span></button>:null}
  </section>
 </div>
}
