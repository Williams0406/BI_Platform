"use client";
import {useEffect,useState} from "react";
function parseBound(v){if(v==="")return null;if(v.startsWith("$"))return {parameter:v.slice(1)};const n=Number(v);return Number.isNaN(n)?v:n;}
function show(v){if(v==null)return "";return typeof v==="object"?`$${v.parameter}`:String(v);}
export default function VariableForm({modelId,parameters,initialValue,onSubmit,onCancel,isSaving}){
 const [f,setF]=useState({name:"",variable_type:"CONTINUOUS",lower_bound:"0",upper_bound:"",description:""});
 useEffect(()=>setF({name:initialValue?.name||"",variable_type:initialValue?.variable_type||"CONTINUOUS",lower_bound:show(initialValue?.lower_bound??0),upper_bound:show(initialValue?.upper_bound),description:initialValue?.description||""}),[initialValue]); const set=(k,v)=>setF(o=>({...o,[k]:v}));
 return <form className="formGrid" onSubmit={e=>{e.preventDefault();onSubmit({model:modelId,name:f.name,variable_type:f.variable_type,lower_bound:f.lower_bound===""?0:parseBound(f.lower_bound),upper_bound:parseBound(f.upper_bound),description:f.description});}}>
  <label className="fieldGroup"><span>Nombre</span><input required value={f.name} onChange={e=>set("name",e.target.value)} placeholder="x"/></label><label className="fieldGroup"><span>Tipo</span><select value={f.variable_type} onChange={e=>set("variable_type",e.target.value)}><option>CONTINUOUS</option><option>INTEGER</option><option>BINARY</option></select></label>
  <label className="fieldGroup"><span>Lower bound</span><input value={f.lower_bound} onChange={e=>set("lower_bound",e.target.value)} placeholder="0 o $capacity"/><small>Número o $nombre_parametro.</small></label><label className="fieldGroup"><span>Upper bound</span><input value={f.upper_bound} onChange={e=>set("upper_bound",e.target.value)} placeholder="vacío o $capacity"/></label>
  {parameters.length>0&&<div className="fullWidth chipRow">{parameters.map(p=><button type="button" className="chipButton" key={p.id} onClick={()=>set("upper_bound",`$${p.name}`)}>${p.name}</button>)}</div>}
  <label className="fieldGroup fullWidth"><span>Descripción</span><textarea rows="2" value={f.description} onChange={e=>set("description",e.target.value)}/></label><div className="formActions fullWidth"><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button><button type="submit" className="button primaryButton" disabled={isSaving}>Guardar variable</button></div>
 </form>;
}