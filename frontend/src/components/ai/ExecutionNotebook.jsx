"use client";
import {useEffect,useState} from "react";
import ScriptWorkbench from "@/components/data/ScriptWorkbench";
import {analyzeScript,createScriptBlock,deleteScriptBlock,listScriptBlocks,promoteScriptVariable} from "@/lib/services/scripts";
import {getApiErrorMessage} from "@/lib/utils/errors";
const listValue=d=>Array.isArray(d)?d:d?.results||[];
export default function ExecutionNotebook({workspaceId,kind,objectId,canWrite=true,onError=()=>{},onMessage=()=>{}}){
 const [blocks,setBlocks]=useState([]),[language,setLanguage]=useState("PYTHON"),[code,setCode]=useState(""),[adding,setAdding]=useState(false);
 const objectType=kind==="ML"?"ML_MODEL":"OPTIMIZATION";
 async function load(){if(!workspaceId||!objectId)return;try{const data=await listScriptBlocks(workspaceId);setBlocks(listValue(data).filter(x=>x.linked_object_type===objectType&&String(x.linked_object_id)===String(objectId)).sort((a,b)=>(a.context?.order??0)-(b.context?.order??0)));}catch(e){onError(getApiErrorMessage(e));}}
 useEffect(()=>{load();},[workspaceId,objectId]);
 async function commit(){if(!code.trim())return;try{await analyzeScript(language,code);await createScriptBlock({workspace:workspaceId,name:`Block ${blocks.length+1}`,language,purpose:kind,code,context:{section:kind==="ML"?"machine-learning":"optimization",order:blocks.length+1},linked_object_type:objectType,linked_object_id:String(objectId),status:"SAVED"});setCode("");setAdding(false);onMessage("Code block saved.");await load();}catch(e){onError(getApiErrorMessage(e));}}
 async function remove(id){try{await deleteScriptBlock(id);await load();}catch(e){onError(getApiErrorMessage(e));}}
 async function promote(block,artifact){try{await promoteScriptVariable(block.id,artifact.id);onMessage(`${artifact.name} is now a metric artifact.`);await load();}catch(e){onError(getApiErrorMessage(e));}}
 return <section className="card executionNotebook"><div className="cardHeader"><div><h2>Notebook</h2><p>Segment the model into ordered code blocks. Assigning <code>table["new_column"] = ...</code> creates a field rule.</p></div>{canWrite&&!adding&&<button className="button primaryButton smallButton" onClick={()=>setAdding(true)}>+ Code</button>}</div>
  <div className="notebookBlocks">{blocks.map((b,i)=><article className="notebookBlock" key={b.id}><header><span className="notebookIndex">{String(i+1).padStart(2,"0")}</span><div><strong>{b.name}</strong><small>{b.language} · {b.status}</small></div>{canWrite&&<button className="iconButton" title="Delete block" onClick={()=>remove(b.id)}>×</button>}</header><pre className="notebookCode"><code>{b.code}</code></pre>{b.artifacts?.length>0&&<div className="notebookOutputs">{b.artifacts.map(a=><div className="notebookOutput" key={a.id}><span><strong>{a.name||a.artifact_type}</strong><small>{a.artifact_type.replaceAll("_"," ")}</small></span>{a.artifact_type==="VARIABLE"&&a.metadata?.metric_candidate&&canWrite&&<button className="button secondaryButton smallButton" onClick={()=>promote(b,a)}>+ Metric</button>}</div>)}</div>}</article>)}</div>
  {adding&&<div className="notebookComposer"><ScriptWorkbench language={language} onLanguage={setLanguage} code={code} onCode={setCode} onCommit={commit}/><button className="button secondaryButton smallButton" onClick={()=>{setAdding(false);setCode("")}}>Cancel</button></div>}
  {!blocks.length&&!adding&&<div className="notebookEmpty">No code blocks yet. Add blocks for data preparation, model definition, training, constraints, solving and results.</div>}
 </section>;
}
