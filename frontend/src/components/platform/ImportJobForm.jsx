"use client";

import { useEffect, useMemo, useState } from "react";
import { inspectImportFile } from "@/lib/services/importExport";
import { normalizeTechnicalName, tableLabel } from "@/lib/tableIdentity";

const DESTINATIONS = [
  { value: "CREATE", label: "Create new table" },
  { value: "APPEND", label: "Append" },
  { value: "REPLACE", label: "Replace" },
  { value: "UPSERT", label: "Upsert" },
];

function normalized(value){return normalizeTechnicalName(value).replace(/_/g,"");}

export default function ImportJobForm({ workspaceId, tables, onSubmit, isSaving }) {
  const [file,setFile]=useState(null),[mode,setMode]=useState("CREATE"),[name,setName]=useState(""),[tableId,setTableId]=useState("");
  const [inspection,setInspection]=useState(null),[sheet,setSheet]=useState(""),[mapping,setMapping]=useState({}),[inspecting,setInspecting]=useState(false),[inspectError,setInspectError]=useState("");
  const selectedTable=useMemo(()=>tables.find(t=>t.id===tableId),[tables,tableId]);
  const sourceColumns=inspection?.columns||[];

  async function inspect(nextFile,nextSheet=""){
    if(!nextFile)return;
    setInspecting(true);setInspectError("");
    try{
      const fd=new FormData();fd.append("file",nextFile);if(nextSheet)fd.append("sheet_name",nextSheet);
      const result=await inspectImportFile(fd);setInspection(result);setSheet(result.selected_sheet||"");
    }catch(e){setInspectError(e?.response?.data?.detail||"Could not inspect this file.");}finally{setInspecting(false)}
  }
  async function chooseFile(nextFile){setFile(nextFile);setInspection(null);setMapping({});if(nextFile&&!name)setName(nextFile.name.replace(/\.[^.]+$/, ""));await inspect(nextFile)}
  async function chooseSheet(value){setSheet(value);setMapping({});await inspect(file,value)}

  useEffect(()=>{
    if(mode==="CREATE"||!selectedTable||!sourceColumns.length){setMapping({});return;}
    const target=selectedTable.fields||[];const next={};
    sourceColumns.forEach(src=>{const exact=target.find(f=>f.name===src)||target.find(f=>normalized(f.name)===normalized(src));if(exact)next[src]=exact.name;});
    setMapping(next);
  },[mode,tableId,inspection?.selected_sheet]); // eslint-disable-line react-hooks/exhaustive-deps

  function submit(e){e.preventDefault();if(!file)return;const fd=new FormData();fd.append("workspace",workspaceId);fd.append("file",file);fd.append("file_type",file.name.toLowerCase().endsWith(".xlsx")?"XLSX":"CSV");fd.append("mode",mode);
    if(mode==="CREATE"){if(!name.trim())return;fd.append("target_table_name",normalizeTechnicalName(name));}
    else {if(!tableId)return;fd.append("target_table",tableId);fd.append("column_mapping",JSON.stringify(mapping));}
    if(sheet)fd.append("sheet_name",sheet);onSubmit(fd);
  }
  return <form className="importStudioForm" onSubmit={submit}>
    <div className="importDropCard"><input id="managed-import-file" type="file" accept=".csv,.xlsx" className="srOnly" onChange={e=>chooseFile(e.target.files?.[0]||null)}/><label htmlFor="managed-import-file" className="importDropTarget"><span className="importDropIcon">⇧</span><strong>{file?.name||"Choose CSV or Excel file"}</strong><small>CSV · Excel (.xlsx)</small><span className="button secondaryButton smallButton">Browse file</span></label></div>
    <section className="importConfigSection"><div className="destinationChoiceGrid">{DESTINATIONS.map(item=><button type="button" key={item.value} className={`destinationChoice ${mode===item.value?"selected":""}`} onClick={()=>setMode(item.value)}><span className="dataSourceModeRadio"/><strong>{item.label}</strong></button>)}</div>
      {mode==="CREATE"?<label className="field"><span>Name</span><input value={name} onChange={e=>setName(e.target.value)} placeholder="Ventas 2026" required/><small className="technicalNamePreview">Technical name: <strong>{normalizeTechnicalName(name)||"—"}</strong></small></label>:<label className="field"><span>Platform table</span><select value={tableId} onChange={e=>setTableId(e.target.value)} required><option value="">Select table…</option>{tables.map(t=><option key={t.id} value={t.id}>{tableLabel(t)}</option>)}</select></label>}
      {inspection?.sheets?.length>0&&<label className="field"><span>Excel sheet</span><select value={sheet} onChange={e=>chooseSheet(e.target.value)}>{inspection.sheets.map(s=><option key={s} value={s}>{s}</option>)}</select></label>}
      {inspectError&&<p className="errorText">{inspectError}</p>}{inspecting&&<p className="fieldHint">Reading file…</p>}
      {mode!=="CREATE"&&selectedTable&&sourceColumns.length>0&&<div className="columnMappingStudio"><h3>Column mapping</h3><div className="mappingRows">{sourceColumns.map(src=><div className="mappingRow" key={src}><span>{src}</span><span>→</span><select value={mapping[src]||""} onChange={e=>setMapping(v=>({...v,[src]:e.target.value}))}><option value="">Do not import</option>{(selectedTable.fields||[]).map(f=><option key={f.id||f.name} value={f.name}>{f.name}</option>)}</select></div>)}</div></div>}
      {mode==="UPSERT"&&selectedTable&&<div className="field"><span>Match rows using</span><strong>{selectedTable.primary_key_field||selectedTable.primary_key||"Platform table primary key"}</strong><small>Upsert uses the table primary key to update matches and insert new rows.</small></div>}
      {inspection?.rows?.length>0&&<div className="tableWrap importInlinePreview"><table className="dataTable"><thead><tr>{sourceColumns.map(c=><th key={c}>{c}</th>)}</tr></thead><tbody>{inspection.rows.slice(0,8).map((r,i)=><tr key={i}>{sourceColumns.map(c=><td key={c}>{r[c]==null?"NULL":String(r[c])}</td>)}</tr>)}</tbody></table></div>}
    </section>
    <div className="formActions importFormActions"><button className="button primaryButton" disabled={isSaving||!file||inspecting}>{isSaving?"Uploading…":"Upload and preview"}</button></div>
  </form>
}
