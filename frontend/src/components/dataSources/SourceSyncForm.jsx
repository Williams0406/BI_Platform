"use client";

import {useMemo,useState} from "react";

export default function SourceSyncForm({workspaceId,source,table,onSubmit,onCancel,isSaving}){
 const[targetName,setTargetName]=useState((table?.table_name||"imported_table").replace(/[^A-Za-z0-9_]+/g,"_").toLowerCase());
 const candidates=useMemo(()=>(table?.fields||[]).filter(f=>["DATE","DATETIME","DATETIME_TZ","INTEGER","BIGINT"].includes(f.logical_type)),[table]);
 const preferred=candidates.find(f=>["updated_at","modified_at","last_updated","updated","modified"].includes(String(f.name).toLowerCase()))||null;
 function submit(e){e.preventDefault();onSubmit({workspace:workspaceId,source_data_source:source.id,source_table:table.id,target_table_name:targetName.trim(),strategy:preferred?"INCREMENTAL":"FULL",schedule:"HOURLY",custom_interval_minutes:60,incremental_field:preferred?.name||"",enabled:true})}
 return <form className="sourceSyncForm" onSubmit={submit}><div className="syncFlowStrip"><span>{source.name}</span><b>→</b><span>Platform Copy</span></div><label className="field"><span>Name</span><input value={targetName} onChange={e=>setTargetName(e.target.value)} required/><small>Synchronization is managed automatically. Platform uses incremental synchronization when a suitable change cursor is available; otherwise it performs a full synchronization.</small></label><div className="formActions"><button type="button" className="button secondaryButton" onClick={onCancel}>Cancel</button><button className="button primaryButton" disabled={isSaving||!targetName.trim()}>{isSaving?"Connecting…":"Import to Platform"}</button></div></form>
}
