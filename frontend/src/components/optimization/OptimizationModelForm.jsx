"use client";
import {useEffect,useState} from "react";
export default function OptimizationModelForm({workspaceId,initialValue,onSubmit,onCancel,isSaving}){
 const [f,setF]=useState({name:"",description:"",problem_type:"MILP",enabled:true});
 useEffect(()=>setF({name:initialValue?.name||"",description:initialValue?.description||"",problem_type:initialValue?.problem_type||"MILP",enabled:initialValue?.enabled??true}),[initialValue]);
 const set=(k,v)=>setF(o=>({...o,[k]:v}));
 return <form className="formGrid" onSubmit={e=>{e.preventDefault();onSubmit({workspace:workspaceId,...f});}}>
  <label className="fieldGroup"><span>Nombre</span><input required value={f.name} onChange={e=>set("name",e.target.value)}/></label>
  <label className="fieldGroup"><span>Tipo de problema</span><select value={f.problem_type} onChange={e=>set("problem_type",e.target.value)}><option value="LP">LP — Linear Programming</option><option value="MILP">MILP — Mixed Integer Linear Programming</option></select></label>
  <label className="fieldGroup fullWidth"><span>Descripción</span><textarea rows="3" value={f.description} onChange={e=>set("description",e.target.value)}/></label>
  <label className="checkField"><input type="checkbox" checked={f.enabled} onChange={e=>set("enabled",e.target.checked)}/> Habilitado</label>
  <div className="formActions fullWidth"><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button><button type="submit" className="button primaryButton" disabled={isSaving}>{isSaving?"Guardando...":"Guardar"}</button></div>
 </form>;
}