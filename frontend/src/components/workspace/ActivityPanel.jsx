"use client";
import { useEffect, useRef, useState } from "react";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { listExecutions } from "@/lib/services/executions";
import { executionLabel, executionTimestamp, formatRelativeTime, normalizeCollection } from "@/lib/utils/activity";

export default function ActivityPanel({open,onClose}){
  const{activeWorkspaceId}=useWorkspace();
  const[items,setItems]=useState([]),[loading,setLoading]=useState(false);
  const closeRef=useRef(null),returnFocusRef=useRef(null);
  useEffect(()=>{if(!open||!activeWorkspaceId)return;setLoading(true);listExecutions({workspace:activeWorkspaceId}).then(v=>setItems(normalizeCollection(v).slice(0,12))).finally(()=>setLoading(false));},[open,activeWorkspaceId]);
  useEffect(()=>{if(!open)return;returnFocusRef.current=document.activeElement;closeRef.current?.focus();const h=e=>{if(e.key==="Escape")onClose();};window.addEventListener("keydown",h);return()=>{window.removeEventListener("keydown",h);returnFocusRef.current?.focus?.();};},[open,onClose]);
  if(!open)return null;
  return <><button type="button" className="activityBackdrop" aria-label="Close activity" onClick={onClose}/><aside className="activityDrawer" role="dialog" aria-modal="true" aria-labelledby="activity-title"><div className="activityHeader"><div><span>Workspace</span><h2 id="activity-title">Activity</h2></div><button ref={closeRef} type="button" className="iconButton" onClick={onClose} aria-label="Close activity">×</button></div><div className="activityList" aria-live="polite" aria-busy={loading}>{loading?<p className="commandEmpty">Loading activity…</p>:null}{!loading&&!items.length?<p className="commandEmpty">No executions yet.</p>:null}{items.map(x=><div className="activityItem" key={x.id}><span aria-hidden="true" className={`activityDot status-${String(x.status||"").toLowerCase()}`}/><div><strong>{executionLabel(x)}</strong><small>{x.status} · {formatRelativeTime(executionTimestamp(x))}</small>{x.progress!=null&&["RUNNING","QUEUED"].includes(x.status)?<span className="miniProgress" role="progressbar" aria-label={`${executionLabel(x)} progress`} aria-valuenow={x.progress} aria-valuemin="0" aria-valuemax="100"><i style={{width:`${x.progress}%`}}/></span>:null}</div></div>)}</div></aside></>
}
