"use client";
import { useMemo, useState } from "react";
import Alert from "@/components/ui/Alert";
import Spinner from "@/components/ui/Spinner";
import { queryMetric } from "@/lib/services/metrics";
import { getApiErrorMessage } from "@/lib/utils/errors";
const OPS=["eq","ne","gt","gte","lt","lte","contains","in"];
function formatValue(value, metric){ if(value===null||value===undefined)return "—"; const n=Number(value); if(Number.isNaN(n)) return String(value); const dp=metric.decimal_places??2; if(metric.format_type==="PERCENT") return `${(n*100).toFixed(dp)}%`; if(metric.format_type==="INTEGER") return Math.round(n).toLocaleString(); const base=n.toLocaleString(undefined,{minimumFractionDigits:dp,maximumFractionDigits:dp}); return metric.unit ? `${metric.unit} ${base}` : base; }
export default function MetricQueryPanel({ metric, model, table }) {
 const [dimensions,setDimensions]=useState([]); const [filters,setFilters]=useState([]); const [limit,setLimit]=useState(1000); const [useCache,setUseCache]=useState(true); const [result,setResult]=useState(null); const [loading,setLoading]=useState(false); const [error,setError]=useState("");
 const available=model?.dimensions||[]; const fields=table?.fields||[];
 function toggle(id){setDimensions(v=>v.includes(id)?v.filter(x=>x!==id):[...v,id]);}
 function addFilter(){setFilters(v=>[...v,{field:fields[0]?.name||"",operator:"eq",value:""}]);}
 function changeFilter(i,k,v){setFilters(list=>list.map((x,idx)=>idx===i?{...x,[k]:v}:x));}
 async function run(){setLoading(true);setError("");try{const normalized=filters.filter(f=>f.field).map(f=>({...f,value:f.operator==="in"?String(f.value).split(",").map(x=>x.trim()).filter(Boolean):f.value})); setResult(await queryMetric(metric.id,{dimensions,filters:normalized,limit:Number(limit),use_cache:useCache}));}catch(e){setError(getApiErrorMessage(e));}finally{setLoading(false);}}
 const columns=useMemo(()=>result?.rows?.length?Object.keys(result.rows[0]):[],[result]);
 return <div className="pageStack">
  <section className="card"><div className="cardHeader"><div><h2>Consulta semántica</h2><p>Selecciona dimensiones y filtros; el backend genera el GROUP BY y la expresión de la métrica.</p></div></div>
   {error&&<Alert type="error">{error}</Alert>}
   <div className="metricDimensionPicker"><strong>Dimensiones</strong><div className="chipList">{available.map(d=><button type="button" key={d.id} className={`chipButton ${dimensions.includes(d.id)?"activeChip":""}`} onClick={()=>toggle(d.id)}>{d.name}</button>)}</div></div>
   <div className="queryToolbar"><label>Limit <select value={limit} onChange={e=>setLimit(e.target.value)}><option>100</option><option>1000</option><option>5000</option></select></label><label className="checkField"><input type="checkbox" checked={useCache} onChange={e=>setUseCache(e.target.checked)} /> Usar caché</label><button type="button" className="button secondaryButton" onClick={addFilter}>Agregar filtro</button><button type="button" className="button primaryButton" onClick={run} disabled={loading}>{loading?"Consultando...":"Ejecutar consulta"}</button></div>
   {filters.length>0&&<div className="filterRows">{filters.map((f,i)=><div className="filterRow" key={i}><select value={f.field} onChange={e=>changeFilter(i,"field",e.target.value)}>{fields.map(field=><option key={field.id} value={field.name}>{field.name}</option>)}</select><select value={f.operator} onChange={e=>changeFilter(i,"operator",e.target.value)}>{OPS.map(op=><option key={op}>{op}</option>)}</select><input value={f.value} onChange={e=>changeFilter(i,"value",e.target.value)} placeholder={f.operator==="in"?"A, B, C":"Valor"}/><button type="button" className="button dangerButton smallButton" onClick={()=>setFilters(v=>v.filter((_,idx)=>idx!==i))}>Quitar</button></div>)}</div>}
  </section>
  {loading?<Spinner label="Consultando métrica..."/>:result&&<section className="card"><div className="cardHeader"><div><h2>Resultado</h2><p>{result.returned} fila(s) · {result.cached?"cache":"consulta nueva"}</p></div>{dimensions.length===0&&result.rows?.[0]&&<div className="metricBigValue">{formatValue(result.rows[0].value,result.metric)}</div>}</div>{dimensions.length>0&&<div className="tableWrap"><table className="dataTable"><thead><tr>{columns.map(c=><th key={c}>{c==="value"?metric.name:(result.dimensions.find(d=>d.id===c)?.name||c)}</th>)}</tr></thead><tbody>{result.rows.map((row,i)=><tr key={i}>{columns.map(c=><td key={c}>{c==="value"?formatValue(row[c],result.metric):String(row[c]??"—")}</td>)}</tr>)}</tbody></table></div>}</section>}
 </div>;
}
