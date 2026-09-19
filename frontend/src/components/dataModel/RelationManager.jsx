"use client";
import {useMemo,useState} from "react";
import Icon from "@/components/ui/Icon";

const CARDINALITIES=[
  ["ONE_TO_MANY","One to many (1:*)"],
  ["MANY_TO_ONE","Many to one (*:1)"],
  ["ONE_TO_ONE","One to one (1:1)"],
  ["MANY_TO_MANY","Many to many (*:*)"],
];
const FILTER_DIRECTIONS=[["SINGLE","Single"],["BOTH","Both"]];
const cardinalityLabel=(value)=>CARDINALITIES.find(([key])=>key===value)?.[1]||value||"One to many (1:*)";
const filterLabel=(value)=>FILTER_DIRECTIONS.find(([key])=>key===value)?.[1]||value||"Single";

export default function RelationManager({tables=[],relations=[],sources=[],onCreate,onDelete,onClose,isSaving}){
 const [showEditor,setShowEditor]=useState(relations.length===0),[search,setSearch]=useState("");
 const [sourceId,setSourceId]=useState(tables[0]?.id||""),[targetId,setTargetId]=useState(""),[sourceColumn,setSourceColumn]=useState(""),[targetColumn,setTargetColumn]=useState(""),[name,setName]=useState("");
 const [cardinality,setCardinality]=useState("ONE_TO_MANY"),[crossFilter,setCrossFilter]=useState("SINGLE"),[isActive,setIsActive]=useState(true);
 const source=useMemo(()=>tables.find(t=>String(t.id)===String(sourceId)),[tables,sourceId]);
 const target=useMemo(()=>tables.find(t=>String(t.id)===String(targetId)),[tables,targetId]);
 const sourceById=useMemo(()=>Object.fromEntries(sources.map(s=>[String(s.id),s])),[sources]);
 const tableById=useMemo(()=>Object.fromEntries(tables.map(t=>[String(t.id),t])),[tables]);
 const visibleRelations=useMemo(()=>{const q=search.trim().toLowerCase();if(!q)return relations;return relations.filter(r=>{const a=tableById[String(r.source_table)],b=tableById[String(r.target_table)];return [r.name,a?.table_name,b?.table_name,(r.source_columns||[]).join(" "),(r.target_columns||[]).join(" "),cardinalityLabel(r.cardinality)].join(" ").toLowerCase().includes(q)})},[relations,search,tableById]);
 function resetEditor(){setName("");setTargetId("");setSourceColumn("");setTargetColumn("");setCardinality("ONE_TO_MANY");setCrossFilter("SINGLE");setIsActive(true)}
 async function submit(e){e.preventDefault();if(!source||!target||!sourceColumn||!targetColumn)return;const autoName=`${source.table_name}_${sourceColumn}__${target.table_name}_${targetColumn}`;await onCreate({name:name.trim()||autoName,data_source:source.data_source,source_table:source.id,target_table:target.id,source_columns:[sourceColumn],target_columns:[targetColumn],cardinality,cross_filter_direction:crossFilter,is_active:isActive});resetEditor();setShowEditor(false)}
 return <div className="relationManager relationManagerListUX">
  <div className="relationManagerHeader"><div><span className="eyebrow">MODEL</span><h2>Manage relationships</h2><p>Review and create logical relationships used by the platform model. These relationships do not alter the schema of External or Private Gateway databases.</p></div><button type="button" className="iconButton" onClick={onClose}>×</button></div>

  <div className="relationManagerToolbar">
   <label className="relationshipSearch"><Icon name="search" size={14}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search relationships"/></label>
   <span className="relationshipCount">{relations.length} relationship{relations.length===1?"":"s"}</span>
   <button type="button" className="button primaryButton smallButton" onClick={()=>setShowEditor(v=>!v)}>{showEditor?"Close editor":"+ New relationship"}</button>
  </div>

  <div className="relationshipsTableWrap">
   <table className="relationshipsTable">
    <thead><tr><th>From</th><th>To</th><th>Cardinality</th><th>Cross-filter</th><th>Active</th><th aria-label="Actions"></th></tr></thead>
    <tbody>{visibleRelations.length?visibleRelations.map(r=>{const a=tableById[String(r.source_table)],b=tableById[String(r.target_table)];return <tr key={r.id}>
      <td><strong>{a?.table_name||"Unknown"}</strong><span>{(r.source_columns||[]).join(", ")||"—"}</span></td>
      <td><strong>{b?.table_name||"Unknown"}</strong><span>{(r.target_columns||[]).join(", ")||"—"}</span></td>
      <td>{cardinalityLabel(r.cardinality)}</td><td>{filterLabel(r.cross_filter_direction)}</td><td><span className={`relationStatus ${r.is_active!==false?"active":"inactive"}`}>{r.is_active!==false?"Active":"Inactive"}</span></td>
      <td><button type="button" className="iconButton danger" title="Delete relationship" onClick={()=>onDelete(r.id)}>×</button></td>
     </tr>}):<tr><td colSpan="6" className="relationshipEmpty">No relationships match this view.</td></tr>}</tbody>
   </table>
  </div>

  {showEditor&&<form className="relationshipEditor" onSubmit={submit}>
   <div className="relationshipEditorHeading"><div><span className="eyebrow">NEW RELATIONSHIP</span><strong>Connect two fields</strong></div><span className="relationshipSafety">Logical model only</span></div>
   <div className="relationshipEndpoints">
    <section className="relationshipEndpoint"><span className="endpointBadge">From</span><label>Table<select value={sourceId} onChange={e=>{setSourceId(e.target.value);setSourceColumn("");if(String(e.target.value)===String(targetId)){setTargetId("");setTargetColumn("")}}}>{tables.map(t=><option key={t.id} value={t.id}>{sourceById[String(t.data_source)]?.name?`${sourceById[String(t.data_source)].name} · `:""}{t.technical_name||t.table_name}</option>)}</select></label><label>Field<select value={sourceColumn} onChange={e=>setSourceColumn(e.target.value)}><option value="">Select field</option>{(source?.fields||[]).map(f=><option key={f.id} value={f.name}>{f.business_name||f.name}</option>)}</select></label></section>
    <div className="relationshipDirection">→</div>
    <section className="relationshipEndpoint"><span className="endpointBadge">To</span><label>Table<select value={targetId} onChange={e=>{setTargetId(e.target.value);setTargetColumn("")}}><option value="">Select table</option>{tables.filter(t=>String(t.id)!==String(sourceId)).map(t=><option key={t.id} value={t.id}>{sourceById[String(t.data_source)]?.name?`${sourceById[String(t.data_source)].name} · `:""}{t.technical_name||t.table_name}</option>)}</select></label><label>Field<select value={targetColumn} onChange={e=>setTargetColumn(e.target.value)}><option value="">Select field</option>{(target?.fields||[]).map(f=><option key={f.id} value={f.name}>{f.business_name||f.name}</option>)}</select></label></section>
   </div>
   <div className="relationshipOptionsGrid">
    <label>Name <input value={name} onChange={e=>setName(e.target.value)} placeholder="Optional · generated automatically"/></label>
    <label>Cardinality <select value={cardinality} onChange={e=>setCardinality(e.target.value)}>{CARDINALITIES.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label>
    <label>Cross-filter direction <select value={crossFilter} onChange={e=>setCrossFilter(e.target.value)}>{FILTER_DIRECTIONS.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label>
    <label className="relationshipActiveToggle"><input type="checkbox" checked={isActive} onChange={e=>setIsActive(e.target.checked)}/><span>Active relationship</span></label>
   </div>
   <div className="formActions"><button type="button" className="button secondaryButton" onClick={()=>{resetEditor();setShowEditor(false)}}>Cancel</button><button className="button primaryButton" disabled={isSaving||!targetId||!sourceColumn||!targetColumn}>{isSaving?"Saving...":"Create relationship"}</button></div>
  </form>}
 </div>
}
