"use client";

import { useEffect, useState } from "react";

export default function DatasetForm({ workspaceId, tables, initialValue, onSubmit, onCancel, isSaving }) {
  const [form, setForm] = useState({ name:"", description:"", source_table:"", filter_config:"[]", sample_limit:"", enabled:true });
  useEffect(()=>setForm({
    name:initialValue?.name||"",
    description:initialValue?.description||"",
    source_table:initialValue?.source_table||tables?.[0]?.id||"",
    filter_config:JSON.stringify(initialValue?.filter_config||[],null,2),
    sample_limit:initialValue?.sample_limit??"",
    enabled:initialValue?.enabled??true,
  }),[initialValue,tables]);
  function set(k,v){setForm(o=>({...o,[k]:v}));}
  function submit(e){
    e.preventDefault();
    let filterConfig=[];
    try{filterConfig=JSON.parse(form.filter_config||"[]");}catch{window.alert("filter_config debe ser JSON válido.");return;}
    onSubmit({workspace:workspaceId,name:form.name,description:form.description,source_table:form.source_table,filter_config:filterConfig,sample_limit:form.sample_limit===""?null:Number(form.sample_limit),enabled:form.enabled});
  }
  return <form className="formGrid" onSubmit={submit}>
    <label className="fieldGroup"><span>Nombre</span><input value={form.name} onChange={e=>set("name",e.target.value)} required /></label>
    <label className="fieldGroup"><span>Tabla fuente</span><select value={form.source_table} onChange={e=>set("source_table",e.target.value)} required><option value="">Seleccionar</option>{tables.map(t=><option key={t.id} value={t.id}>{t.technical_name||t.table_name}</option>)}</select></label>
    <label className="fieldGroup fullWidth"><span>Descripción</span><textarea rows="2" value={form.description} onChange={e=>set("description",e.target.value)} /></label>
    <label className="fieldGroup"><span>Sample limit</span><input type="number" min="1" value={form.sample_limit} onChange={e=>set("sample_limit",e.target.value)} placeholder="Sin límite" /></label>
    <label className="checkField"><input type="checkbox" checked={form.enabled} onChange={e=>set("enabled",e.target.checked)} /> Habilitado</label>
    <label className="fieldGroup fullWidth"><span>Filter config (JSON)</span><textarea className="codeArea" rows="4" value={form.filter_config} onChange={e=>set("filter_config",e.target.value)} /><small>El modelo backend conserva este metadata, pero la implementación actual de dataset_to_dataframe todavía no aplica filter_config al SQL.</small></label>
    <div className="formActions fullWidth"><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button><button type="submit" className="button primaryButton" disabled={isSaving}>{isSaving?"Guardando...":"Guardar"}</button></div>
  </form>;
}
