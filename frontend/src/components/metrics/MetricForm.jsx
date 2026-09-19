"use client";
import { useEffect, useMemo, useState } from "react";
const AGG=["SUM","AVG","MIN","MAX","COUNT","COUNT_DISTINCT","NONE"];
const FORMAT=["NUMBER","INTEGER","PERCENT","CURRENCY","DURATION","CUSTOM"];
export default function MetricForm({ workspaceId, models, tablesById, initialValue, onSubmit, onCancel, isSaving }) {
 const [form,setForm]=useState({semantic_model:"",name:"",description:"",expression_type:"SIMPLE",source_field:"",aggregation:"SUM",expression:"",format_type:"NUMBER",unit:"",decimal_places:2,enabled:true,cache_ttl_seconds:60});
 useEffect(()=>setForm({semantic_model:initialValue?.semantic_model||models?.[0]?.id||"",name:initialValue?.name||"",description:initialValue?.description||"",expression_type:initialValue?.expression_type||"SIMPLE",source_field:initialValue?.source_field||"",aggregation:initialValue?.aggregation||"SUM",expression:initialValue?.expression||"",format_type:initialValue?.format_type||"NUMBER",unit:initialValue?.unit||"",decimal_places:initialValue?.decimal_places??2,enabled:initialValue?.enabled??true,cache_ttl_seconds:initialValue?.cache_ttl_seconds??60}),[initialValue,models]);
 const model=useMemo(()=>models.find(x=>x.id===form.semantic_model),[models,form.semantic_model]); const fields=tablesById[model?.base_table]?.fields||[];
 function set(k,v){setForm(o=>({...o,[k]:v}));}
 function insertField(name){set("expression",`${form.expression}${form.expression?" ":""}{{field:${name}}}`);}
 function submit(e){e.preventDefault(); const payload={workspace:workspaceId,...form,decimal_places:Number(form.decimal_places)||0,cache_ttl_seconds:Number(form.cache_ttl_seconds)||0}; if(form.expression_type==="SIMPLE"&&form.aggregation==="COUNT") payload.source_field=null; if(form.expression_type==="SQL") payload.source_field=form.source_field||null; onSubmit(payload);}
 return <form className="formGrid" onSubmit={submit}>
  <label className="fieldGroup"><span>Semantic Model</span><select value={form.semantic_model} onChange={e=>{set("semantic_model",e.target.value);set("source_field","");}} required><option value="">Seleccionar</option>{models.map(m=><option key={m.id} value={m.id}>{m.name}</option>)}</select></label>
  <label className="fieldGroup"><span>Nombre</span><input value={form.name} onChange={e=>set("name",e.target.value)} required /></label>
  <label className="fieldGroup fullWidth"><span>Descripción</span><textarea rows="2" value={form.description} onChange={e=>set("description",e.target.value)} /></label>
  <label className="fieldGroup"><span>Tipo de expresión</span><select value={form.expression_type} onChange={e=>set("expression_type",e.target.value)}><option>SIMPLE</option><option>SQL</option></select></label>
  <label className="fieldGroup"><span>Agregación</span><select value={form.aggregation} onChange={e=>set("aggregation",e.target.value)}>{AGG.map(x=><option key={x}>{x}</option>)}</select></label>
  <label className="fieldGroup"><span>Campo fuente</span><select value={form.source_field||""} onChange={e=>set("source_field",e.target.value)} disabled={form.expression_type==="SIMPLE"&&form.aggregation==="COUNT"}><option value="">Sin campo</option>{fields.map(f=><option key={f.id} value={f.id}>{f.name} · {f.logical_type}</option>)}</select></label>
  <label className="fieldGroup"><span>Formato</span><select value={form.format_type} onChange={e=>set("format_type",e.target.value)}>{FORMAT.map(x=><option key={x}>{x}</option>)}</select></label>
  {form.expression_type==="SQL"&&<div className="fieldGroup fullWidth"><span>Expresión SQL (no sentencia completa)</span><textarea className="codeArea" rows="4" value={form.expression} onChange={e=>set("expression",e.target.value)} placeholder="SUM({{field:amount}}) / NULLIF(COUNT(*), 0)" /><div className="chipList">{fields.map(f=><button type="button" className="chipButton" key={f.id} onClick={()=>insertField(f.name)}>{f.name}</button>)}</div></div>}
  <label className="fieldGroup"><span>Unidad</span><input value={form.unit} onChange={e=>set("unit",e.target.value)} placeholder="S/, USD, kg, h..." /></label>
  <label className="fieldGroup"><span>Decimales</span><input type="number" min="0" max="10" value={form.decimal_places} onChange={e=>set("decimal_places",e.target.value)} /></label>
  <label className="fieldGroup"><span>Cache TTL (seg.)</span><input type="number" min="0" value={form.cache_ttl_seconds} onChange={e=>set("cache_ttl_seconds",e.target.value)} /></label>
  <label className="checkField"><input type="checkbox" checked={form.enabled} onChange={e=>set("enabled",e.target.checked)} /> Habilitada</label>
  <div className="formActions fullWidth"><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button><button type="submit" className="button primaryButton" disabled={isSaving}>{isSaving?"Guardando...":"Guardar"}</button></div>
 </form>;
}
