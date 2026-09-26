"use client";
import {useEffect,useState} from "react";
import {useWorkspace} from "@/lib/hooks/useWorkspace";

export function useMeasureSelection(code,setCode){
 const [metricId,setMetricId]=useState(null);
 const {activeWorkspace}=useWorkspace();
 useEffect(()=>{if(!code)setMetricId(null)},[code]);
 useEffect(()=>{
  const clear=event=>{
   if(String(event.detail.workspace)===String(activeWorkspace?.id)&&(event.detail.deleted_metric_ids||[]).includes(String(metricId))){setCode("");setMetricId(null)}
  };
  window.addEventListener("bi-code-deleted",clear);
  return()=>window.removeEventListener("bi-code-deleted",clear);
 },[activeWorkspace?.id,metricId,setCode]);
 return [metricId,setMetricId];
}
