"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import DimensionForm from "@/components/metrics/DimensionForm";
import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { getCatalogTable } from "@/lib/services/dataModel";
import { createDimension, deleteDimension, getSemanticModel, updateDimension } from "@/lib/services/metrics";
import { getApiErrorMessage } from "@/lib/utils/errors";
const WRITE_ROLES=["OWNER","ADMIN","BUILDER"];
export default function SemanticModelDetailPage(){
 const {id}=useParams(); const {activeWorkspace,organizations}=useWorkspace(); const [model,setModel]=useState(null); const [table,setTable]=useState(null); const [loading,setLoading]=useState(true); const [error,setError]=useState(""); const [message,setMessage]=useState(""); const [show,setShow]=useState(false); const [editing,setEditing]=useState(null); const [saving,setSaving]=useState(false);
 const org=useMemo(()=>organizations.find(x=>x.id===activeWorkspace?.organization),[organizations,activeWorkspace]); const canWrite=WRITE_ROLES.includes(org?.current_user_role);
 async function load(){setLoading(true);setError("");try{const m=await getSemanticModel(id);setModel(m);setTable(await getCatalogTable(m.base_table));}catch(e){setError(getApiErrorMessage(e));}finally{setLoading(false);}}
 useEffect(()=>{if(id)load();},[id]);
 async function save(payload){setSaving(true);setError("");try{if(editing){await updateDimension(editing.id,payload);setMessage("Dimensión actualizada.");}else{await createDimension(payload);setMessage("Dimensión creada.");}setShow(false);setEditing(null);await load();}catch(e){setError(getApiErrorMessage(e));}finally{setSaving(false);}}
 async function remove(item){if(!confirm(`¿Eliminar la dimensión "${item.name}"?`))return;try{await deleteDimension(item.id);setMessage("Dimensión eliminada.");await load();}catch(e){setError(getApiErrorMessage(e));}}
 if(loading)return <Spinner label="Cargando Semantic Model..."/>; if(error&&!model)return <Alert type="error">{error}</Alert>; if(!model)return <EmptyState title="Semantic Model no encontrado"/>;
 return <div className="pageStack"><header className="pageHeader pageHeaderActions"><div><p className="eyebrow">Semantic Model</p><h1>{model.name}</h1><p>{model.description||"Sin descripción"}</p></div><div className="headerActions"><Link className="button secondaryButton" href="/app/metrics">Volver</Link>{canWrite&&<button type="button" className="button primaryButton" onClick={()=>{setEditing(null);setShow(true);}}>Nueva dimensión</button>}</div></header>{error&&<Alert type="error">{error}</Alert>}{message&&<Alert type="success">{message}</Alert>}
 <section className="card"><div className="detailGrid"><div><span>Tabla base</span><strong>{table?table.table_name:model.base_table}</strong></div><div><span>Campos</span><strong>{table?.fields?.length||0}</strong></div><div><span>Dimensiones</span><strong>{model.dimensions?.length||0}</strong></div><div><span>Métricas</span><strong>{model.metrics?.length||0}</strong></div></div></section>
 {show&&<section className="card"><div className="cardHeader"><div><h2>{editing?"Editar dimensión":"Nueva dimensión"}</h2><p>Una dimensión solo puede utilizar campos de la tabla base de este modelo.</p></div></div><DimensionForm semanticModelId={model.id} fields={table?.fields||[]} initialValue={editing} onSubmit={save} onCancel={()=>{setShow(false);setEditing(null);}} isSaving={saving}/></section>}
 <section className="card"><div className="cardHeader"><div><h2>Dimensiones</h2><p>Campos de negocio disponibles para segmentar las consultas.</p></div></div>{!model.dimensions?.length?<EmptyState title="Sin dimensiones" description="Puedes consultar una métrica sin dimensión para obtener un KPI agregado, o crear dimensiones para GROUP BY."/>:<div className="tableWrap"><table className="dataTable"><thead><tr><th>Nombre</th><th>Campo</th><th>Tipo</th><th>Formato</th><th>Hierarchy</th><th>Orden</th><th>Acciones</th></tr></thead><tbody>{model.dimensions.map(d=><tr key={d.id}><td><strong>{d.name}</strong></td><td>{d.field_name}<div className="mutedText">{d.logical_type}</div></td><td>{d.dimension_type}</td><td>{d.format||"—"}</td><td><code>{JSON.stringify(d.hierarchy||[])}</code></td><td>{d.sort_order}</td><td>{canWrite&&<div className="tableActions"><button type="button" className="button secondaryButton smallButton" onClick={()=>{setEditing(d);setShow(true);}}>Editar</button><button type="button" className="button dangerButton smallButton" onClick={()=>remove(d)}>Eliminar</button></div>}</td></tr>)}</tbody></table></div>}</section>
 <section className="card"><div className="cardHeader"><div><h2>Métricas del modelo</h2><p>{model.metrics?.length||0} definición(es)</p></div></div>{!model.metrics?.length?<EmptyState title="Sin métricas" description="Crea métricas desde la pantalla principal de Metrics."/>:<div className="metricCards">{model.metrics.map(m=><Link href={`/app/metrics/${m.id}`} className="metricCard" key={m.id}><span>{m.format_type}</span><strong>{m.name}</strong><small>{m.expression_type} · {m.aggregation}</small></Link>)}</div>}</section></div>;
}
