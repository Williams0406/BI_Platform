"use client";
import { useEffect, useState } from "react";
import Alert from "@/components/ui/Alert";

function text(value, fallback) { try { return JSON.stringify(value ?? fallback, null, 2); } catch { return JSON.stringify(fallback, null, 2); } }
export default function DashboardForm({ workspaceId, initialValue, onSubmit, onCancel, isSaving }) {
  const [name,setName]=useState(""); const [description,setDescription]=useState(""); const [layout,setLayout]=useState("{}"); const [filters,setFilters]=useState("[]"); const [error,setError]=useState("");
  useEffect(()=>{setName(initialValue?.name||"");setDescription(initialValue?.description||"");setLayout(text(initialValue?.layout,{}));setFilters(text(initialValue?.global_filters,[]));setError("");},[initialValue]);
  function submit(e){e.preventDefault();setError("");try{const l=JSON.parse(layout||"{}");const f=JSON.parse(filters||"[]");if(!Array.isArray(f))throw new Error("global_filters debe ser una lista JSON.");onSubmit({workspace:workspaceId,name:name.trim(),description,layout:l,global_filters:f});}catch(err){setError(err.message||"JSON inválido.");}}
  return <form className="formGrid" onSubmit={submit}>{error&&<Alert type="error">{error}</Alert>}<label>Nombre<input value={name} onChange={e=>setName(e.target.value)} required/></label><label className="span2">Descripción<textarea rows="3" value={description} onChange={e=>setDescription(e.target.value)}/></label><label className="span2">Layout JSON<textarea rows="5" value={layout} onChange={e=>setLayout(e.target.value)}/></label><label className="span2">Global filters JSON<textarea rows="5" value={filters} onChange={e=>setFilters(e.target.value)}/></label><div className="formActions span2"><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button><button type="submit" className="button primaryButton" disabled={isSaving}>{isSaving?"Guardando...":"Guardar dashboard"}</button></div></form>;
}
