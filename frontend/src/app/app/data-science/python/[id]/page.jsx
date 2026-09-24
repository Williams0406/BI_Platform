"use client";

import Link from "next/link";
import { use, useEffect, useMemo, useState } from "react";

import PythonInputForm from "@/components/dataScience/PythonInputForm";
import ExecutionStatus from "@/components/logic/ExecutionStatus";
import PrepareTabs from "@/components/prepare/PrepareTabs";
import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { listCatalogTables } from "@/lib/services/dataModel";
import { listDataAssets, listDataSources } from "@/lib/services/dataSources";
import { addPythonTransformationInput, getPythonTransformation, runPythonTransformation } from "@/lib/services/dataScience";
import { getExecution } from "@/lib/services/executions";
import { getApiErrorMessage } from "@/lib/utils/errors";

const WRITE_ROLES=["OWNER","ADMIN","BUILDER"];
function listValue(data){return Array.isArray(data)?data:data?.results||[];}
const TERMINAL=new Set(["SUCCESS","FAILED","CANCELLED","BLOCKED"]);

export default function PythonTransformationDetailPage({params}){
  const {id}=use(params);
  const {activeWorkspace,organizations}=useWorkspace();
  const [item,setItem]=useState(null);const [assets,setAssets]=useState([]);const [execution,setExecution]=useState(null);const [loading,setLoading]=useState(true);const [saving,setSaving]=useState(false);const [running,setRunning]=useState(false);const [error,setError]=useState("");const [message,setMessage]=useState("");
  const organization=useMemo(()=>organizations.find(x=>x.id===activeWorkspace?.organization),[organizations,activeWorkspace]);
  const canWrite=WRITE_ROLES.includes(organization?.current_user_role);

  async function load(){setLoading(true);setError("");try{
    const [transformation,sourceData,tableData,assetData]=await Promise.all([getPythonTransformation(id),listDataSources(activeWorkspace?.id),listCatalogTables(),listDataAssets(activeWorkspace?.id)]);
    const managedIds=new Set(listValue(sourceData).filter(s=>s.mode==="MANAGED").map(s=>s.id));
    const tables=listValue(tableData).filter(t=>managedIds.has(t.data_source)&&t.object_type==="TABLE");
    const tabularAssetIds=new Set(tables.map(t=>t.data_asset));
    setItem(transformation);setAssets(listValue(assetData).filter(a=>tabularAssetIds.has(a.id)));
  }catch(e){setError(getApiErrorMessage(e));}finally{setLoading(false);}}
  useEffect(()=>{if(activeWorkspace?.id)load();},[id,activeWorkspace?.id]);

  useEffect(()=>{
    if(!execution?.id||TERMINAL.has(execution.status))return;
    const timer=setInterval(async()=>{try{const updated=await getExecution(execution.id);setExecution(updated);if(TERMINAL.has(updated.status)){await load();setMessage(updated.status==="SUCCESS"?"Transformación Python completada.":`Ejecución finalizada: ${updated.status}`);}}catch{}},2000);
    return()=>clearInterval(timer);
  },[execution?.id,execution?.status]);

  async function addInput(payload){setSaving(true);setError("");try{await addPythonTransformationInput(id,payload);setMessage("Input agregado.");await load();}catch(e){setError(getApiErrorMessage(e));}finally{setSaving(false);}}
  async function run(){setRunning(true);setError("");setMessage("");try{const result=await runPythonTransformation(id);setExecution({id:result.execution_id,status:result.status,progress:0});setMessage("Ejecución enviada a la cola python.");}catch(e){setError(getApiErrorMessage(e));}finally{setRunning(false);}}

  if(loading)return <Spinner label="Cargando transformación Python..."/>;
  if(!item)return <EmptyState title="Transformación no disponible" description={error||"No fue posible cargar la definición."}/>;

  return <div className="pageStack">
    <header className="pageHeader pageHeaderActions"><div><p className="eyebrow">Prepare · Python</p><h1>{item.name}</h1><p>{item.description||"Transformación Python controlada."}</p></div><div className="headerActions"><Link className="button secondaryButton" href="/app/data-science">Volver</Link>{canWrite&&<button type="button" className="button primaryButton" onClick={run} disabled={running||!item.enabled||!item.inputs?.length}>{running?"Encolando...":"Ejecutar"}</button>}</div></header>
    <PrepareTabs />{error&&<Alert type="error">{error}</Alert>}{message&&<Alert type="success">{message}</Alert>}
    {!item.inputs?.length&&<Alert type="info">Agrega al menos un input antes de ejecutar. El backend actual permite agregar inputs pero no eliminarlos individualmente; para redefinirlos completamente debe recrearse la transformación.</Alert>}

    <section className="card"><div className="detailGrid"><div><span>Output name</span><strong>{item.output_name}</strong></div><div><span>Output Asset</span><strong>{item.output_asset?"Generado":"Pendiente"}</strong></div><div><span>Timeout</span><strong>{item.timeout_seconds}s</strong></div><div><span>Memory</span><strong>{item.memory_limit_mb} MB</strong></div><div><span>Max input rows</span><strong>{item.max_input_rows}</strong></div><div><span>Packages</span><strong>{item.allowed_packages?.join(", ")||"base"}</strong></div></div></section>

    <section className="card"><div className="cardHeader"><div><h2>Inputs</h2><p>Cada alias queda disponible mediante table("alias"). Solo se ofrecen Data Assets tabulares MANAGED.</p></div></div>{item.inputs?.length?<div className="chipList">{item.inputs.map(input=><span className="dataChip" key={input.id}><strong>{input.alias}</strong><small>{input.asset_name}</small></span>)}</div>:<p className="mutedText">Sin inputs registrados.</p>}{canWrite&&<div className="sectionDivider"><PythonInputForm assets={assets} existingInputs={item.inputs||[]} onSubmit={addInput} isSaving={saving}/></div>}</section>

    <section className="card"><div className="cardHeader"><div><h2>Código</h2><p>Se ejecuta con Python aislado (-I), import guard y límites del runtime.</p></div></div><pre className="codeBlock">{item.code}</pre></section>

    {execution&&<section className="card"><div className="cardHeader"><div><h2>Ejecución</h2><p>Seguimiento del Execution Engine compartido.</p></div><span className="statusBadge">Execution {execution.id}</span></div><div className="detailGrid"><div><span>Status</span><ExecutionStatus status={execution.status}/></div><div><span>Progress</span><strong>{execution.progress??0}%</strong></div><div><span>Execution ID</span><code>{execution.id}</code></div></div><div className="progressTrack"><div className="progressFill" style={{width:`${Math.max(0,Math.min(100,Number(execution.progress)||0))}%`}}/></div>{execution.result&&<pre className="codeBlock">{JSON.stringify(execution.result,null,2)}</pre>}{execution.error_message&&<Alert type="error">{execution.error_message}</Alert>}</section>}
  </div>;
}
