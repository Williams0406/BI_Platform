"use client";
import {useEffect,useState} from "react";
import {useWorkspace} from "@/lib/hooks/useWorkspace";
import {createScriptBlock,deleteScriptBlock,listScriptBlocks,updateScriptBlock} from "@/lib/services/scripts";
import EmptyState from "@/components/ui/EmptyState";
import ScriptWorkbench from "@/components/data/ScriptWorkbench";
import Icon from "@/components/ui/Icon";

const listValue=v=>Array.isArray(v)?v:v?.results||[];
const newDraft=()=>({id:`draft-${Date.now()}-${Math.random().toString(36).slice(2)}`,language:"PYTHON",code:"",busy:false});

function SavedCell({item,index,onReload,onDelete,onAddNext}){
 const [language,setLanguage]=useState(item.language),[code,setCode]=useState(item.code),[busy,setBusy]=useState(false),[edit,setEdit]=useState(false),[name,setName]=useState(item.name);
 useEffect(()=>{setLanguage(item.language);setCode(item.code);setName(item.name)},[item.id,item.updated_at]);
 async function run({addNext=false}={}){if(!code.trim()||busy)return;setBusy(true);try{await updateScriptBlock(item.id,{language,code,status:"SAVED"});await onReload();if(addNext)onAddNext()}finally{setBusy(false)}}
 async function remove(){if(!window.confirm("Delete this code block?"))return;await onDelete(item.id)}
 function cellKey(e){if((e.ctrlKey||e.metaKey)&&e.shiftKey&&(e.key==="Backspace"||e.key==="Delete")){e.preventDefault();remove()}}
 return <article className="notebookCell" onKeyDown={cellKey}>
   <div className="notebookPrompt">In [{index+1}]</div>
   <div className="notebookCellBody">
    <div className="notebookMeta"><div className="notebookArtifactList">{(item.artifacts||[]).map(a=><span key={a.id||`${a.artifact_type}-${a.name}`}>{a.artifact_type.replaceAll("_"," ")}</span>)}</div>{edit?<input autoFocus value={name} onChange={e=>setName(e.target.value)} onKeyDown={async e=>{if(e.key==="Enter"){await updateScriptBlock(item.id,{name});setEdit(false);onReload()}if(e.key==="Escape")setEdit(false)}} onBlur={()=>setEdit(false)}/>:<strong onDoubleClick={()=>setEdit(true)}>{name}</strong>}<button type="button" className="notebookDelete" aria-label="Delete code block" title="Delete block · Ctrl/Cmd+Shift+Backspace" onClick={remove}>×</button></div>
    <ScriptWorkbench language={language} onLanguage={setLanguage} code={code} onCode={setCode} onCommit={run} busy={busy}/>
   </div>
 </article>
}

export default function ScriptsPage(){
 const {activeWorkspace}=useWorkspace();const [items,setItems]=useState([]),[drafts,setDrafts]=useState([]);
 async function load(){if(activeWorkspace?.id)setItems(listValue(await listScriptBlocks(activeWorkspace.id)))}
 useEffect(()=>{load()},[activeWorkspace?.id]);
 function addBlock(){setDrafts(current=>[...current,newDraft()])}
 function patchDraft(id,patch){setDrafts(current=>current.map(d=>d.id===id?{...d,...patch}:d))}
 async function commitDraft(draft,{addNext=false}={}){if(!activeWorkspace?.id||!draft.code.trim()||draft.busy)return;patchDraft(draft.id,{busy:true});try{await createScriptBlock({workspace:activeWorkspace.id,name:`${draft.language} · ${new Date().toLocaleString()}`,language:draft.language,purpose:"",code:draft.code,context:{section:"notebook"},status:"SAVED"});setDrafts(current=>current.filter(d=>d.id!==draft.id));await load();if(addNext)addBlock()}finally{patchDraft(draft.id,{busy:false})}}
 async function removeSaved(id){await deleteScriptBlock(id);await load()}
 if(!activeWorkspace)return <EmptyState title="Select a workspace"/>;
 return <div className="pageStack scriptsPage"><header className="pageHeader scriptsHeader"><h1>Code</h1><button type="button" className="scriptsAddBlock" onClick={addBlock}><Icon name="plus" size={15}/><span>Code</span></button></header>
  <section className="scriptNotebook">
   {items.map((x,i)=><SavedCell key={x.id} item={x} index={i} onReload={load} onDelete={removeSaved} onAddNext={addBlock}/>)}
   {drafts.map((draft,index)=><article className="notebookCell notebookDraftCell" key={draft.id}><div className="notebookPrompt">In [{items.length+index+1}]</div><div className="notebookCellBody"><div className="draftCellActions"><span>New code block</span><button type="button" title="Remove draft" onClick={()=>setDrafts(c=>c.filter(d=>d.id!==draft.id))}>×</button></div><ScriptWorkbench language={draft.language} onLanguage={language=>patchDraft(draft.id,{language})} code={draft.code} onCode={code=>patchDraft(draft.id,{code})} onCommit={opts=>commitDraft(draft,opts)} busy={draft.busy} autoFocus/></div></article>)}
   <button type="button" className="notebookAddZone" onClick={addBlock}><Icon name="plus" size={16}/><span>Add code block</span><small>Click or use Shift+Enter from the previous block</small></button>
  </section>
 </div>
}
