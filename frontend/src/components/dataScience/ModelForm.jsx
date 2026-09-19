"use client";

import { useEffect, useMemo, useState } from "react";

const ALGORITHMS = {
  CLASSIFICATION: ["LOGISTIC_REGRESSION", "RANDOM_FOREST_CLASSIFIER"],
  REGRESSION: ["LINEAR_REGRESSION", "RANDOM_FOREST_REGRESSOR"],
};

export default function ModelForm({ workspaceId, datasets, tablesById, initialValue, onSubmit, onCancel, isSaving }) {
  const [form,setForm]=useState({dataset:"",name:"",description:"",task_type:"CLASSIFICATION",algorithm:"LOGISTIC_REGRESSION",features:[],target:"",parameters:"{}",test_size:0.2,random_state:42,enabled:true});
  useEffect(()=>setForm({
    dataset:initialValue?.dataset||datasets?.[0]?.id||"",
    name:initialValue?.name||"",
    description:initialValue?.description||"",
    task_type:initialValue?.task_type||"CLASSIFICATION",
    algorithm:initialValue?.algorithm||"LOGISTIC_REGRESSION",
    features:initialValue?.features||[],
    target:initialValue?.target||"",
    parameters:JSON.stringify(initialValue?.parameters||{},null,2),
    test_size:initialValue?.test_size??0.2,
    random_state:initialValue?.random_state??42,
    enabled:initialValue?.enabled??true,
  }),[initialValue,datasets]);
  const dataset=useMemo(()=>datasets.find(d=>d.id===form.dataset),[datasets,form.dataset]);
  const fields=tablesById[dataset?.source_table]?.fields||[];
  const algorithms=ALGORITHMS[form.task_type]||[];
  function set(k,v){setForm(o=>({...o,[k]:v}));}
  function changeTask(value){setForm(o=>({...o,task_type:value,algorithm:ALGORITHMS[value][0]}));}
  function toggleFeature(id){set("features",form.features.includes(id)?form.features.filter(x=>x!==id):[...form.features,id]);}
  function submit(e){
    e.preventDefault();
    let parameters={};
    try{parameters=JSON.parse(form.parameters||"{}");}catch{window.alert("Parameters debe ser JSON válido.");return;}
    if(!form.features.length){window.alert("Selecciona al menos un feature.");return;}
    if(form.features.includes(form.target)){window.alert("El target no puede estar incluido en features.");return;}
    onSubmit({workspace:workspaceId,dataset:form.dataset,name:form.name,description:form.description,task_type:form.task_type,algorithm:form.algorithm,features:form.features,target:form.target,parameters,test_size:Number(form.test_size),random_state:Number(form.random_state),enabled:form.enabled});
  }
  return <form className="formGrid" onSubmit={submit}>
    <label className="fieldGroup"><span>Dataset</span><select value={form.dataset} onChange={e=>{set("dataset",e.target.value);set("features",[]);set("target","");}} required><option value="">Seleccionar</option>{datasets.map(d=><option key={d.id} value={d.id}>{d.name}</option>)}</select></label>
    <label className="fieldGroup"><span>Nombre</span><input value={form.name} onChange={e=>set("name",e.target.value)} required /></label>
    <label className="fieldGroup fullWidth"><span>Descripción</span><textarea rows="2" value={form.description} onChange={e=>set("description",e.target.value)} /></label>
    <label className="fieldGroup"><span>Task</span><select value={form.task_type} onChange={e=>changeTask(e.target.value)}><option value="CLASSIFICATION">CLASSIFICATION</option><option value="REGRESSION">REGRESSION</option></select></label>
    <label className="fieldGroup"><span>Algoritmo</span><select value={form.algorithm} onChange={e=>set("algorithm",e.target.value)}>{algorithms.map(a=><option key={a}>{a}</option>)}</select></label>
    <label className="fieldGroup"><span>Target</span><select value={form.target} onChange={e=>set("target",e.target.value)} required><option value="">Seleccionar</option>{fields.map(f=><option key={f.id} value={f.id}>{f.name} · {f.logical_type}</option>)}</select></label>
    <label className="fieldGroup"><span>Test size</span><input type="number" step="0.05" min="0.05" max="0.5" value={form.test_size} onChange={e=>set("test_size",e.target.value)} /></label>
    <label className="fieldGroup"><span>Random state</span><input type="number" value={form.random_state} onChange={e=>set("random_state",e.target.value)} /></label>
    <label className="checkField"><input type="checkbox" checked={form.enabled} onChange={e=>set("enabled",e.target.checked)} /> Habilitado</label>
    <div className="fieldGroup fullWidth"><span>Features</span><div className="featurePicker">{fields.length?fields.map(f=><label className={`featureOption ${form.features.includes(f.id)?"selectedFeature":""}`} key={f.id}><input type="checkbox" checked={form.features.includes(f.id)} disabled={form.target===f.id} onChange={()=>toggleFeature(f.id)} /><strong>{f.name}</strong><small>{f.logical_type}</small></label>):<small>Selecciona un Dataset para cargar campos.</small>}</div></div>
    <label className="fieldGroup fullWidth"><span>Parámetros sklearn (JSON)</span><textarea className="codeArea" rows="5" value={form.parameters} onChange={e=>set("parameters",e.target.value)} placeholder='{"n_estimators": 200}' /></label>
    <div className="formActions fullWidth"><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button><button type="submit" className="button primaryButton" disabled={isSaving}>{isSaving?"Guardando...":"Guardar modelo"}</button></div>
  </form>;
}
