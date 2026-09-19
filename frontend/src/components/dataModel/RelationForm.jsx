"use client";
import {useMemo,useState} from "react";
export default function RelationForm({tables=[],onSubmit,onCancel,isSaving}){
 const [sourceId,setSourceId]=useState(tables[0]?.id||""),[targetId,setTargetId]=useState(""),[sourceColumn,setSourceColumn]=useState(""),[targetColumn,setTargetColumn]=useState(""),[name,setName]=useState("");
 const source=useMemo(()=>tables.find(t=>String(t.id)===String(sourceId)),[tables,sourceId]);
 const compatible=tables.filter(t=>String(t.id)!==String(sourceId)&&String(t.data_source)===String(source?.data_source));
 const target=compatible.find(t=>String(t.id)===String(targetId));
 function submit(e){e.preventDefault();if(!source||!target||!sourceColumn||!targetColumn)return;onSubmit({name:name.trim()||`fk_${source.table_name}_${target.table_name}_${sourceColumn}`,data_source:source.data_source,source_table:source.id,target_table:target.id,source_columns:[sourceColumn],target_columns:[targetColumn]});}
 return <form className="relationDesignerForm" onSubmit={submit}>
  <p className="mutedText">Create a relationship between cataloged tables from the same source. For managed tables this becomes part of the model metadata used by the platform.</p>
  <label className="field">Relationship name<input value={name} onChange={e=>setName(e.target.value)} placeholder="Optional · generated automatically"/></label>
  <div className="relationDesignerGrid">
   <section><span className="eyebrow">FROM</span><label className="field">Table<select value={sourceId} onChange={e=>{setSourceId(e.target.value);setTargetId("");setSourceColumn("");setTargetColumn("")}}>{tables.map(t=><option key={t.id} value={t.id}>{t.technical_name||t.table_name}</option>)}</select></label><label className="field">Column<select value={sourceColumn} onChange={e=>setSourceColumn(e.target.value)}><option value="">Select column</option>{(source?.fields||[]).map(f=><option key={f.id} value={f.name}>{f.name} · {f.logical_type}</option>)}</select></label></section>
   <div className="relationArrow">→</div>
   <section><span className="eyebrow">TO</span><label className="field">Table<select value={targetId} onChange={e=>{setTargetId(e.target.value);setTargetColumn("")}}><option value="">Select table</option>{compatible.map(t=><option key={t.id} value={t.id}>{t.technical_name||t.table_name}</option>)}</select></label><label className="field">Column<select value={targetColumn} onChange={e=>setTargetColumn(e.target.value)}><option value="">Select column</option>{(target?.fields||[]).map(f=><option key={f.id} value={f.name}>{f.name} · {f.logical_type}</option>)}</select></label></section>
  </div>
  <div className="formActions"><button className="button primaryButton" disabled={isSaving||!targetId||!sourceColumn||!targetColumn}>{isSaving?"Creating...":"Create relationship"}</button><button type="button" className="button secondaryButton" onClick={onCancel}>Cancel</button></div>
 </form>
}
