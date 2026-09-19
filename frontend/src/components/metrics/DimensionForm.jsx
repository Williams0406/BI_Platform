"use client";
import { useEffect, useState } from "react";
const TYPES=["CATEGORY","DATE","DATETIME","NUMBER","TEXT"];
export default function DimensionForm({ semanticModelId, fields, initialValue, onSubmit, onCancel, isSaving }) {
 const [form,setForm]=useState({field:"",name:"",dimension_type:"CATEGORY",format:"",hierarchy:"[]",sort_order:0});
 useEffect(()=>setForm({field:initialValue?.field||fields?.[0]?.id||"",name:initialValue?.name||"",dimension_type:initialValue?.dimension_type||"CATEGORY",format:initialValue?.format||"",hierarchy:JSON.stringify(initialValue?.hierarchy||[],null,2),sort_order:initialValue?.sort_order||0}),[initialValue,fields]);
 function set(k,v){setForm(o=>({...o,[k]:v}));}
 function submit(e){e.preventDefault(); let hierarchy=[]; try{hierarchy=JSON.parse(form.hierarchy||"[]");}catch{alert("Hierarchy debe ser JSON válido.");return;} onSubmit({semantic_model:semanticModelId,field:form.field,name:form.name,dimension_type:form.dimension_type,format:form.format,hierarchy,sort_order:Number(form.sort_order)||0});}
 return <form className="formGrid" onSubmit={submit}>
  <label className="fieldGroup"><span>Campo</span><select value={form.field} onChange={e=>set("field",e.target.value)} required>{fields.map(f=><option key={f.id} value={f.id}>{f.name} · {f.logical_type}</option>)}</select></label>
  <label className="fieldGroup"><span>Nombre de negocio</span><input value={form.name} onChange={e=>set("name",e.target.value)} required /></label>
  <label className="fieldGroup"><span>Tipo</span><select value={form.dimension_type} onChange={e=>set("dimension_type",e.target.value)}>{TYPES.map(x=><option key={x}>{x}</option>)}</select></label>
  <label className="fieldGroup"><span>Formato</span><input value={form.format} onChange={e=>set("format",e.target.value)} placeholder="YYYY-MM, 0.00, etc." /></label>
  <label className="fieldGroup"><span>Orden</span><input type="number" min="0" value={form.sort_order} onChange={e=>set("sort_order",e.target.value)} /></label>
  <label className="fieldGroup fullWidth"><span>Hierarchy JSON</span><textarea className="codeArea" rows="3" value={form.hierarchy} onChange={e=>set("hierarchy",e.target.value)} /></label>
  <div className="formActions fullWidth"><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button><button type="submit" className="button primaryButton" disabled={isSaving}>{isSaving?"Guardando...":"Guardar"}</button></div>
 </form>;
}
