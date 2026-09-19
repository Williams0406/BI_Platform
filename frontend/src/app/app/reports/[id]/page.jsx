"use client";
import Link from "next/link";
import { useEffect,useState } from "react";
import DashboardRenderer from "@/components/analytics/DashboardRenderer";
import Alert from "@/components/ui/Alert";
import Spinner from "@/components/ui/Spinner";
import { getDashboardDataset,getReport } from "@/lib/services/analytics";
import { getApiErrorMessage } from "@/lib/utils/errors";
export default function ReportDetailPage({params}){
 const [id,setId]=useState(null);const [report,setReport]=useState(null);const [data,setData]=useState(null);const [loading,setLoading]=useState(true);const [running,setRunning]=useState(false);const [error,setError]=useState("");
 useEffect(()=>{Promise.resolve(params).then(p=>setId(p.id));},[params]);
 useEffect(()=>{if(!id)return;(async()=>{setLoading(true);setError("");try{setReport(await getReport(id));}catch(e){setError(getApiErrorMessage(e));}finally{setLoading(false);}})();},[id]);
 async function preview(){if(!report?.dashboard)return;setRunning(true);setError("");try{setData(await getDashboardDataset(report.dashboard,{filters:[],use_cache:true}));}catch(e){setError(getApiErrorMessage(e));}finally{setRunning(false);}}
 if(loading)return <Spinner label="Cargando reporte..."/>;if(!report)return <Alert type="error">{error||"Reporte no encontrado."}</Alert>;
 return <div className="pageStack"><header className="pageHeader pageHeaderActions"><div><p className="eyebrow">Report</p><h1>{report.name}</h1><p>{report.description||"Sin descripción"}</p></div><div className="headerActions"><Link className="button secondaryButton" href="/app/reports">Volver</Link>{report.dashboard&&<button type="button" className="button primaryButton" onClick={preview} disabled={running}>{running?"Generando preview...":"Previsualizar dashboard"}</button>}</div></header>{error&&<Alert type="error">{error}</Alert>}
 <section className="card"><div className="detailGrid"><div><span>Formato preferido</span><strong>{report.default_export_format}</strong></div><div><span>Dashboard</span><strong>{report.dashboard?String(report.dashboard).slice(0,8):"No asociado"}</strong></div><div><span>Creado</span><strong>{report.created_at?new Date(report.created_at).toLocaleString():"—"}</strong></div><div><span>Actualizado</span><strong>{report.updated_at?new Date(report.updated_at).toLocaleString():"—"}</strong></div></div><pre className="codeBlock">{JSON.stringify(report.config||{},null,2)}</pre></section>
 {!report.dashboard&&<Alert type="info">Este reporte no tiene Dashboard asociado. Puedes editarlo desde Reports para asignar uno.</Alert>}
 {data&&<section className="card reportPreview"><div className="reportPreviewHeader"><div><small>REPORT PREVIEW</small><h2>{report.name}</h2><p>{report.description}</p></div><strong>{report.default_export_format}</strong></div><DashboardRenderer data={data}/></section>}
 </div>;
}
