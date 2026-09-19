"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import MetricQueryPanel from "@/components/metrics/MetricQueryPanel";
import Alert from "@/components/ui/Alert";
import Spinner from "@/components/ui/Spinner";
import { getCatalogTable } from "@/lib/services/dataModel";
import { getMetric, getSemanticModel } from "@/lib/services/metrics";
import { getApiErrorMessage } from "@/lib/utils/errors";
export default function MetricDetailPage(){const {id}=useParams(); const [metric,setMetric]=useState(null); const [model,setModel]=useState(null); const [table,setTable]=useState(null); const [loading,setLoading]=useState(true); const [error,setError]=useState(""); useEffect(()=>{async function load(){setLoading(true);try{const m=await getMetric(id);setMetric(m);const sm=await getSemanticModel(m.semantic_model);setModel(sm);setTable(await getCatalogTable(sm.base_table));}catch(e){setError(getApiErrorMessage(e));}finally{setLoading(false);}}if(id)load();},[id]); if(loading)return <Spinner label="Cargando métrica..."/>; if(error)return <Alert type="error">{error}</Alert>; if(!metric)return null; return <div className="pageStack"><header className="pageHeader pageHeaderActions"><div><p className="eyebrow">Metric Query</p><h1>{metric.name}</h1><p>{metric.description||"Consulta y valida la métrica antes de utilizarla en Analytics."}</p></div><Link className="button secondaryButton" href="/app/metrics">Volver</Link></header><section className="card"><div className="detailGrid"><div><span>Semantic Model</span><strong>{model?.name||metric.semantic_model}</strong></div><div><span>Expresión</span><strong>{metric.expression_type} · {metric.aggregation}</strong></div><div><span>Formato</span><strong>{metric.format_type}{metric.unit?` · ${metric.unit}`:""}</strong></div><div><span>Cache TTL</span><strong>{metric.cache_ttl_seconds}s</strong></div></div>{metric.expression_type==="SQL"&&<pre className="codeBlock">{metric.expression}</pre>}</section><MetricQueryPanel metric={metric} model={model} table={table}/></div>;}
